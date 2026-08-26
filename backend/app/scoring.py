"""Fit %. Pure module — no imports from app, mirrored in frontend/src/lib/scoring.ts.

The model never produces a fit %. This is the whole of "model calls, then arithmetic": after
/api/analyze writes, every number the UI shows comes from here (docs/CONTRACT.md §2).
"""

from dataclasses import dataclass

WEIGHT = {"core": 3, "supporting": 1}
DEPTH = {"full": 1.0, "partial": 0.5}
TICK = 0.5      # self-report earns half (was 1.0 in v3)
PROOF = 1.0     # a passing repo submission earns full


@dataclass(frozen=True)
class ScoredSkill:
    skill_id: str
    weight: str                    # "core" | "supporting"
    coverage_depth: str | None     # "full" | "partial" | None — already collapsed to the best
    checked: bool
    verified: bool


def fit_percent(skills: list[ScoredSkill]) -> int:
    earned = total = 0.0
    for s in skills:
        w = WEIGHT[s.weight]
        total += w
        # max, never if/elif: no action a student takes may lower a score. An elif chain
        # would drop a fully-covered skill from 1.0 to 0.5 the moment it was ticked.
        earned += w * max(
            PROOF if s.verified else 0.0,
            TICK if s.checked else 0.0,
            DEPTH.get(s.coverage_depth, 0.0) if s.coverage_depth else 0.0,
        )
    # Half-up on purpose: Python's round() is banker's, TS uses Math.floor(x + 0.5).
    # An off-by-one in test_parity.py against scoring.test.ts is always this line.
    return int((earned / total) * 100 + 0.5) if total else 0
