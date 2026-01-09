from __future__ import annotations

import enum


class Role(str, enum.Enum):
    clinic_admin = "clinic_admin"
    clinic_staff = "clinic_staff"
    doctor = "doctor"
    admin = "admin"


class Specialty(str, enum.Enum):
    dentist_general = "dentist_general"
    endodontist = "endodontist"
    anesthetist = "anesthetist"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ShiftStatus(str, enum.Enum):
    draft = "draft"
    posted = "posted"
    booked = "booked"
    en_route = "en_route"
    checked_in = "checked_in"
    completed = "completed"
    paid = "paid"
    canceled = "canceled"
    no_show = "no_show"


class AssignmentStatus(str, enum.Enum):
    booked = "booked"
    en_route = "en_route"
    checked_in = "checked_in"
    completed = "completed"
    canceled = "canceled"
    no_show = "no_show"


class CredentialStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OtpType(str, enum.Enum):
    checkin = "checkin"
    checkout = "checkout"


class PaymentStatus(str, enum.Enum):
    created = "created"
    paid = "paid"
    failed = "failed"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    paid = "paid"
    failed = "failed"


class AuditEventType(str, enum.Enum):
    shift_posted = "shift_posted"
    shift_booked = "shift_booked"
    shift_canceled = "shift_canceled"
    en_route = "en_route"
    checkin = "checkin"
    checkout = "checkout"
    no_show = "no_show"
    payout_eligible = "payout_eligible"
    payout_paid = "payout_paid"
    sos = "sos"
    location_ping = "location_ping"

