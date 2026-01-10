from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.clinic import ClinicProfile
from app.models.doctor import DoctorProfile
from app.models.enums import PaymentStatus, Role, Specialty, VerificationStatus, ShiftStatus
from app.models.finance import Payment
from app.models.shift import Shift
from app.models.user import User


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_booking_and_checkin_otp_flow(client, db_session: Session):
    now = datetime.now(timezone.utc)

    clinic_user = User(role=Role.clinic_admin, phone="9000000001")
    doctor_user = User(role=Role.doctor, phone="9100000100")
    db_session.add_all([clinic_user, doctor_user])
    db_session.flush()

    clinic = ClinicProfile(
        user_id=clinic_user.id,
        name="Test Clinic",
        address="T. Nagar, Chennai",
        city="Chennai",
        lat=13.0418,
        lng=80.2341,
    )
    doc = DoctorProfile(
        user_id=doctor_user.id,
        full_name="Test Doctor",
        specialty=Specialty.dentist_general,
        reg_no="TN-DENT-12345",
        verification_status=VerificationStatus.approved,
        home_lat=13.0420,
        home_lng=80.2342,
    )
    db_session.add_all([clinic, doc])
    db_session.flush()

    shift = Shift(
        clinic_user_id=clinic_user.id,
        clinic_profile_id=clinic.id,
        specialty=Specialty.dentist_general,
        start_time=now + timedelta(minutes=10),
        end_time=now + timedelta(hours=4),
        pay_amount_inr=3500,
        address=clinic.address,
        lat=clinic.lat,
        lng=clinic.lng,
        status=ShiftStatus.posted,
    )
    db_session.add(shift)
    db_session.commit()

    clinic_token = create_access_token(str(clinic_user.id), clinic_user.role.value)
    doctor_token = create_access_token(str(doctor_user.id), doctor_user.role.value)

    # Doctor books the shift (open marketplace)
    res = client.post(f"/shifts/{shift.id}/book", json={}, headers=auth_header(doctor_token))
    assert res.status_code == 200, res.text
    assignment_id = res.json()["assignment_id"]

    # Payment must be captured before live shift actions
    db_session.add(
        Payment(
            shift_id=shift.id,
            clinic_user_id=clinic_user.id,
            amount_inr=shift.pay_amount_inr,
            status=PaymentStatus.paid,
            provider="razorpay",
            provider_order_id="order_test",
            provider_payment_id="pay_test",
        )
    )
    db_session.commit()

    # Doctor sends a location ping within geofence and active window
    ping = {"ts": now.isoformat(), "lat": 13.04181, "lng": 80.23411, "accuracy": 8.0}
    res = client.post(f"/assignments/{assignment_id}/location", json=ping, headers=auth_header(doctor_token))
    assert res.status_code == 200, res.text

    # Clinic creates OTP for check-in (dev OTP echoed)
    res = client.post(
        f"/assignments/{assignment_id}/otp/create?type=checkin",
        json={},
        headers=auth_header(clinic_token),
    )
    assert res.status_code == 200, res.text
    otp = res.json().get("dev_otp")
    assert otp

    # Doctor verifies OTP and checks in
    res = client.post(
        f"/assignments/{assignment_id}/otp/verify?type=checkin",
        json={"otp": otp},
        headers=auth_header(doctor_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "checked_in"

