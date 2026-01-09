from __future__ import annotations

import pytest

from app.models.enums import ShiftStatus
from app.services.shift_state import ensure_transition, tracking_window_active


def test_allowed_transitions():
    ensure_transition(ShiftStatus.draft, ShiftStatus.posted)
    ensure_transition(ShiftStatus.posted, ShiftStatus.booked)
    ensure_transition(ShiftStatus.booked, ShiftStatus.en_route)
    ensure_transition(ShiftStatus.en_route, ShiftStatus.checked_in)
    ensure_transition(ShiftStatus.checked_in, ShiftStatus.completed)
    ensure_transition(ShiftStatus.completed, ShiftStatus.paid)


def test_invalid_transition_raises():
    with pytest.raises(Exception):
        ensure_transition(ShiftStatus.posted, ShiftStatus.checked_in)

