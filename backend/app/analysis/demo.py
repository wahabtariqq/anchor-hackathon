"""DEMO_MODE: serve the committed analysis instead of calling the model (PRD 12.1).

Gated on DEMO_MODE **and** the student's name, never on DEMO_MODE alone (DECISIONS #7). That
gate is the whole reason judges can try their own input right after the pitch: Ayesha gets the
cached run, anyone else gets a real call. Losing the name check turns a live product into a
video.

This matters more than it did when it was written. The free tier returned 503 "high demand" on
two different models during S0, and live latency measured 53-102 s. The cached path is not a
nicety any more -- it is what the 75-second script actually runs on.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.analysis.client import AnalysisFailed
from app.analysis.schema import AnalysisOut
from app.config import settings

# backend/app/analysis/demo.py -> repo root -> contracts/
FIXTURE = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "demo_analysis.json"

# PRD 12.1. The Analyzing screen shows staged copy at 0s and 12s, so ~6s reads as real work
# without the second line ever appearing. Shorter looks fake; longer wastes the pitch.
ANALYSIS_DELAY_SECONDS = 6.0


def applies(student) -> bool:
    """True only for the demo student, and only when DEMO_MODE is on.

    Case-insensitive and whitespace-tolerant (DECISIONS #41): PRD 12.1 writes `==`, but a demo
    lost to a lowercase "ayesha" is not a trade worth making. Salman's routers already match the
    same way, so the three demo paths agree.
    """
    if not settings.DEMO_MODE:
        return False
    name = getattr(student, "name", "") or ""
    return name.strip().lower() == settings.DEMO_STUDENT_NAME.strip().lower()


def load(*, delay: float | None = None) -> tuple[AnalysisOut, str]:
    """Return the committed fixture as `(parsed, raw)` -- the same shape as a live call.

    Validated on the way out even though it is a file we committed ourselves: a fixture that
    silently stopped satisfying V1-V6 would fail later inside `persist_analysis`, mid-demo, as
    an opaque database error rather than a legible one here.

    The delay happens **after** validation so a broken fixture fails immediately instead of
    six seconds later. `delay=0` in tests.
    """
    if not FIXTURE.exists():
        raise AnalysisFailed(
            f"DEMO_MODE is on but {FIXTURE} is missing. The deployed host must ship "
            "contracts/fixtures/ alongside backend/, or the demo path cannot work."
        )

    raw = FIXTURE.read_text(encoding="utf-8")
    if '"_todo"' in raw:
        raise AnalysisFailed(
            f"{FIXTURE} is still the placeholder. Run: "
            "python scripts/run_analysis_cli.py --demo --save"
        )

    try:
        parsed = AnalysisOut.model_validate_json(raw)
    except Exception as exc:
        raise AnalysisFailed(f"demo fixture no longer validates: {exc}") from exc

    time.sleep(ANALYSIS_DELAY_SECONDS if delay is None else delay)
    return parsed, raw
