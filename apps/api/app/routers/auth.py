from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, generate_otp, hash_secret, now_utc, verify_secret
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import AuthOtp, User
from app.schemas.auth import AuthOtpRequestIn, AuthOtpRequestOut, AuthOtpVerifyIn, AuthTokenOut


router = APIRouter()


@router.post("/otp/request", response_model=AuthOtpRequestOut)
def otp_request(payload: AuthOtpRequestIn, db: Session = Depends(get_db)) -> AuthOtpRequestOut:
    otp = generate_otp()
    expires_at = now_utc() + timedelta(seconds=settings.otp_ttl_seconds)

    existing = db.scalar(select(AuthOtp).where(AuthOtp.phone == payload.phone))
    if existing:
        existing.otp_hash = hash_secret(otp)
        existing.expires_at = expires_at
        existing.consumed_at = None
    else:
        db.add(AuthOtp(phone=payload.phone, otp_hash=hash_secret(otp), expires_at=expires_at))
    db.commit()

    return AuthOtpRequestOut(dev_otp=otp if settings.allow_dev_otp_echo else None)


@router.post("/otp/verify", response_model=AuthTokenOut)
def otp_verify(payload: AuthOtpVerifyIn, db: Session = Depends(get_db)) -> AuthTokenOut:
    otp_row = db.scalar(select(AuthOtp).where(AuthOtp.phone == payload.phone))
    if not otp_row or otp_row.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP invalid")
    if otp_row.expires_at < now_utc():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    if not verify_secret(payload.otp, otp_row.otp_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP invalid")

    try:
        role = Role(payload.role)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        user = User(role=role, phone=payload.phone)
        db.add(user)
        db.flush()
    else:
        # Keep role stable (avoid privilege escalation)
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role mismatch for this phone")

    otp_row.consumed_at = now_utc()
    user.last_login_at = now_utc()
    db.commit()

    return AuthTokenOut(access_token=create_access_token(str(user.id), user.role.value))

