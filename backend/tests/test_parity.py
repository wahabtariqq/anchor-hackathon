"""Python/TypeScript agreement on the v4 fit formula.

Reads the same file as frontend/src/lib/scoring.test.ts. If one suite is green and the other
is off by exactly 1, the cause is banker's vs half-up rounding — see app/scoring.py.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.scoring import ScoredSkill, fit_percent

FIXTURE = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "parity_cases.json"
CASES: list[dict[str, Any]] = json.loads(FIXTURE.read_text())["cases"]


def test_fixture_is_present_and_populated() -> None:
    assert len(CASES) >= 12, f"{FIXTURE} has only {len(CASES)} cases"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_parity_case(case: dict[str, Any]) -> None:
    skills = [
        ScoredSkill(
            skill_id=f"sk_{i}",
            weight=s["weight"],
            coverage_depth=s["coverage_depth"],
            checked=s["checked"],
            verified=s["verified"],
        )
        for i, s in enumerate(case["skills"])
    ]
    assert fit_percent(skills) == case["expected"]
