"""Fit %. Pure module — no imports from app, mirrored in frontend/src/lib/scoring.ts.

The model never produces a fit %. This is the whole of "one model call, then arithmetic":
after /api/analyze writes, every number the UI shows comes from here (docs/CONTRACT.md §2).
"""

from dataclasses import dataclass

WEIGHT = {"core": 3, "supporting": 1}
DEPTH = {"full": 1.0, "partial": 0.5}


@dataclass(frozen=True)
class ScoredSkill:
    skill_id: str
    weight: str                    # "core" | "supporting"
    coverage_depth: str | None     # "full" | "partial" | None — already collapsed to the best
    checked: bool


def fit_percent(skills: list[ScoredSkill]) -> int:
    earned = total = 0.0
    for s in skills:
        w = WEIGHT[s.weight]
        total += w
        if s.checked:
            earned += w
        elif s.coverage_depth:
            earned += w * DEPTH[s.coverage_depth]
    # Half-up on purpose: Python's round() is banker's, TS uses Math.floor(x + 0.5).
    # An off-by-one in test_parity.py against scoring.test.ts is always this line.
    return int((earned / total) * 100 + 0.5) if total else 0
