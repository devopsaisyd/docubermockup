from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.deps import get_clinic_owner_id, require_role
from app.core.geo import CHENNAI_POLYGON_LATLNG, haversine_m, point_in_polygon
from app.db.session import get_db
from app.models.clinic import ClinicProfile
from app.models.doctor import DoctorProfile
from app.models.enums import AssignmentStatus, Role, ShiftStatus, VerificationStatus
from app.models.shift import Shift, ShiftAssignment
from app.models.user import User
from app.schemas.shifts import BookResultOut, CandidateOut, ShiftBookIn, ShiftCreateIn, ShiftOut
from app.services.audit import record_event
from app.services.google_maps import distance_matrix_eta
from app.services.shift_state import assignment_status_from_shift_status, ensure_transition, now_utc
from app.realtime.socketio import emit_specialty_broadcast


router = APIRouter()


def _to_shift_out(db: Session, shift: Shift) -> ShiftOut:
    assignment_id = shift.assignment.id if shift.assignment else None
    doctor_user_id = shift.assignment.doctor_user_id if shift.assignment else None
    doctor_name = None
    if doctor_user_id:
        d = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == doctor_user_id))
        doctor_name = d.full_name if d else None
    return ShiftOut(
        id=shift.id,
        clinic_profile_id=shift.clinic_profile_id,
        specialty=shift.specialty,
        start_time=shift.start_time,
        end_time=shift.end_time,
        pay_amount_inr=shift.pay_amount_inr,
        address=shift.address,
        lat=shift.lat,
        lng=shift.lng,
        notes=shift.notes,
        auto_replace=shift.auto_replace,
        status=shift.status,
        created_at=shift.created_at,
        assignment_id=assignment_id,
        doctor_user_id=doctor_user_id,
        doctor_name=doctor_name,
    )


@router.post("/shifts", response_model=ShiftOut)
async def create_shift(
    payload: ShiftCreateIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    owner_id = get_clinic_owner_id(user, db)
    clinic = db.scalar(select(ClinicProfile).where(ClinicProfile.user_id == owner_id))
    if not clinic:
        raise HTTPException(status_code=400, detail="Create clinic profile first")
    if not point_in_polygon(payload.lat, payload.lng, CHENNAI_POLYGON_LATLNG):
        raise HTTPException(status_code=400, detail="Shift location must be within Chennai (MVP)")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    shift = Shift(
        clinic_user_id=owner_id,
        clinic_profile_id=clinic.id,
        specialty=payload.specialty,
        start_time=payload.start_time,
        end_time=payload.end_time,
        pay_amount_inr=payload.pay_amount_inr,
        address=payload.address,
        lat=payload.lat,
        lng=payload.lng,
        notes=payload.notes,
        auto_replace=payload.auto_replace,
        status=ShiftStatus.posted,
    )
    db.add(shift)
    db.flush()
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=None,
        actor_user_id=user.id,
        event_type="shift_posted",
        payload={"status": shift.status.value},
    )
    db.commit()
    db.refresh(shift)
    # Broadcast to doctors in the same specialty (bidding lobby)
    await emit_specialty_broadcast(
        shift.specialty.value,
        {
            "type": "shift_posted",
            "shift": {
                "id": str(shift.id),
                "specialty": shift.specialty.value,
                "start_time": shift.start_time.isoformat(),
                "end_time": shift.end_time.isoformat(),
                "pay_amount_inr": shift.pay_amount_inr,
                "address": shift.address,
                "lat": shift.lat,
                "lng": shift.lng,
                "status": shift.status.value,
            },
        },
    )
    return _to_shift_out(db, shift)


@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    owner_id = get_clinic_owner_id(user, db)
    rows = db.scalars(select(Shift).where(Shift.clinic_user_id == owner_id).order_by(Shift.start_time.desc())).all()
    return [_to_shift_out(db, s) for s in rows]


@router.get("/shifts/{shift_id}", response_model=ShiftOut)
def get_shift(
    shift_id: uuid.UUID,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if user.role in (Role.clinic_admin, Role.clinic_staff):
        owner_id = get_clinic_owner_id(user, db)
        if shift.clinic_user_id != owner_id:
            raise HTTPException(status_code=403, detail="Not your shift")
    return _to_shift_out(db, shift)


@router.get("/shifts/{shift_id}/candidates", response_model=list[CandidateOut])
async def candidates(
    shift_id: uuid.UUID,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    owner_id = get_clinic_owner_id(user, db)
    if not shift or shift.clinic_user_id != owner_id:
        raise HTTPException(status_code=404, detail="Shift not found")

    doctors = db.scalars(
        select(DoctorProfile).where(
            and_(
                DoctorProfile.verification_status == VerificationStatus.approved,
                DoctorProfile.specialty == shift.specialty,
            )
        )
    ).all()

    out: list[CandidateOut] = []
    for d in doctors:
        if d.home_lat is None or d.home_lng is None:
            continue
        eta = await distance_matrix_eta(origin_lat=d.home_lat, origin_lng=d.home_lng, dest_lat=shift.lat, dest_lng=shift.lng)
        out.append(
            CandidateOut(
                doctor_user_id=d.user_id,
                doctor_profile_id=d.id,
                full_name=d.full_name,
                specialty=d.specialty.value,
                reliability={
                    "cancels_count": d.reliability_cancels_count,
                    "no_show_count": d.reliability_no_show_count,
                    "on_time_rate": d.reliability_on_time_rate,
                    "avg_rating": d.reliability_avg_rating,
                },
                eta_minutes=eta.eta_minutes,
                distance_m=eta.distance_m,
            )
        )

    out.sort(key=lambda x: (x.eta_minutes if x.eta_minutes is not None else 10**9, -x.reliability.get("on_time_rate", 0)))
    return out[:20]


@router.get("/jobs/available", response_model=list[ShiftOut])
def available_jobs(user: User = Depends(require_role(Role.doctor)), db: Session = Depends(get_db)):
    doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
    if not doc:
        raise HTTPException(status_code=400, detail="Create doctor profile first")
    if doc.verification_status != VerificationStatus.approved:
        return []
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Shift).where(
            and_(
                Shift.status == ShiftStatus.posted,
                Shift.specialty == doc.specialty,
                Shift.start_time >= now,
            )
        ).order_by(Shift.start_time.asc())
    ).all()
    return [_to_shift_out(db, s) for s in rows]


@router.post("/shifts/{shift_id}/book", response_model=BookResultOut)
def book_shift(
    shift_id: uuid.UUID,
    payload: ShiftBookIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if shift.status != ShiftStatus.posted:
        raise HTTPException(status_code=409, detail="Shift not available")

    if user.role == Role.doctor:
        doctor_user_id = user.id
    else:
        owner_id = get_clinic_owner_id(user, db)
        if shift.clinic_user_id != owner_id:
            raise HTTPException(status_code=403, detail="Not your shift")
        if not payload.doctor_user_id:
            raise HTTPException(status_code=400, detail="doctor_user_id required for clinic booking")
        doctor_user_id = payload.doctor_user_id

    doc = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == doctor_user_id))
    if not doc or doc.verification_status != VerificationStatus.approved:
        raise HTTPException(status_code=400, detail="Doctor not available/verified")
    if doc.specialty != shift.specialty:
        raise HTTPException(status_code=400, detail="Specialty mismatch")

    ensure_transition(shift.status, ShiftStatus.booked)
    shift.status = ShiftStatus.booked

    assignment = ShiftAssignment(
        shift_id=shift.id,
        doctor_user_id=doctor_user_id,
        doctor_profile_id=doc.id,
        status=AssignmentStatus.booked,
        accepted_at=now_utc(),
    )
    db.add(assignment)
    db.flush()

    record_event(
        db,
        shift_id=shift.id,
        assignment_id=assignment.id,
        actor_user_id=user.id,
        event_type="shift_booked",
        payload={"doctor_user_id": str(doctor_user_id)},
    )
    db.commit()

    return BookResultOut(shift_id=shift.id, assignment_id=assignment.id, status=assignment.status.value)

