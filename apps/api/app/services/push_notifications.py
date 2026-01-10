from __future__ import annotations

import json
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.push import PushToken


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_expo_push(to: str, title: str, body: str, data: dict | None = None) -> None:
    payload = {"to": to, "title": title, "body": body, "data": data or {}}
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(EXPO_PUSH_URL, json=payload)


async def notify_user(db: Session, user_id: uuid.UUID, *, title: str, body: str, data: dict | None = None) -> None:
    tokens = db.scalars(select(PushToken).where(PushToken.user_id == user_id)).all()
    for t in tokens:
        if t.platform == "expo":
            try:
                await send_expo_push(t.token, title, body, data=data)
            except Exception:
                continue

