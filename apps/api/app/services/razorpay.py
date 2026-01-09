from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import httpx

from app.core.config import settings


class RazorpayClient:
    def __init__(self) -> None:
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret

    async def create_order(self, *, amount_inr: int, receipt: str) -> dict:
        # Razorpay amount is in paise
        if not self.key_id or not self.key_secret:
            return {
                "id": f"order_demo_{uuid.uuid4().hex}",
                "amount": amount_inr * 100,
                "currency": "INR",
                "status": "created",
                "receipt": receipt,
                "notes": {"mode": "demo"},
            }

        url = "https://api.razorpay.com/v1/orders"
        payload = {
            "amount": amount_inr * 100,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        }
        async with httpx.AsyncClient(timeout=10.0, auth=(self.key_id, self.key_secret)) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    def verify_webhook(self, *, body: bytes, signature: str) -> bool:
        if not settings.razorpay_webhook_secret:
            # Dev fallback: accept
            return True
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


razorpay = RazorpayClient()

