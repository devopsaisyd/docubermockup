from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CreateOrderIn(BaseModel):
    shift_id: UUID


class CreateOrderOut(BaseModel):
    provider: str = "razorpay"
    amount_inr: int
    currency: str = "INR"
    provider_order_id: str
    razorpay_key_id: str | None = None


class ConfirmPaymentIn(BaseModel):
    provider_order_id: str
    provider_payment_id: str
    provider_signature: str | None = None


class ConfirmPaymentOut(BaseModel):
    ok: bool = True
    status: str
    shift_id: UUID


class WebhookIn(BaseModel):
    # Razorpay sends arbitrary payload; keep raw.
    payload: dict = Field(default_factory=dict)


class InitiatePayoutIn(BaseModel):
    shift_id: UUID


class PayoutOut(BaseModel):
    shift_id: UUID
    status: str
    provider_payout_id: str | None = None

