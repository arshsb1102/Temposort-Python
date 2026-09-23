import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "TempoSort FastAPI")
    app_env: str = os.getenv("APP_ENV", "development")
    jwt_secret: str = os.getenv("JWT_SECRET", "tempo-sort-dev-secret-key-2026-!@#123456")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


settings = Settings()
