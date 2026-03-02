from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_KEY: str = ""
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/automatic_notice"
    REDIS_URL: str = "redis://redis:6379/0"
    CRAWL_CONCURRENCY: int = 20
    DOWNLOAD_CONCURRENCY: int = 8
    SYNC_CRON: str = "*/30 * * * *"
    STALE_SYNC_MINUTES: int = 10
    NOTICE_SYNC_NOOP_HOURS: int = 6
    ATTACHMENT_PARSE_MAX_MB: int = 20
    RAG_EMBED_BATCH_LIMIT: int = 200


settings = Settings()
