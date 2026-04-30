"""Application configuration using pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://docerp:docerp_password@localhost:5432/doc_erp_db"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://docerp:docerp_password@localhost:5432/doc_erp_test"

    # JWT
    SECRET_KEY: str = "change-this-secret-key-in-production-use-256-bit-random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    MAX_CONTENT_SIZE_MB: int = 5
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    @property
    def max_content_size_bytes(self) -> int:
        return self.MAX_CONTENT_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
