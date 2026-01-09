from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.enums import PayoutStatus, Role, ShiftStatus
from app.models.finance import Payout
from app.models.shift import Shift
from app.models.user import User
from app.schemas.payments import InitiatePayoutIn, PayoutOut
from app.services.audit import record_event
from app.services.shift_state import ensure_transition


router = APIRouter()


@router.post("/payouts/initiate", response_model=PayoutOut)
def initiate_payout(
    payload: InitiatePayoutIn,
    user: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, payload.shift_id)
    if not shift or not shift.assignment:
        raise HTTPException(status_code=404, detail="Shift/assignment not found")
    if shift.status != ShiftStatus.completed:
        raise HTTPException(status_code=409, detail="Shift not completed")

    existing = db.scalar(select(Payout).where(Payout.shift_id == shift.id))
    if existing:
        return PayoutOut(shift_id=shift.id, status=existing.status.value, provider_payout_id=existing.provider_payout_id)

    payout = Payout(
        shift_id=shift.id,
        doctor_user_id=shift.assignment.doctor_user_id,
        amount_inr=shift.pay_amount_inr,
        status=PayoutStatus.pending,
        provider_payout_id=None,
    )
    db.add(payout)
    record_event(
        db,
        shift_id=shift.id,
        assignment_id=shift.assignment.id,
        actor_user_id=user.id,
        event_type="payout_initiated",
        payload={"amount_inr": shift.pay_amount_inr},
    )
    db.commit()
    return PayoutOut(shift_id=shift.id, status=payout.status.value, provider_payout_id=payout.provider_payout_id)

