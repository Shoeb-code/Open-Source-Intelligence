import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Public Appearance Intelligence System"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///./appearance_intelligence.db"

    # Redis & Task queue
    REDIS_URL: str = "redis://localhost:6379/0"
    WORKER_MODE: str = "async_task"  # "async_task" (FastAPI background) or "celery"

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    EXA_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

