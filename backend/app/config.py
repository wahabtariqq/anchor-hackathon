"""Settings. Every env read in the backend goes through this module (docs/TDD.md §4.1)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str

    # Which provider app/analysis/ calls. Gemini, over raw REST -- the google-genai SDK
    # 403s with our key while the same key works against the REST endpoint (DECISIONS #45).
    LLM_PROVIDER: str = "gemini"
    # Optional for the same reason as ANTHROPIC_API_KEY below: the API must boot for Salman
    # and Wahab without the AI lane's key.
    GEMINI_API_KEY: str = ""
    # Pinned, never a "-latest" alias: an auto-updating model could change between rehearsal
    # and the demo slot. gemini-2.5-flash is NOT usable -- 404, "no longer available to new
    # users" -- despite still appearing in models.list (DECISIONS #46).
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Declared fallback provider, kept pinned so falling back is a one-class change.
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
