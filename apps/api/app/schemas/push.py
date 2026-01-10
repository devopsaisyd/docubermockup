from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterPushTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    platform: str = Field(default="expo")


class RegisterPushTokenOut(BaseModel):
    ok: bool = True

