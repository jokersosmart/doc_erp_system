"""Application settings loaded from environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    DATABASE_URL: str = Field(..., description="Async PostgreSQL DSN")
    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    # --- Auth ---
    SECRET_KEY: str = Field(..., description="JWT signing key — use openssl rand -hex 32")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"
    # --- LDAP ---
    LDAP_URL: str = "ldap://localhost:389"
    LDAP_BIND_DN: str = "cn=admin,dc=example,dc=com"
    LDAP_BIND_PASSWORD: str = "changeme"
    LDAP_BASE_DN: str = "dc=example,dc=com"
    LDAP_USER_SEARCH_FILTER: str = "(uid={username})"
    # --- LLM ---
    LLM_API_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_CONTEXT_MAX_TOKENS: int = 4096
    # --- Git backend ---
    GIT_BACKEND_TYPE: Literal["gerrit", "github", "gitlab"] = "github"
    GERRIT_URL: str = ""
    GITHUB_TOKEN: str = ""
    GITLAB_URL: str = ""
    GITLAB_TOKEN: str = ""
    # --- Email ---
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "doce-erp@example.com"
    # --- Storage ---
    AUDIT_PACKAGE_STORAGE_PATH: str = "/app/storage/audit_packages"
    AUDIT_PACKAGE_QUOTA_WARNING_GB: float = 50.0
    # --- CodeBeamer ---
    CODEBEAMER_SCHEMA_VERSION: str = "v2024.1"
    # --- App ---
    APP_ENV: Literal["development", "production"] = "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
