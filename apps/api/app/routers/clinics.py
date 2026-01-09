from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_clinic_owner_id, require_role
from app.core.geo import CHENNAI_POLYGON_LATLNG, point_in_polygon
from app.db.session import get_db
from app.models.clinic import ClinicProfile
from app.models.clinic_staff import ClinicStaffMember
from app.models.enums import Role
from app.models.user import User
from app.schemas.profiles import ClinicMeOut, ClinicUpsertIn
from app.schemas.staff import StaffInviteIn, StaffMemberOut


router = APIRouter()


@router.get("/me", response_model=ClinicMeOut)
def get_me(user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)), db: Session = Depends(get_db)):
    owner_id = get_clinic_owner_id(user, db)
    prof = db.scalar(select(ClinicProfile).where(ClinicProfile.user_id == owner_id))
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic profile not created")
    return prof


@router.post("/me", response_model=ClinicMeOut)
def upsert_me(
    payload: ClinicUpsertIn,
    user: User = Depends(require_role(Role.clinic_admin)),
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


@router.get("/staff", response_model=list[StaffMemberOut])
def list_staff(
    user: User = Depends(require_role(Role.clinic_admin)),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(ClinicStaffMember).where(ClinicStaffMember.clinic_user_id == user.id)).all()
    staff_users = [db.get(User, r.staff_user_id) for r in rows]
    out: list[StaffMemberOut] = []
    for r, u in zip(rows, staff_users, strict=False):
        out.append(StaffMemberOut(id=r.staff_user_id, phone=u.phone if u else None, created_at=r.created_at))
    return out


@router.post("/staff/invite", response_model=StaffMemberOut)
def invite_staff(
    payload: StaffInviteIn,
    user: User = Depends(require_role(Role.clinic_admin)),
    db: Session = Depends(get_db),
):
    # Create (or reuse) staff user account with role clinic_staff
    staff = db.scalar(select(User).where(User.phone == payload.phone))
    if not staff:
        staff = User(role=Role.clinic_staff, phone=payload.phone)
        db.add(staff)
        db.flush()
    else:
        if staff.role != Role.clinic_staff:
            raise HTTPException(status_code=409, detail="Phone is already registered with a different role")

    existing = db.scalar(
        select(ClinicStaffMember).where(
            ClinicStaffMember.clinic_user_id == user.id, ClinicStaffMember.staff_user_id == staff.id
        )
    )
    created_at = None
    if not existing:
        link = ClinicStaffMember(clinic_user_id=user.id, staff_user_id=staff.id)
        db.add(link)
        db.commit()
        created_at = link.created_at
    else:
        created_at = existing.created_at
    return StaffMemberOut(id=staff.id, phone=staff.phone, created_at=created_at or staff.created_at)


@router.delete("/staff/{staff_user_id}")
def remove_staff(
    staff_user_id: str,
    user: User = Depends(require_role(Role.clinic_admin)),
    db: Session = Depends(get_db),
):
    import uuid as _uuid
    from sqlalchemy import delete

    sid = _uuid.UUID(staff_user_id)
    res = db.execute(
        delete(ClinicStaffMember).where(
            ClinicStaffMember.clinic_user_id == user.id, ClinicStaffMember.staff_user_id == sid
        )
    )
    db.commit()
    return {"ok": True, "deleted": res.rowcount or 0}

