from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import JWT_ALGORITHM, JWT_ALGORITHMS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TaskHub"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "mysql+aiomysql://root@127.0.0.1:3306/taskhub"
    db_echo: bool = False

    # --- Authentication & Authorization
    # SECRET_KEY phải không được để trống: validate ở đây để fail-fast khi env rỗng.
    secret_key: str = Field(
        default="dev-secret-key-change-me-please-32chars-min",
        min_length=32,
    )
    jwt_algorithm: str = JWT_ALGORITHM
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings", "JWT_ALGORITHMS"]
