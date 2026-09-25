from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TempoSort FastAPI"
    app_env: str = "development"
    debug: bool = False
    jwt_secret: SecretStr = Field(default="tempo-sort-dev-secret-key-2026-!@#123456")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "postgresql://postgres:postgres@localhost:5433/temposort"
    frontend_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    mail_provider: str = "console"
    resend_api_key: SecretStr = Field(default=SecretStr(""))
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = Field(default=SecretStr(""))
    smtp_from_email: str = "no-reply@temposort.local"
    smtp_from_name: str = "TempoSort"
    enable_ssl: bool = False


settings = Settings()

__all__ = ["settings"]
