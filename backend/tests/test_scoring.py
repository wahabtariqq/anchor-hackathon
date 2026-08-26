"""fit_percent units. The shared-fixture agreement with TypeScript lives in test_parity.py."""

from app.scoring import ScoredSkill, fit_percent


def skill(weight: str = "core", depth: str | None = None, checked: bool = False) -> ScoredSkill:
    return ScoredSkill(skill_id="sk", weight=weight, coverage_depth=depth, checked=checked)


def test_empty_role_is_zero_not_a_division_error() -> None:
    assert fit_percent([]) == 0


def test_nothing_covered_is_zero() -> None:
    assert fit_percent([skill(), skill("supporting")]) == 0


def test_everything_fully_covered_is_one_hundred() -> None:
    assert fit_percent([skill(depth="full"), skill("supporting", depth="full")]) == 100


def test_partial_coverage_earns_half_the_weight() -> None:
    assert fit_percent([skill(depth="partial")]) == 50


def test_checked_beats_partial_coursework() -> None:
    assert fit_percent([skill(depth="partial", checked=True)]) == 100


def test_checked_needs_no_coverage_at_all() -> None:
    assert fit_percent([skill(checked=True)]) == 100


def test_core_weighs_three_times_supporting() -> None:
    # one covered core + one missing supporting = 3 of 4
    assert fit_percent([skill(depth="full"), skill("supporting")]) == 75
    # one missing core + one covered supporting = 1 of 4
    assert fit_percent([skill(), skill("supporting", depth="full")]) == 25


def test_rounding_is_half_up_not_bankers() -> None:
    # 1 of 8 = 12.5 -> 13. Python's round() would give 12.
    role = [skill("supporting", depth="full"), skill(), skill(), skill("supporting")]
    assert fit_percent(role) == 13
    # 3 of 8 = 37.5 -> 38. Python's round() would give 38 too, so keep the 12.5 case above.
    role = [skill(depth="full"), skill(), skill("supporting"), skill("supporting")]
    assert fit_percent(role) == 38
