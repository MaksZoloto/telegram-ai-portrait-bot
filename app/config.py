from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr | None = Field(default=None, alias="BOT_TOKEN")
    run_bot: bool = Field(default=False, alias="RUN_BOT")
    public_base_url: str = Field(default="http://localhost:8090", alias="PUBLIC_BASE_URL")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/runtime/ai_portrait_demo.db",
        alias="DATABASE_URL",
    )
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    starter_credits: int = Field(default=3, alias="STARTER_CREDITS")

    leonardo_api_key: SecretStr | None = Field(default=None, alias="LEONARDO_API_KEY")
    leonardo_model_id: str | None = Field(default=None, alias="LEONARDO_MODEL_ID")
    generation_timeout_sec: int = Field(default=120, alias="GENERATION_TIMEOUT_SEC")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8090, alias="PORT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
