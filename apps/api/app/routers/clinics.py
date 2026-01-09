from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.geo import CHENNAI_POLYGON_LATLNG, point_in_polygon
from app.db.session import get_db
from app.models.clinic import ClinicProfile
from app.models.enums import Role
from app.models.user import User
from app.schemas.profiles import ClinicMeOut, ClinicUpsertIn


router = APIRouter()


@router.get("/me", response_model=ClinicMeOut)
def get_me(user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)), db: Session = Depends(get_db)):
    prof = db.scalar(select(ClinicProfile).where(ClinicProfile.user_id == user.id))
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic profile not created")
    return prof


@router.post("/me", response_model=ClinicMeOut)
def upsert_me(
    payload: ClinicUpsertIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    if not point_in_polygon(payload.lat, payload.lng, CHENNAI_POLYGON_LATLNG):
        raise HTTPException(status_code=400, detail="Clinic location must be within Chennai (MVP)")

    prof = db.scalar(select(ClinicProfile).where(ClinicProfile.user_id == user.id))
    if not prof:
        prof = ClinicProfile(
            user_id=user.id,
            name=payload.name,
            address=payload.address,
            city=payload.city,
            lat=payload.lat,
            lng=payload.lng,
        )
        db.add(prof)
    else:
        prof.name = payload.name
        prof.address = payload.address
        prof.city = payload.city
        prof.lat = payload.lat
        prof.lng = payload.lng
    db.commit()
    db.refresh(prof)
    return prof

