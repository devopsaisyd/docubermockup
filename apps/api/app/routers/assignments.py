from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.geo import haversine_m
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.clinic import ClinicProfile
from app.models.enums import AssignmentStatus, Role, ShiftStatus
from app.models.shift import LocationPing, Shift, ShiftAssignment
from app.models.user import User
from app.schemas.assignments import (
    AssignmentOut,
    AssignmentStatusUpdateIn,
    LiveSnapshotOut,
    LocationPingIn,
    SosIn,
)
from app.services.audit import emit_timeline_update, record_event
from app.services.shift_state import ensure_transition, now_utc, tracking_window_active


router = APIRouter()


def _load_assignment(db: Session, assignment_id: uuid.UUID) -> ShiftAssignment:
    a = db.get(ShiftAssignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


@router.post("/assignments/{assignment_id}/accept", response_model=AssignmentOut)
def accept_assignment(
    assignment_id: uuid.UUID,
    user: User = Depends(require_role(Role.doctor)),
    db: Session = Depends(get_db),
):
    a = _load_assignment(db, assignment_id)
    if a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    return AssignmentOut(
        id=a.id,
        shift_id=a.shift_id,
        doctor_user_id=a.doctor_user_id,
        status=a.status,
        accepted_at=a.accepted_at,
        created_at=a.created_at,
    )


@router.post("/assignments/{assignment_id}/status", response_model=AssignmentOut)
async def update_status(
    assignment_id: uuid.UUID,
    payload: AssignmentStatusUpdateIn,
    user: User = Depends(require_role(Role.doctor)),
    db: Session = Depends(get_db),
):
    a = _load_assignment(db, assignment_id)
    if a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    shift = db.get(Shift, a.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Only allow advancing along strict machine (booked->en_route)
    if payload.status == AssignmentStatus.en_route:
        ensure_transition(shift.status, ShiftStatus.en_route)
        shift.status = ShiftStatus.en_route
        a.status = AssignmentStatus.en_route
        record_event(db, shift_id=shift.id, assignment_id=a.id, actor_user_id=user.id, event_type="en_route", payload={})
        db.commit()
        await emit_timeline_update(assignment_id=a.id, shift_id=shift.id, event_type="en_route", payload={})
    else:
        raise HTTPException(status_code=400, detail="Unsupported status update in MVP (use OTP for checkin/checkout)")

    return AssignmentOut(
        id=a.id,
        shift_id=a.shift_id,
        doctor_user_id=a.doctor_user_id,
        status=a.status,
        accepted_at=a.accepted_at,
        created_at=a.created_at,
    )


@router.post("/assignments/{assignment_id}/location")
async def location_ping(
    assignment_id: uuid.UUID,
    payload: LocationPingIn,
    user: User = Depends(require_role(Role.doctor)),
    db: Session = Depends(get_db),
):
    a = _load_assignment(db, assignment_id)
    if a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    shift = db.get(Shift, a.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if shift.status not in (ShiftStatus.booked, ShiftStatus.en_route, ShiftStatus.checked_in):
        raise HTTPException(status_code=409, detail="Shift not trackable")

    # Determine checkout timestamp (if completed)
    checkout_at = None
    if shift.status in (ShiftStatus.completed, ShiftStatus.paid):
        ev = db.scalar(
            select(AuditEvent)
            .where(and_(AuditEvent.shift_id == shift.id, AuditEvent.event_type == "checkout"))
            .order_by(desc(AuditEvent.created_at))
        )
        checkout_at = ev.created_at if ev else None

    if not tracking_window_active(shift_start=shift.start_time, shift_end=shift.end_time, checkout_at=checkout_at):
        raise HTTPException(status_code=403, detail="Tracking not active (only during duty window)")

    # crude rate limit: max 1 ping / 5 seconds
    last = db.scalar(
        select(LocationPing).where(LocationPing.assignment_id == a.id).order_by(desc(LocationPing.ts)).limit(1)
    )
    if last and (payload.ts - last.ts).total_seconds() < 5:
        return {"ok": True, "ignored": True}

    ping = LocationPing(
        assignment_id=a.id,
        ts=payload.ts,
        lat=payload.lat,
        lng=payload.lng,
        speed=payload.speed,
        heading=payload.heading,
        accuracy=payload.accuracy,
    )
    db.add(ping)
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=a.id,
        actor_user_id=user.id,
        event_type="location_ping",
        payload={"lat": payload.lat, "lng": payload.lng, "accuracy": payload.accuracy},
    )
    db.commit()

    await emit_timeline_update(
        assignment_id=a.id,
        shift_id=shift.id,
        event_type="location_ping",
        payload={"lat": payload.lat, "lng": payload.lng, "ts": payload.ts.isoformat()},
    )
    return {"ok": True}


@router.get("/assignments/{assignment_id}/live", response_model=LiveSnapshotOut)
def live_snapshot(
    assignment_id: uuid.UUID,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff, Role.doctor)),
    db: Session = Depends(get_db),
):
    a = _load_assignment(db, assignment_id)
    shift = db.get(Shift, a.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if user.role in (Role.clinic_admin, Role.clinic_staff) and shift.clinic_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if user.role == Role.doctor and a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    last_ping = db.scalar(
        select(LocationPing).where(LocationPing.assignment_id == a.id).order_by(desc(LocationPing.ts)).limit(1)
    )
    timeline = db.scalars(
        select(AuditEvent).where(AuditEvent.shift_id == shift.id).order_by(AuditEvent.created_at.asc())
    ).all()

    # best effort: infer checkout time
    checkout_ev = next((t for t in reversed(timeline) if t.event_type == "checkout"), None)
    checkout_at = checkout_ev.created_at if checkout_ev else None
    active = tracking_window_active(shift_start=shift.start_time, shift_end=shift.end_time, checkout_at=checkout_at)

    # Privacy: clinics can only see location during duty window.
    if user.role in (Role.clinic_admin, Role.clinic_staff) and not active:
        last_ping = None

    return LiveSnapshotOut(
        assignment_id=a.id,
        shift_id=shift.id,
        status=shift.status.value,
        tracking_active=active,
        last_ping=(
            {
                "ts": last_ping.ts.isoformat(),
                "lat": last_ping.lat,
                "lng": last_ping.lng,
                "speed": last_ping.speed,
                "heading": last_ping.heading,
                "accuracy": last_ping.accuracy,
            }
            if last_ping
            else None
        ),
        timeline=[
            {"event_type": t.event_type, "ts": t.created_at.isoformat(), "payload": t.payload} for t in timeline
        ],
    )


@router.post("/assignments/{assignment_id}/sos")
async def sos(
    assignment_id: uuid.UUID,
    payload: SosIn,
    user: User = Depends(require_role(Role.doctor)),
    db: Session = Depends(get_db),
):
    a = _load_assignment(db, assignment_id)
    if a.doctor_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    shift = db.get(Shift, a.shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=a.id,
        actor_user_id=user.id,
        event_type="sos",
        payload={"message": payload.message},
    )
    db.commit()
    await emit_timeline_update(assignment_id=a.id, shift_id=shift.id, event_type="sos", payload={"message": payload.message})
    return {"ok": True}

