from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import Role
from app.models.user import User
from app.schemas.profiles import DoctorMeOut, DoctorUpsertIn


router = APIRouter()


@router.get("/me", response_model=DoctorMeOut)
def get_me(user: User = Depends(require_role(Role.doctor)), db: Session = Depends(get_db)):
    prof = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not created")
    return DoctorMeOut(
        id=prof.id,
        full_name=prof.full_name,
        specialty=prof.specialty,
        reg_no=prof.reg_no,
        verification_status=prof.verification_status,
        home_lat=prof.home_lat,
        home_lng=prof.home_lng,
        reliability={
            "cancels_count": prof.reliability_cancels_count,
            "no_show_count": prof.reliability_no_show_count,
            "on_time_rate": prof.reliability_on_time_rate,
            "avg_rating": prof.reliability_avg_rating,
        },
    )


@router.post("/me", response_model=DoctorMeOut)
def upsert_me(payload: DoctorUpsertIn, user: User = Depends(require_role(Role.doctor)), db: Session = Depends(get_db)):
    prof = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
    if not prof:
        prof = DoctorProfile(
            user_id=user.id,
            full_name=payload.full_name,
            specialty=payload.specialty,
            reg_no=payload.reg_no,
            home_lat=payload.home_lat,
            home_lng=payload.home_lng,
        )
        db.add(prof)
    else:
        prof.full_name = payload.full_name
        prof.specialty = payload.specialty
        prof.reg_no = payload.reg_no
        prof.home_lat = payload.home_lat
        prof.home_lng = payload.home_lng
    db.commit()
    return get_me(user=user, db=db)

