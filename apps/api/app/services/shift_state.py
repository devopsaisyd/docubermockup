from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.models.enums import AssignmentStatus, ShiftStatus


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_TRANSITIONS: dict[ShiftStatus, set[ShiftStatus]] = {
    ShiftStatus.draft: {ShiftStatus.posted, ShiftStatus.canceled},
    ShiftStatus.posted: {ShiftStatus.booked, ShiftStatus.canceled},
    # MVP: allow direct check-in even if doctor didn't set "en_route"
    ShiftStatus.booked: {ShiftStatus.en_route, ShiftStatus.checked_in, ShiftStatus.canceled, ShiftStatus.no_show},
    ShiftStatus.en_route: {ShiftStatus.checked_in, ShiftStatus.canceled, ShiftStatus.no_show},
    ShiftStatus.checked_in: {ShiftStatus.completed},
    ShiftStatus.completed: {ShiftStatus.paid},
    ShiftStatus.paid: set(),
    ShiftStatus.canceled: set(),
    ShiftStatus.no_show: set(),
}


def ensure_transition(current: ShiftStatus, target: ShiftStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid shift transition {current.value} -> {target.value}",
        )


def assignment_status_from_shift_status(status_: ShiftStatus) -> AssignmentStatus | None:
    mapping = {
        ShiftStatus.booked: AssignmentStatus.booked,
        ShiftStatus.en_route: AssignmentStatus.en_route,
        ShiftStatus.checked_in: AssignmentStatus.checked_in,
        ShiftStatus.completed: AssignmentStatus.completed,
        ShiftStatus.canceled: AssignmentStatus.canceled,
        ShiftStatus.no_show: AssignmentStatus.no_show,
    }
    return mapping.get(status_)


def tracking_window_active(
    *,
    shift_start: datetime,
    shift_end: datetime,
    checkout_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    n = now or now_utc()
    # Defensive: sqlite test DB may roundtrip tz-naive datetimes. Assume UTC.
    if shift_start.tzinfo is None:
        shift_start = shift_start.replace(tzinfo=timezone.utc)
    if shift_end.tzinfo is None:
        shift_end = shift_end.replace(tzinfo=timezone.utc)
    if checkout_at is not None and checkout_at.tzinfo is None:
        checkout_at = checkout_at.replace(tzinfo=timezone.utc)
    start = shift_start - timedelta(minutes=30)
    end = min(shift_end, checkout_at) if checkout_at else shift_end
    return start <= n <= end

