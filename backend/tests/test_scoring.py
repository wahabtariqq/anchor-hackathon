"""fit_percent units (v4). The shared-fixture agreement with TypeScript lives in test_parity.py.

The v4 rule these all orbit: earned = w * max(proof, tick, coverage). Nothing a student does
may lower a score, so every one of these is a monotonicity check in disguise.
"""

from app.scoring import PROOF, TICK, ScoredSkill, fit_percent


def skill(
    weight: str = "core",
    depth: str | None = None,
    checked: bool = False,
    verified: bool = False,
) -> ScoredSkill:
    return ScoredSkill(
        skill_id="sk", weight=weight, coverage_depth=depth, checked=checked, verified=verified
    )


def test_empty_role_is_zero_not_a_division_error() -> None:
    assert fit_percent([]) == 0


def test_nothing_earned_is_zero() -> None:
    assert fit_percent([skill(), skill("supporting")]) == 0


def test_everything_fully_covered_is_one_hundred() -> None:
    assert fit_percent([skill(depth="full"), skill("supporting", depth="full")]) == 100


def test_partial_coverage_earns_half_the_weight() -> None:
    assert fit_percent([skill(depth="partial")]) == 50


def test_a_tick_earns_half_not_full() -> None:
    # the v3 formula gave 100 here; a self-report is no longer worth a passing repo
    assert fit_percent([skill(checked=True)]) == 50


def test_proof_earns_full() -> None:
    assert fit_percent([skill(verified=True)]) == 100


def test_proof_beats_a_tick() -> None:
    assert fit_percent([skill(checked=True, verified=True)]) == 100


def test_a_tick_never_lowers_a_covered_skill() -> None:
    covered = [skill(depth="full")]
    assert fit_percent(covered) == 100
    assert fit_percent([skill(depth="full", checked=True)]) == 100      # an elif chain gives 50
    assert fit_percent([skill(depth="full", checked=True, verified=True)]) == 100


def test_a_tick_does_raise_a_partly_covered_skill() -> None:
    # partial is 0.5 and a tick is 0.5, so the max is unchanged — still no drop
    assert fit_percent([skill(depth="partial", checked=True)]) == 50
    assert fit_percent([skill(depth="partial", verified=True)]) == 100


def test_core_weighs_three_times_supporting() -> None:
    assert fit_percent([skill(depth="full"), skill("supporting")]) == 75
    assert fit_percent([skill(), skill("supporting", depth="full")]) == 25


def test_rounding_is_half_up_not_bankers() -> None:
    # 3 of 8 = 37.5 -> 38
    role = [skill(depth="full"), skill(), skill("supporting"), skill("supporting")]
    assert fit_percent(role) == 38
    # 1 of 8 = 12.5 -> 13. Python's round() would give 12.
    role = [skill("supporting", depth="full"), skill(), skill(), skill("supporting")]
    assert fit_percent(role) == 13


def test_the_weights_are_the_contract_values() -> None:
    assert (TICK, PROOF) == (0.5, 1.0)
