from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import PayoutStatus, Role, ShiftStatus, VerificationStatus
from app.models.finance import Payout
from app.models.shift import LocationPing, Shift
from app.models.user import User
from app.services.audit import record_event
from app.services.shift_state import ensure_transition


router = APIRouter()


@router.post("/doctors/{doctor_profile_id}/verify")
def verify_doctor(
    doctor_profile_id: uuid.UUID,
    user: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    doc = db.get(DoctorProfile, doctor_profile_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doc.verification_status = VerificationStatus.approved
    db.commit()
    return {"ok": True, "verification_status": doc.verification_status.value}


@router.post("/payouts/{shift_id}/mark-paid")
def mark_payout_paid(
    shift_id: uuid.UUID,
    user: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift or not shift.assignment:
        raise HTTPException(status_code=404, detail="Shift/assignment not found")
    if shift.status != ShiftStatus.completed:
        raise HTTPException(status_code=409, detail="Shift not eligible (must be completed)")

    payout = db.scalar(select(Payout).where(Payout.shift_id == shift.id))
    if not payout:
        payout = Payout(
            shift_id=shift.id,
            doctor_user_id=shift.assignment.doctor_user_id,
            amount_inr=shift.pay_amount_inr,
            status=PayoutStatus.paid,
            paid_at=datetime.now(timezone.utc),
        )
        db.add(payout)
    else:
        payout.status = PayoutStatus.paid
        payout.paid_at = datetime.now(timezone.utc)

    ensure_transition(shift.status, ShiftStatus.paid)
    shift.status = ShiftStatus.paid

    record_event(
        db,
        shift_id=shift.id,
        assignment_id=shift.assignment.id,
        actor_user_id=user.id,
        event_type="payout_paid",
        payload={"amount_inr": shift.pay_amount_inr},
    )
    db.commit()
    return {"ok": True, "shift_status": shift.status.value}


@router.post("/jobs/run-no-show")
def run_no_show(
    user: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    shifts = db.scalars(
        select(Shift).where(
            and_(
                Shift.status.in_([ShiftStatus.booked, ShiftStatus.en_route]),
                Shift.start_time < now,
            )
        )
    ).all()
    updated = 0
    for s in shifts:
        # MVP: mark no_show if shift start passed and status not checked_in
        s.status = ShiftStatus.no_show
        updated += 1
        record_event(
            db,
            shift_id=s.id,
            assignment_id=s.assignment.id if s.assignment else None,
            actor_user_id=user.id,
            event_type="no_show",
            payload={},
        )
    db.commit()
    return {"ok": True, "updated": updated}


@router.post("/location/rollup")
def location_rollup(
    user: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    """
    MVP rollup: keep only last 2 hours of location pings.
    For production, consider 1/min compression + long-term storage policies.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    res = db.execute(delete(LocationPing).where(LocationPing.ts < cutoff))
    db.commit()
    return {"ok": True, "deleted": res.rowcount or 0}

