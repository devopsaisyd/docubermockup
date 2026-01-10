from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.deps import get_clinic_owner_id, require_role
from app.db.session import get_db
from app.models.enums import Role, ShiftStatus
from app.models.finance import Payment, Payout
from app.models.shift import Shift
from app.models.user import User


router = APIRouter()


@router.get("/billing/clinic/payments")
def clinic_payments(user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)), db: Session = Depends(get_db)):
    owner_id = get_clinic_owner_id(user, db)
    payments = db.scalars(select(Payment).where(Payment.clinic_user_id == owner_id).order_by(Payment.created_at.desc())).all()
    return [
        {
            "shift_id": str(p.shift_id),
            "amount_inr": p.amount_inr,
            "status": p.status.value,
            "provider": p.provider,
            "provider_order_id": p.provider_order_id,
            "provider_payment_id": p.provider_payment_id,
            "created_at": p.created_at.isoformat(),
        }
        for p in payments
    ]


@router.get("/billing/clinic/invoices")
def clinic_invoices(user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)), db: Session = Depends(get_db)):
    owner_id = get_clinic_owner_id(user, db)
    shifts = db.scalars(select(Shift).where(Shift.clinic_user_id == owner_id).order_by(Shift.start_time.desc())).all()
    return [
        {
            "shift_id": str(s.id),
            "status": s.status.value,
            "amount_inr": s.pay_amount_inr,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "invoice_url": f"/invoices/{s.id}",
        }
        for s in shifts
    ]


@router.get("/billing/doctor/earnings")
def doctor_earnings(user: User = Depends(require_role(Role.doctor)), db: Session = Depends(get_db)):
    # Show completed/paid shifts assigned to the doctor
    shifts = db.scalars(
        select(Shift)
        .join(Shift.assignment)
        .where(Shift.assignment.has(doctor_user_id=user.id))
        .order_by(Shift.start_time.desc())
    ).all()
    payouts = db.scalars(select(Payout).where(Payout.doctor_user_id == user.id).order_by(Payout.created_at.desc())).all()
    return {
        "shifts": [
            {
                "shift_id": str(s.id),
                "status": s.status.value,
                "amount_inr": s.pay_amount_inr,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "invoice_url": f"/invoices/{s.id}",
            }
            for s in shifts
        ],
        "payouts": [
            {
                "shift_id": str(p.shift_id),
                "amount_inr": p.amount_inr,
                "status": p.status.value,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "created_at": p.created_at.isoformat(),
            }
            for p in payouts
        ],
    }

