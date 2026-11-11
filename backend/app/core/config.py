from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
    )

    DATABASE_URL: str = (
        "postgresql+asyncpg://content_marketing:content_marketing"
        "@127.0.0.1:5432/content_marketing"
    )
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"


settings = Settings()
