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

    # API Keys & LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Groq API Configuration (Fast OpenAI-compatible inference)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    EXA_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None

    # Article extraction tuning (prioritize free HTTPX before paid Firecrawl fallback)
    ARTICLE_MIN_CONTENT_LENGTH: int = 200

    # Discovery & Extraction Concurrency Controls
    DISCOVERY_MAX_WORKERS: int = 6
    QUERY_MAX_WORKERS: int = 4
    EXTRACTION_MAX_WORKERS: int = 10
    ANALYSIS_MAX_WORKERS: int = 5
    PER_DOMAIN_MAX_CONCURRENCY: int = 3
    ENABLE_BULK_YOUTUBE_WHISPER: bool = False

    # Optional Bearer/API token for authenticated sensitive endpoints (e.g. LinkedIn enrichment)
    API_AUTH_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

