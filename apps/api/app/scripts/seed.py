from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.clinic import ClinicProfile
from app.models.doctor import DoctorProfile
from app.models.enums import Role, Specialty, VerificationStatus, ShiftStatus
from app.models.shift import Shift
from app.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


CHENNAI_LOCATIONS = [
    ("T. Nagar", 13.0418, 80.2341),
    ("Adyar", 13.0012, 80.2565),
    ("Anna Nagar", 13.0850, 80.2101),
    ("Velachery", 12.9750, 80.2212),
    ("Porur", 13.0382, 80.1565),
    ("Mylapore", 13.0337, 80.2692),
]


def seed() -> None:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with Session(engine) as db:
        # Admin user
        admin = db.scalar(select(User).where(User.phone == "9999999999"))
        if not admin:
            admin = User(role=Role.admin, phone="9999999999")
            db.add(admin)

        # Clinics
        clinics = [
            ("Lakshmi Dental Clinic", "T. Nagar, Chennai", 13.0418, 80.2341, "9000000001"),
            ("Marina Multispeciality", "Mylapore, Chennai", 13.0337, 80.2692, "9000000002"),
            ("OMR Care Hospital", "Adyar, Chennai", 13.0012, 80.2565, "9000000003"),
        ]
        clinic_users: list[User] = []
        for name, addr, lat, lng, phone in clinics:
            u = db.scalar(select(User).where(User.phone == phone))
            if not u:
                u = User(role=Role.clinic_admin, phone=phone)
                db.add(u)
                db.flush()
            clinic_users.append(u)
            prof = db.scalar(select(ClinicProfile).where(ClinicProfile.user_id == u.id))
            if not prof:
                db.add(ClinicProfile(user_id=u.id, name=name, address=addr, city="Chennai", lat=lat, lng=lng))

        # Doctors
        first_names = ["Arun", "Meena", "Karthik", "Priya", "Sathya", "Divya", "Vijay", "Anitha", "Ramesh", "Nisha"]
        last_names = ["Iyer", "Kumar", "Rao", "Menon", "Sharma", "Nair", "Krishnan", "Sundar", "Rajan", "Varma"]
        specialties = [Specialty.dentist_general, Specialty.endodontist, Specialty.anesthetist]

        for i in range(20):
            phone = f"9100000{100 + i}"
            u = db.scalar(select(User).where(User.phone == phone))
            if not u:
                u = User(role=Role.doctor, phone=phone)
                db.add(u)
                db.flush()
            prof = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == u.id))
            if not prof:
                area, lat, lng = random.choice(CHENNAI_LOCATIONS)
                spec = random.choice(specialties)
                full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                reg_no = f"TN-DENT-{10000+i}"
                prof = DoctorProfile(
                    user_id=u.id,
                    full_name=full_name,
                    specialty=spec,
                    reg_no=reg_no,
                    verification_status=VerificationStatus.approved,
                    home_lat=lat + random.uniform(-0.01, 0.01),
                    home_lng=lng + random.uniform(-0.01, 0.01),
                )
                db.add(prof)

        db.flush()

        # Shifts (posted)
        clinic_profiles = db.scalars(select(ClinicProfile)).all()
        for i in range(30):
            clinic = random.choice(clinic_profiles)
            spec = random.choice(specialties)
            start = utcnow() + timedelta(hours=6 + i)
            end = start + timedelta(hours=4)
            pay = random.choice([2500, 3000, 3500, 4000, 5000, 6000, 8000])
            addr = clinic.address
            existing = db.scalar(
                select(Shift).where(Shift.address == addr, Shift.start_time == start, Shift.specialty == spec)
            )
            if existing:
                continue
            db.add(
                Shift(
                    clinic_user_id=clinic.user_id,
                    clinic_profile_id=clinic.id,
                    specialty=spec,
                    start_time=start,
                    end_time=end,
                    pay_amount_inr=pay,
                    address=addr,
                    lat=clinic.lat,
                    lng=clinic.lng,
                    notes="MVP demo shift",
                    auto_replace=bool(i % 2),
                    status=ShiftStatus.posted,
                )
            )

        db.commit()


if __name__ == "__main__":
    seed()

