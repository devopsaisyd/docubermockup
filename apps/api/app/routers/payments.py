from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_role
from app.db.session import get_db
from app.models.enums import PaymentStatus, Role, ShiftStatus
from app.models.finance import Payment
from app.models.shift import Shift
from app.models.user import User
from app.schemas.payments import CreateOrderIn, CreateOrderOut
from app.services.audit import record_event
from app.services.razorpay import razorpay


router = APIRouter()


@router.post("/payments/create-order", response_model=CreateOrderOut)
async def create_order(
    payload: CreateOrderIn,
    user: User = Depends(require_role(Role.clinic_admin, Role.clinic_staff)),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, payload.shift_id)
    if not shift or shift.clinic_user_id != user.id:
        raise HTTPException(status_code=404, detail="Shift not found")
    if shift.status not in (ShiftStatus.posted, ShiftStatus.booked):
        raise HTTPException(status_code=409, detail="Shift not payable")

    existing = db.scalar(select(Payment).where(Payment.shift_id == shift.id))
    if existing and existing.provider_order_id:
        return CreateOrderOut(
            amount_inr=existing.amount_inr,
            provider_order_id=existing.provider_order_id,
            razorpay_key_id=settings.razorpay_key_id,
        )

    order = await razorpay.create_order(amount_inr=shift.pay_amount_inr, receipt=f"shift_{shift.id}")
    provider_order_id = order["id"]

    if not existing:
        existing = Payment(
            shift_id=shift.id,
            clinic_user_id=user.id,
            amount_inr=shift.pay_amount_inr,
            status=PaymentStatus.created,
            provider="razorpay",
            provider_order_id=provider_order_id,
            raw_provider_payload=json.dumps(order),
        )
        db.add(existing)
    else:
        existing.provider_order_id = provider_order_id
        existing.status = PaymentStatus.created
        existing.raw_provider_payload = json.dumps(order)

    record_event(
        db,
        shift_id=shift.id,
        assignment_id=shift.assignment.id if shift.assignment else None,
        actor_user_id=user.id,
        event_type="payment_order_created",
        payload={"provider_order_id": provider_order_id},
    )
    db.commit()

    return CreateOrderOut(
        amount_inr=shift.pay_amount_inr,
        provider_order_id=provider_order_id,
        razorpay_key_id=settings.razorpay_key_id,
    )


@router.post("/payments/webhook")
async def webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    body = await request.body()
    sig = x_razorpay_signature or ""
    if not razorpay.verify_webhook(body=body, signature=sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event")
    entity = (payload.get("payload") or {}).get("payment", {}).get("entity", {})
    order_id = entity.get("order_id")
    payment_id = entity.get("id")

    if event in ("payment.captured", "payment.authorized") and order_id:
        p = db.scalar(select(Payment).where(Payment.provider_order_id == order_id))
        if p:
            p.status = PaymentStatus.paid
            p.provider_payment_id = payment_id
            p.raw_provider_payload = json.dumps(payload)
            db.commit()
            return {"ok": True}

    return {"ok": True}

