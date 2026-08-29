"""DEMO_MODE: the cached analysis path, and the gate that keeps the product live.

The gate is the point. DEMO_MODE alone would serve Ayesha's cached run to every visitor, which
turns the pitch into a video -- judges could not try their own courses (DECISIONS #7). These
tests exist mostly to stop someone "simplifying" the name check away.

Every test passes delay=0 or patches the constant: a 6 s sleep in a unit suite is a bug.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from app.analysis import demo, run_analysis
from app.analysis.client import AnalysisFailed
from app.analysis.schema import AnalysisOut
from app.config import settings


def student(name: str = "Ayesha") -> SimpleNamespace:
    return SimpleNamespace(name=name, semester=4, interests=["Databases", "Security"])


COURSES = [SimpleNamespace(code="CS201", name="DS", curriculum_text="Trees.", semester_tag="past")]


@pytest.fixture
def demo_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_STUDENT_NAME", "Ayesha")
    monkeypatch.setattr(demo, "ANALYSIS_DELAY_SECONDS", 0.0)


class Recorder:
    """A client that must never be reached on the demo path."""

    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, prompt, schema, *, max_tokens, temperature):
        self.calls += 1
        raise AssertionError("the live client was called on the demo path")


# ---- the gate ----------------------------------------------------------------------


def test_applies_for_the_demo_student(demo_on) -> None:
    assert demo.applies(student("Ayesha"))


@pytest.mark.parametrize("name", ["ayesha", "AYESHA", "  Ayesha  "])
def test_the_name_match_is_case_and_whitespace_tolerant(demo_on, name: str) -> None:
    """DECISIONS #41. A demo lost to a lowercase 'ayesha' is not a trade worth making."""
    assert demo.applies(student(name))


def test_does_not_apply_to_any_other_student(demo_on) -> None:
    """The whole reason judges can try their own courses right after the pitch."""
    assert not demo.applies(student("Bilal"))


def test_does_not_apply_when_demo_mode_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    assert not demo.applies(student("Ayesha"))


def test_a_student_with_no_name_does_not_crash_the_gate(demo_on) -> None:
    assert not demo.applies(SimpleNamespace())


# ---- loading the fixture -----------------------------------------------------------


def test_load_returns_a_validated_analysis_and_the_raw_bytes() -> None:
    parsed, raw = demo.load(delay=0)
    assert isinstance(parsed, AnalysisOut)
    assert raw.strip().startswith("{")
    assert len(parsed.roles) == 8


def test_the_committed_fixture_is_the_demo_students_courses() -> None:
    """PRD 12.2. If these codes drift, persist_analysis drops coverage rows with only a log
    warning, and every fit percentage comes out low on stage with nothing explaining why."""
    parsed, _ = demo.load(delay=0)
    assert {c.course_code for c in parsed.coverage} <= {"CS201", "CS301", "CS401", "CS402"}


def test_load_sleeps_so_the_analyzing_screen_reads_as_work() -> None:
    started = time.perf_counter()
    demo.load(delay=0.05)
    assert time.perf_counter() - started >= 0.05


def test_a_missing_fixture_fails_with_a_deploy_shaped_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """contracts/ sits outside backend/. If the host ships only backend/, DEMO_MODE breaks --
    and it breaks during the pitch, so the error has to name the cause."""
    monkeypatch.setattr(demo, "FIXTURE", tmp_path / "nope.json")
    with pytest.raises(AnalysisFailed) as caught:
        demo.load(delay=0)
    assert "contracts/fixtures" in str(caught.value)


def test_the_placeholder_fixture_is_rejected_with_the_command_to_fix_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    stub = tmp_path / "demo_analysis.json"
    stub.write_text('{ "_todo": "not written yet" }', encoding="utf-8")
    monkeypatch.setattr(demo, "FIXTURE", stub)
    with pytest.raises(AnalysisFailed) as caught:
        demo.load(delay=0)
    assert "run_analysis_cli.py --demo --save" in str(caught.value)


def test_a_fixture_that_stopped_validating_fails_here_not_in_persistence(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    bad = tmp_path / "demo_analysis.json"
    bad.write_text('{"skills": [], "coverage": [], "roles": []}', encoding="utf-8")
    monkeypatch.setattr(demo, "FIXTURE", bad)
    with pytest.raises(AnalysisFailed) as caught:
        demo.load(delay=0)
    assert "no longer validates" in str(caught.value)


# ---- the branch in run_analysis ----------------------------------------------------


def test_run_analysis_serves_the_cache_and_never_calls_the_model(demo_on) -> None:
    client = Recorder()
    parsed, raw = run_analysis(student("Ayesha"), COURSES, client=client)
    assert isinstance(parsed, AnalysisOut) and client.calls == 0


def test_run_analysis_calls_the_model_for_everyone_else(demo_on) -> None:
    """DECISIONS #7, and the reason the demo gate is on the name and not just the flag."""
    import json

    from tests.test_validation import valid_payload

    payload = json.dumps(valid_payload())

    class Live:
        def __init__(self) -> None:
            self.calls = 0

        def complete_json(self, prompt, schema, *, max_tokens, temperature):
            self.calls += 1
            return payload, "stop"

    live = Live()
    parsed, raw = run_analysis(student("Bilal"), COURSES, client=live)
    assert live.calls == 1 and raw == payload


def test_run_analysis_is_live_when_demo_mode_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    client = Recorder()
    with pytest.raises(AssertionError, match="live client was called"):
        run_analysis(student("Ayesha"), COURSES, client=client)
