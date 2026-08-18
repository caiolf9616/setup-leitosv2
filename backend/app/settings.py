from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    session_max_age_days: int = 30
    environment: Literal["development", "test", "production"] = "development"
    cookie_secure: bool = False
    allow_insecure_internal_http: bool = False
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    seed_coordinator_password: str | None = None
    seed_admin_password: str | None = None
    allow_homologation_data: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment == "production":
            if not self.cookie_secure and not self.allow_insecure_internal_http:
                raise ValueError(
                    "COOKIE_SECURE deve ser true em produção, salvo quando "
                    "ALLOW_INSECURE_INTERNAL_HTTP=true for explicitamente definido"
                )
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    """Le o .env uma unica vez e reaproveita (cache) durante a vida do processo."""
    return Settings()
