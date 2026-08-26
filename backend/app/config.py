"""Settings. Every env read in the backend goes through this module (docs/TDD.md §4.1)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # Optional so the API boots without the AI lane's key — nothing outside app/analysis/
    # reads it, and app/analysis/ is imported lazily (see routers/analyze.py).
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANALYSIS_MAX_TOKENS: int = 16000
    ANALYSIS_RETRY_MAX_TOKENS: int = 24000
    DEMO_MODE: bool = False
    DEMO_STUDENT_NAME: str = "Ayesha"
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()  # type: ignore[call-arg]  # values come from .env / the environment
