"""Is this deployment actually going to work? — answered without a login or a shell.

The failure this exists for: `contracts/fixtures/` sits *outside* `backend/`, and
app/analysis/demo.py resolves it as `parents[3]`. A host configured with a root directory of
`backend/` builds green, serves /health green, and then fails on the demo path in front of
judges. That is discoverable in one curl instead of on stage.

Booleans only. Never report a key's value, only whether it is set.
"""

from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session

from app.config import settings
from app.db import engine

# app/readiness.py -> app -> backend -> repo root. Must agree with FIXTURE in
# app/analysis/demo.py (which counts from app/analysis/); tests/test_readiness.py pins them
# together so a move on either side fails loudly rather than at pitch time.
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
DEMO_FIXTURES = ("demo_analysis.json", "demo_project.json", "demo_review.json")


def missing_demo_fixtures() -> list[str]:
    return [name for name in DEMO_FIXTURES if not (FIXTURES_DIR / name).is_file()]


def database_reachable() -> bool:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))  # type: ignore[call-overload]
        return True
    except Exception:
        return False


def readiness() -> dict[str, object]:
    missing = missing_demo_fixtures()
    return {
        "ok": True,                                   # the process is up; that is what the host asks
        "database": database_reachable(),
        "demo_mode": settings.DEMO_MODE,
        # only meaningful when DEMO_MODE is on, but reported always so it can be checked
        # before flipping the switch on the day
        "demo_fixtures_present": not missing,
        "missing_demo_fixtures": missing,
        "demo_repo_url_set": bool(settings.DEMO_REPO_URL),
        "llm_key_set": bool(settings.GEMINI_API_KEY or settings.ANTHROPIC_API_KEY),
        "github_token_set": bool(settings.GITHUB_TOKEN),
        "cors_origins": [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    }
