from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_secret(value: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + value).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_secret(plain: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split("$", 1)
    except Exception:
        return False
    expected = hashlib.sha256((salt + plain).encode("utf-8")).hexdigest()
    return secrets.compare_digest(expected, digest)


def generate_otp(length: int = 6) -> str:
    # numeric otp
    alphabet = "0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_access_token(user_id: str, role: str) -> str:
    exp = now_utc() + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {"sub": user_id, "role": role, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

