from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://nebus:nebus@localhost:5432/nebus",
        alias="DATABASE_URL",
    )
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        alias="RABBITMQ_URL",
    )

    api_key: str = Field(default="local-secret-key-change-me", alias="API_KEY")

    outbox_poll_interval_seconds: float = Field(default=2.0, alias="OUTBOX_POLL_INTERVAL_SECONDS")

    max_retry_attempts: int = Field(default=3, alias="MAX_RETRY_ATTEMPTS")
    retry_base_delay_seconds: float = Field(default=1.0, alias="RETRY_BASE_DELAY_SECONDS")

    webhook_max_attempts: int = Field(default=3, alias="WEBHOOK_MAX_ATTEMPTS")
    webhook_timeout_seconds: float = Field(default=5.0, alias="WEBHOOK_TIMEOUT_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
