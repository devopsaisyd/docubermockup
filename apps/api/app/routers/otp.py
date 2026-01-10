from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_role
from app.core.geo import haversine_m
from app.core.security import generate_otp, hash_secret, now_utc, verify_secret
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.clinic import ClinicProfile
from app.models.enums import AssignmentStatus, Role, ShiftStatus
from app.models.enums import PaymentStatus
from app.models.finance import Payment
from app.models.shift import LocationPing, OtpSession, Shift, ShiftAssignment
from app.models.user import User
from app.schemas.assignments import OtpCreateOut, OtpVerifyIn
from app.services.audit import emit_timeline_update, record_event
from app.services.shift_state import ensure_transition


router = APIRouter()

def _require_payment_paid(db: Session, shift_id: uuid.UUID) -> None:
    p = db.scalar(select(Payment).where(Payment.shift_id == shift_id))
    if not p or p.status != PaymentStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required before check-in/out")


@router.post("/assignments/{assignment_id}/otp/create", response_model=OtpCreateOut)
def create_otp(
    assignment_id: uuid.UUID,
    type: str = Query(pattern="^(checkin|checkout)$"),
    allow_remote: bool = Query(default=False, description="Clinic override to allow OTP outside geofence"),
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    a = db.get(ShiftAssignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    shift = db.get(Shift, a.shift_id)
    if not shift or shift.clinic_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    _require_payment_paid(db, shift.id)

    otp = generate_otp()
    expires_at = now_utc() + timedelta(seconds=settings.otp_ttl_seconds)
    session = OtpSession(
        assignment_id=a.id,
        type=type,
        otp_hash=hash_secret(otp),
        expires_at=expires_at,
        allow_remote=allow_remote,
    )
    db.add(session)
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=a.id,
        actor_user_id=user.id,
        event_type=f"otp_created_{type}",
        payload={"allow_remote": allow_remote},
    )
    db.commit()

    return OtpCreateOut(expires_at=expires_at, dev_otp=otp if settings.allow_dev_otp_echo else None)


@router.post("/assignments/{assignment_id}/otp/verify")
async def verify_otp(
    assignment_id: uuid.UUID,
    payload: OtpVerifyIn,
    type: str = Query(pattern="^(checkin|checkout)$"),
    user: User = Depends(require_role(Role.doctor)),
    db: Session = Depends(get_db),
):
    a = db.get(ShiftAssignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    shift = db.get(Shift, a.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    _require_payment_paid(db, shift.id)

    otp_row = db.scalar(
        select(OtpSession)
        .where(and_(OtpSession.assignment_id == a.id, OtpSession.type == type, OtpSession.used_at.is_(None)))
        .order_by(desc(OtpSession.created_at))
    )
    if not otp_row:
        raise HTTPException(status_code=400, detail="No OTP session")
    expires_at = otp_row.expires_at
    if expires_at.tzinfo is None:
        from datetime import timezone as _tz

        expires_at = expires_at.replace(tzinfo=_tz.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=400, detail="OTP expired")
    if not verify_secret(payload.otp, otp_row.otp_hash):
        raise HTTPException(status_code=400, detail="OTP invalid")

    # Geofence check (150m), unless clinic override allow_remote=true
    if not otp_row.allow_remote:
        clinic = db.get(ClinicProfile, shift.clinic_profile_id)
        last_ping = db.scalar(
            select(LocationPing).where(LocationPing.assignment_id == a.id).order_by(desc(LocationPing.ts)).limit(1)
        )
        if not clinic or not last_ping:
            raise HTTPException(status_code=409, detail="No recent location available for geofence validation")
        distance = haversine_m(last_ping.lat, last_ping.lng, clinic.lat, clinic.lng)
        if distance > 150:
            raise HTTPException(status_code=403, detail="Not within geofence (150m). Ask clinic for override OTP.")

    otp_row.used_at = now_utc()

    if type == "checkin":
        if shift.status not in (ShiftStatus.booked, ShiftStatus.en_route):
            raise HTTPException(status_code=409, detail="Cannot check-in in current state")
        ensure_transition(shift.status, ShiftStatus.checked_in)
        shift.status = ShiftStatus.checked_in
        a.status = AssignmentStatus.checked_in
        record_event(db, shift_id=shift.id, assignment_id=a.id, actor_user_id=user.id, event_type="checkin", payload={})
        db.commit()
        await emit_timeline_update(assignment_id=a.id, shift_id=shift.id, event_type="checkin", payload={})
        return {"ok": True, "status": shift.status.value}

    if type == "checkout":
        if shift.status != ShiftStatus.checked_in:
            raise HTTPException(status_code=409, detail="Cannot check-out in current state")
        ensure_transition(shift.status, ShiftStatus.completed)
        shift.status = ShiftStatus.completed
        a.status = AssignmentStatus.completed
        record_event(db, shift_id=shift.id, assignment_id=a.id, actor_user_id=user.id, event_type="checkout", payload={})
        record_event(
            db,
            shift_id=shift.id,
            assignment_id=a.id,
            actor_user_id=None,
            event_type="payout_eligible",
            payload={"amount_inr": shift.pay_amount_inr},
        )
        db.commit()
        await emit_timeline_update(assignment_id=a.id, shift_id=shift.id, event_type="checkout", payload={})
        await emit_timeline_update(
            assignment_id=a.id,
            shift_id=shift.id,
            event_type="payout_eligible",
            payload={"amount_inr": shift.pay_amount_inr},
        )
        return {"ok": True, "status": shift.status.value}

    raise HTTPException(status_code=400, detail="Invalid type")

