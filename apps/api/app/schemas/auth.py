from __future__ import annotations

from pydantic import BaseModel, Field


class AuthOtpRequestIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    role_hint: str | None = Field(default=None, description="Optional: clinic_admin | doctor for UX")


class AuthOtpRequestOut(BaseModel):
    ok: bool = True
    dev_otp: str | None = Field(
        default=None,
        description="Only present when ALLOW_DEV_OTP_ECHO=true (local demo).",
    )


class AuthOtpVerifyIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    otp: str = Field(min_length=4, max_length=8)
    role: str = Field(description="clinic_admin | clinic_staff | doctor | admin")


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

