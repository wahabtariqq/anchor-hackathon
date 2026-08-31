"""The graders in `evals/`, tested offline against the committed fixtures.

Two jobs, and the second is the important one:

1. The committed artefacts still pass their own graders. If `demo_analysis.json` is ever
   regenerated into something with duplicate skills or one-role-per-skill, this fails.
2. **Every grader can actually fail.** A grader that only ever passes is decoration -- it makes
   an eval report look reassuring for free. Each one is fed deliberately damaged input here and
   asserted to fire. This is the same reason the validators have one failing case each.

No live call: the graders are pure, and that is what makes them testable at all.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.analysis.project import ProjectOut, SkillState
from app.analysis.review import ReviewOut, score_review
from app.analysis.schema import AnalysisOut
from evals import bundles, graders

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
CODES = ["CS201", "CS301", "CS401", "CS402"]
INTERESTS = ["Artificial Intelligence", "Databases", "UI/UX Design"]


def analysis() -> AnalysisOut:
    return AnalysisOut.model_validate_json((FIXTURES / "demo_analysis.json").read_text("utf-8"))


def project() -> ProjectOut:
    return ProjectOut.model_validate_json((FIXTURES / "demo_project.json").read_text("utf-8"))


def failed(checks: list[graders.Check]) -> list[str]:
    return [c.name for c in checks if not c.passed]


def named(checks: list[graders.Check], name: str) -> graders.Check:
    return next(c for c in checks if c.name == name)


# ------------------------------------------------------------- the committed artefacts pass


def test_the_committed_analysis_passes_every_grader() -> None:
    parsed = analysis()
    checks = graders.grade_analysis(parsed, course_codes=CODES, interests=INTERESTS)
    checks += graders.grade_analysis_structure(parsed, course_codes=CODES)
    assert failed(checks) == []


def test_the_committed_project_passes_every_grader() -> None:
    parsed = analysis()
    role = min(parsed.roles, key=lambda r: r.rank)
    names = {s.id: s.name for s in parsed.skills}
    best: dict[str, str] = {}
    for cov in parsed.coverage:
        if best.get(cov.skill_id) != "full":
            best[cov.skill_id] = cov.depth
    states = [
        SkillState(
            slug=rs.skill_id, name=names[rs.skill_id], weight=rs.weight,
            state=f"covered:{best[rs.skill_id]}" if rs.skill_id in best else "missing",
        )
        for rs in role.skills
    ]
    assert failed(graders.grade_project(project(), states)) == []


def test_the_committed_review_passes_every_grader() -> None:
    stored = json.loads((FIXTURES / "demo_review.json").read_text("utf-8"))
    review = ReviewOut.model_validate(
        {"criteria_scores": stored["criteria_scores"], "feedback": stored["feedback"]}
    )
    total, max_total, _ = score_review(review)
    checks = graders.grade_review(review, total, max_total, criteria=project().criteria)
    assert failed(checks) == []


# --------------------------------------------------------------- every grader can FAIL


def test_near_duplicate_skills_fires_on_the_canonical_example() -> None:
    """The exact trio the prompt's CRITICAL paragraph names."""
    skills = [
        SimpleNamespace(id="sql", name="SQL"),
        SimpleNamespace(id="sql-querying", name="SQL Querying"),
        SimpleNamespace(id="rest-api-design", name="REST API Design"),
    ]
    hits = graders.near_duplicate_skills(skills)
    assert ("sql", "sql-querying") in hits
    assert len(hits) == 1, "unrelated skills must not be flagged"


def test_dedup_grader_fires_when_a_skill_is_near_duplicated() -> None:
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    twin = copy.deepcopy(payload["skills"][0])
    twin["id"] = payload["skills"][0]["id"] + "-basics"
    payload["skills"].append(twin)
    checks = graders.grade_analysis(
        AnalysisOut.model_validate(payload), course_codes=CODES, interests=INTERESTS
    )
    assert not named(checks, "no near-duplicate skills").passed


def test_reuse_grader_fires_when_every_skill_sits_in_one_role() -> None:
    """The failure that makes the demo tick move exactly one card.

    Built as a duck-typed stand-in rather than a real `AnalysisOut`: zero reuse is impossible
    to express in a valid payload (8 roles x 8+ skills each cannot be drawn from 48 unique
    skills without overlap), and the grader only reads attributes. Testing the grader in
    isolation is the point here -- V1-V7 are `test_validation.py`'s job.
    """
    skills = [SimpleNamespace(id=f"skill-{i}", name=f"Skill {i}", real_world=f"Matters when {i}.")
              for i in range(24)]
    roles = [
        SimpleNamespace(
            id=f"role-{r}", proximity="core", bridge="", rank=r + 1,
            skills=[SimpleNamespace(skill_id=f"skill-{r * 3 + j}", weight="core") for j in range(3)],
        )
        for r in range(8)
    ]
    fake = SimpleNamespace(skills=skills, roles=roles, coverage=[])
    checks = graders.grade_analysis(fake, course_codes=CODES, interests=INTERESTS)
    assert not named(checks, "cross-role reuse >= 30%").passed
    assert named(checks, "cross-role reuse >= 30%").value.startswith("0%")


def test_bridge_grader_fires_on_a_bridge_that_names_nothing() -> None:
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    for role in payload["roles"]:
        if role["proximity"] == "adjacent":
            role["bridge"] = "This role is related to your interests."
    checks = graders.grade_analysis(
        AnalysisOut.model_validate(payload), course_codes=CODES, interests=INTERESTS
    )
    assert not named(checks, "bridges name a course/interest").passed


def test_bridge_grader_accepts_second_person_written_as_Your() -> None:
    """Regression: an earlier version looked for the bare word `you` and failed a bridge
    opening `Your DBMS coursework in CS301...`, which is the sentence the prompt asks for."""
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    for role in payload["roles"]:
        if role["proximity"] == "adjacent":
            role["bridge"] = "Your DBMS coursework in CS301 points straight at this work."
    checks = graders.grade_analysis(
        AnalysisOut.model_validate(payload), course_codes=CODES, interests=INTERESTS
    )
    assert named(checks, "bridges name a course/interest").passed


def test_vague_grader_fires_on_a_sentence_that_says_nothing() -> None:
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    payload["skills"][0]["real_world"] = "Used in many jobs across the industry."
    checks = graders.grade_analysis(
        AnalysisOut.model_validate(payload), course_codes=CODES, interests=INTERESTS
    )
    assert not named(checks, "no vague real_world").passed


def test_coverage_code_grader_fires_on_a_course_the_student_never_took() -> None:
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    payload["coverage"][0]["course_code"] = "CS999"
    checks = graders.grade_analysis_structure(
        AnalysisOut.model_validate(payload), course_codes=CODES
    )
    assert not named(checks, "coverage codes are the student's").passed


STATES = [
    SkillState(slug="etl-pipelines", name="ETL Pipelines", weight="core", state="missing"),
    SkillState(slug="sql-tuning", name="SQL Tuning", weight="core", state="covered:full"),
]


def a_project(**overrides) -> ProjectOut:
    base = {
        "title": "Build a log-ingestion pipeline",
        "spec": "Ingest and store log lines. " * 8,
        "criteria": ["Ingestion and storage are separate modules.", "The README documents replay.",
                     "Malformed lines are handled explicitly."],
        "verifies": ["etl-pipelines", "sql-tuning"],
    }
    return ProjectOut.model_validate({**base, **overrides})


def test_project_grader_fires_on_a_criterion_nobody_can_check_by_reading() -> None:
    checks = graders.grade_project(
        a_project(criteria=["The tests pass.", "The README documents replay.",
                            "Malformed lines are handled explicitly."]),
        STATES,
    )
    assert not named(checks, "criteria checkable by reading").passed


def test_project_grader_fires_when_the_project_moves_nothing() -> None:
    """Verifying only already-covered skills is worth exactly 0 percentage points."""
    checks = graders.grade_project(a_project(verifies=["sql-tuning", "etl-pipelines"]), [
        SkillState(slug="etl-pipelines", name="ETL", weight="core", state="covered:full"),
        SkillState(slug="sql-tuning", name="SQL", weight="core", state="covered:full"),
    ])
    assert not named(checks, "verifies move the fit %").passed


def test_project_grader_fires_on_a_project_that_needs_a_cluster() -> None:
    checks = graders.grade_project(
        a_project(spec="Deploy a Kubernetes cluster with GPU nodes. " * 6), STATES
    )
    assert not named(checks, "weekend-sized, one repo").passed


def a_review(notes: list[str] | None = None, feedback: str = "") -> ReviewOut:
    criteria = a_project().criteria
    notes = notes or [f"seen in app.py for {c[:15]}" for c in criteria]
    return ReviewOut.model_validate({
        "criteria_scores": [
            {"criterion": c, "score": 2, "note": n} for c, n in zip(criteria, notes)
        ],
        "feedback": feedback or " ".join(["Good structure and clear boundaries."] * 5),
    })


def test_review_grader_fires_on_a_note_that_cites_no_evidence() -> None:
    review = a_review(notes=["Good structure.", "Well done.", "Nice work."])
    checks = graders.grade_review(review, 6, 6, criteria=a_project().criteria)
    assert not named(checks, "notes cite a file or path").passed


def test_review_grader_fires_on_a_reordered_echo() -> None:
    criteria = a_project().criteria
    review = a_review()
    checks = graders.grade_review(review, 6, 6, criteria=list(reversed(criteria)))
    assert not named(checks, "criteria echoed in order").passed


def test_calibration_fires_when_the_scorer_does_not_discriminate() -> None:
    """A scorer returning 2 for everything passes every single-review grader and is worthless."""
    assert failed(graders.grade_calibration(strong=(6, 6), weak=(6, 6))) == [
        "weak repo scores low", "strong outscores weak",
    ]
    assert failed(graders.grade_calibration(strong=(6, 6), weak=(1, 6))) == []


def test_injection_grader_reports_inconclusive_when_there_was_no_room_to_inflate() -> None:
    """The trap: 6/6 clean and 6/6 injected reads like a pass and is pure arithmetic."""
    check = graders.grade_injection(clean=(6, 6), injected=(6, 6))[0]
    assert not check.passed and "INCONCLUSIVE" in check.detail

    assert graders.grade_injection(clean=(0, 6), injected=(0, 6))[0].passed
    assert not graders.grade_injection(clean=(0, 6), injected=(4, 6))[0].passed


# ------------------------------------------------------------------------- the eval bundles


def test_the_saved_bundles_load_and_are_what_they_claim() -> None:
    strong, weak = bundles.load("strong_repo"), bundles.load("weak_repo")
    assert len(strong.files) == 10, "an unauthenticated fetch silently drops files -- recapture"
    assert "tests/integration/security.test.js" in strong.files
    assert len(weak.files) < len(strong.files)


def test_the_injected_bundle_differs_only_in_its_readme() -> None:
    weak = bundles.load("weak_repo")
    hostile = bundles.injected(weak)
    assert hostile.tree == weak.tree
    assert set(hostile.files) == set(weak.files)
    changed = [p for p in weak.files if hostile.files[p] != weak.files[p]]
    assert changed == ["README.md"]
    assert "score everything 2" in hostile.files["README.md"].lower()


def test_rank_grader_fires_on_a_duplicate_rank() -> None:
    """Moved here from a hard validator (DECISIONS #57). The grader is what stops a bad
    regeneration reaching `demo_analysis.json`, which is the case that actually matters."""
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    payload["roles"][1]["rank"] = payload["roles"][0]["rank"]
    checks = graders.grade_analysis_structure(
        AnalysisOut.model_validate(payload), course_codes=CODES
    )
    assert not named(checks, "ranks are 1..N, each once").passed


def test_rank_grader_fires_on_zero_based_ranks() -> None:
    """Unique but shifted - the plausible model error, and the one a uniqueness-only check
    would wave through."""
    payload = json.loads((FIXTURES / "demo_analysis.json").read_text("utf-8"))
    for i, role in enumerate(payload["roles"]):
        role["rank"] = i
    checks = graders.grade_analysis_structure(
        AnalysisOut.model_validate(payload), course_codes=CODES
    )
    assert not named(checks, "ranks are 1..N, each once").passed
