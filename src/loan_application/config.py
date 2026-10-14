from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    log_format: Literal["text", "json"] = "text"
    seed_officer_username: str = "officer1"
    seed_officer_password: str | None = None


settings = Settings()  # type: ignore[call-arg]  # values come from .env
