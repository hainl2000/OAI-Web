from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/olympicai"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cookie_name: str = "oai_session"
    cookie_secure: bool = False

    cors_origins: str = "http://localhost:3000"

    admin_username: str = "admin"
    admin_password: str = "admin123456"
    admin_name: str = "Quản trị viên"

    csv_max_bytes: int = 5 * 1024 * 1024
    csv_max_rows: int = 50_000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
