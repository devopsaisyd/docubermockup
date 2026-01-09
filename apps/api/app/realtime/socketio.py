from __future__ import annotations

import uuid

import socketio

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.enums import Role, ShiftStatus
from app.models.shift import Shift, ShiftAssignment
from app.services.shift_state import tracking_window_active


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


def room_for_assignment(assignment_id: uuid.UUID) -> str:
    return f"assignment:{assignment_id}"


@sio.event
async def connect(sid, environ, auth):
    # Expect token in auth { token: "..." }
    token = None
    if isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        raise ConnectionRefusedError("missing_token")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise ConnectionRefusedError("invalid_token")
    # Store user_id/role for future authorization checks (minimal MVP)
    sio.save_session(sid, {"user_id": payload.get("sub"), "role": payload.get("role")})


@sio.event
async def join_assignment(sid, data):
    # data: { assignment_id }
    session = await sio.get_session(sid)
    assignment_id = data.get("assignment_id")
    try:
        aid = uuid.UUID(str(assignment_id))
    except Exception:
        return

    # Authorization:
    # - doctor: can join their own assignment
    # - clinic: can join their own shift assignment, but only while tracking window active
    # - admin: can join anything (MVP)
    try:
        user_id = uuid.UUID(str(session.get("user_id")))
        role = Role(str(session.get("role")))
    except Exception:
        return

    with SessionLocal() as db:
        a = db.get(ShiftAssignment, aid)
        if not a:
            return
        shift = db.get(Shift, a.shift_id)
        if not shift:
            return

        if role == Role.doctor:
            if a.doctor_user_id != user_id:
                return
        elif role in (Role.clinic_admin, Role.clinic_staff):
            if shift.clinic_user_id != user_id:
                return
            # Enforce privacy: clinic can join only during duty window
            if not tracking_window_active(shift_start=shift.start_time, shift_end=shift.end_time, checkout_at=None):
                return
        elif role == Role.admin:
            pass
        else:
            return

    await sio.enter_room(sid, room_for_assignment(aid))
    await sio.emit("joined", {"assignment_id": str(aid)}, to=sid)


@sio.event
async def leave_assignment(sid, data):
    assignment_id = data.get("assignment_id")
    try:
        aid = uuid.UUID(str(assignment_id))
    except Exception:
        return
    await sio.leave_room(sid, room_for_assignment(aid))


async def emit_assignment_update(assignment_id: uuid.UUID, payload: dict) -> None:
    await sio.emit("assignment_update", payload, room=room_for_assignment(assignment_id))

