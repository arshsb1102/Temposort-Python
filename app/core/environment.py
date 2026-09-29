from __future__ import annotations

from pydantic import Field, SecretStr, model_validator
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
    redis_url: str = "redis://localhost:6379/0"
    celery_result_backend_url: str = "redis://localhost:6379/1"
    redis_cache_ttl_seconds: int = 300
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "temposort-api"
    metrics_enabled: bool = True
    reminder_digest_enabled: bool = True
    reminder_digest_hour: int = 9
    reminder_digest_minute: int = 0
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

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        if self.app_env.lower() not in {"prod", "production"}:
            return self
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters in production")
        if self.database_url.startswith("postgresql://postgres:postgres@localhost"):
            raise ValueError("DATABASE_URL must use a managed, non-local PostgreSQL service in production")
        if self.redis_url.startswith("redis://"):
            raise ValueError("REDIS_URL must use TLS (rediss://) in production")
        if self.mail_provider.lower() == "console":
            raise ValueError("MAIL_PROVIDER must be configured for production")
        return self


settings = Settings()

__all__ = ["settings"]
