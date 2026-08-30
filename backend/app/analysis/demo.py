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

import json
import time
from pathlib import Path
from typing import Any

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


# --------------------------------------------------------------------------------------
# The Prove It caches (S8). Both fixtures, the demo repo and demo_project.json's criteria
# must agree; they are regenerated together or not at all (PRD §14).
# --------------------------------------------------------------------------------------

PROJECT_FIXTURE = FIXTURE.parent / "demo_project.json"
REVIEW_FIXTURE = FIXTURE.parent / "demo_review.json"

# CONTRACT §3 advertises 3-10 s for a live GET /project. Unlike the analysis and submit paths,
# `routers/project.py` does NOT sleep before calling this -- so the delay has to live here or
# the panel snaps open instantly and reads as canned. The submit path is the mirror image:
# `routers/submit.py` sleeps DEMO_SLEEP_SECONDS = 4 itself, so `load_demo_review` must not
# sleep at all, or the demo waits eight seconds for a cached file.
PROJECT_DELAY_SECONDS = 3.0


def _read_fixture(path, what: str) -> str:
    """Shared preflight: a missing or placeholder fixture fails with a sentence that names the
    command that fixes it, rather than a KeyError three frames deeper."""
    if not path.exists():
        raise AnalysisFailed(
            f"DEMO_MODE is on but {path} is missing. The deployed host must ship "
            "contracts/fixtures/ alongside backend/, or the demo path cannot work."
        )
    raw = path.read_text(encoding="utf-8")
    if '"_todo"' in raw:
        raise AnalysisFailed(f"{path} is still the placeholder. Run: {what}")
    return raw


def load_project(*, delay: float | None = None):
    """The committed demo project, validated, after a short delay. Returns a `ProjectOut`.

    One value, not a tuple: `routers/project.py:155` does `out = load_demo()` and then reads
    `out.title` / `out.spec` / `out.criteria` / `out.verifies`. `generate_project`'s
    `(parsed, raw)` shape is the live path's, and it is unpacked separately in his `else`
    branch -- returning a tuple here would hand him a tuple with no `.verifies`.

    Validated on the way out, as the analysis fixture is: a project that stopped satisfying
    CONTRACT §1b would otherwise surface mid-pitch as an AttributeError in his router.
    """
    from app.analysis.project import ProjectOut

    raw = _read_fixture(PROJECT_FIXTURE, "python scripts/run_project_cli.py --save")
    try:
        parsed = ProjectOut.model_validate_json(raw)
    except Exception as exc:
        raise AnalysisFailed(f"demo project fixture no longer validates: {exc}") from exc

    time.sleep(PROJECT_DELAY_SECONDS if delay is None else delay)
    return parsed


def load_review(project) -> tuple[Any, int, int, bool]:
    """The committed demo review, as `(review, total, max_total, passed)`.

    **No sleep here.** `routers/submit.py` sleeps 4 s before calling this (its
    `DEMO_SLEEP_SECONDS`), so a delay in this function would be added to that one.

    `total`, `max_total` and `passed` are **recomputed** from the scores rather than trusted
    from the file, then checked against the stored values. The fixture carries them because
    CONTRACT §4 says it does, but `score_review` stays the only thing that decides a pass -- so
    a hand-edited fixture, or one saved before REVIEW_PASS_RATIO changed, fails here with a
    legible message instead of showing judges a review whose numbers contradict its own scores.

    The criteria echo is re-checked against the project for the same reason: these two fixtures
    and the demo repo are one artefact in three files, and this is where a partial regeneration
    is caught.
    """
    from app.analysis.review import ReviewOut, check_criteria_echo, score_review

    raw = _read_fixture(REVIEW_FIXTURE, "python scripts/run_review_cli.py --url $DEMO_REPO_URL --save")
    try:
        stored = json.loads(raw)
        review = ReviewOut.model_validate(
            {"criteria_scores": stored["criteria_scores"], "feedback": stored["feedback"]}
        )
    except Exception as exc:
        raise AnalysisFailed(f"demo review fixture no longer validates: {exc}") from exc

    try:
        check_criteria_echo(project.criteria, review)
    except ValueError as exc:
        raise AnalysisFailed(
            f"{REVIEW_FIXTURE} does not match demo_project.json's criteria: {exc}. "
            "The project, the demo repo and the review are regenerated together or not at all."
        ) from exc

    total, max_total, passed = score_review(review)
    for name, computed in (("total", total), ("max_total", max_total), ("passed", passed)):
        if name in stored and stored[name] != computed:
            raise AnalysisFailed(
                f"{REVIEW_FIXTURE} says {name}={stored[name]!r} but the scores compute "
                f"{computed!r} -- do not hand-edit this fixture"
            )
    return review, total, max_total, passed
