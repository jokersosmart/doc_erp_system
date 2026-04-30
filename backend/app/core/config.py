"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DocERP API"
    APP_ENV: Literal["development", "production"] = "development"

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://doce_erp:changeme@localhost:5432/doce_erp"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = Field(default="change-me")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings object."""
    return Settings()


settings = get_settings()
