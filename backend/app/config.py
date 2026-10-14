from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = "postgresql+psycopg://clinicflow:clinicflow@localhost:5432/clinicflow"
    ai_mode: Literal["demo", "live", "disabled"] = "disabled"
    openai_api_key: str = ""
    openai_model: str = ""
    demo_password: str = ""
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    cookie_secure: bool = False
    app_env: Literal["development", "test", "production"] = "development"
    session_hours: int = 8
    generation_limit_per_hour: int = 20
    login_limit_per_minute: int = 10
    provider_timeout_seconds: float = 45

    @property
    def origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def production_settings(self):
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires COOKIE_SECURE=true")
            if not self.origins or any(not o.startswith("https://") or "*" in o for o in self.origins):
                raise ValueError("Production requires explicit HTTPS ALLOWED_ORIGINS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
