from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.realtime.socketio import emit_assignment_update


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def record_event(
    db: Session,
    *,
    shift_id: uuid.UUID,
    assignment_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    event_type: str,
    payload: dict | None = None,
) -> AuditEvent:
    ev = AuditEvent(
        shift_id=shift_id,
        assignment_id=assignment_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        payload=payload or {},
        created_at=now_utc(),
    )
    db.add(ev)
    db.flush()
    return ev


async def emit_timeline_update(*, assignment_id: uuid.UUID, shift_id: uuid.UUID, event_type: str, payload: dict):
    await emit_assignment_update(
        assignment_id,
        {
            "assignment_id": str(assignment_id),
            "shift_id": str(shift_id),
            "event_type": event_type,
            "payload": payload,
            "ts": now_utc().isoformat(),
        },
    )

