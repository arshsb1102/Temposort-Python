from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "TempoSort FastAPI")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    jwt_secret: str = os.getenv("JWT_SECRET", "tempo-sort-dev-secret-key-2026-!@#123456")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/temposort")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    mail_provider: str = os.getenv("MAIL_PROVIDER", "console")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@temposort.local")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "TempoSort")
    enable_ssl: bool = os.getenv("SMTP_ENABLE_SSL", "false").lower() == "true"


settings = Settings()
