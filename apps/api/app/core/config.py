from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/locummap"
    jwt_secret: str = "dev-change-me"
    jwt_ttl_minutes: int = 60 * 24 * 7
    otp_ttl_seconds: int = 300
    allow_dev_otp_echo: bool = True
    service_area: str = "chennai"

    google_maps_api_key: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None


settings = Settings()

