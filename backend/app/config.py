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
    DEMO_REPO_URL: str = ""
    # Optional here so the API boots without it, but set it on the host: unauthenticated
    # GitHub is 60 requests/hour and judge trials would exhaust that (DECISIONS #24).
    # app/github.py logs a warning on every unauthenticated fetch.
    GITHUB_TOKEN: str = ""
    REVIEW_PASS_RATIO: float = 0.6
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()  # type: ignore[call-arg]  # values come from .env / the environment
