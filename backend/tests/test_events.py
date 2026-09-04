"""The V2 write path: Event rows, FitSnapshot rows, and the narrow fit_by_role helper.

Governing docs: TDD-V2 §4.2, §4.5, §5.2, §5.3 · PRD-V2 §6.1.

Nothing here calls the model. The AI-lane stubs mirror test_project_review.py's, since the
submission half of this path runs through the same routers.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.analysis as analysis_pkg
import app.routers.submit as submit_module
from app.config import settings
from app.events import fit_by_role
from app.models import Event, FitSnapshot, Student
from app.routers.roadmap import build_roadmap
from tests.conftest import auth_headers, create_student, persist_demo_analysis


@pytest.fixture
def ai_lane(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"scores": [2, 2, 2]}

    def generate_project(title: str, one_liner: str, skills: list[Any]) -> tuple[Any, str]:
        return (
            SimpleNamespace(
                title="Build a log-ingestion pipeline",
                spec="Ingest, transform and store log lines.",
                criteria=["Has a README", "Parses input", "Stores output"],
                # skills the student is missing — verifying an already-covered one moves
                # nothing, since fit_percent takes a max (DECISIONS #3)
                verifies=([s.slug for s in skills if s.state == "missing"] or
                          [s.slug for s in skills])[:2],
            ),
            "{}",
        )

    def review_repo(project: Any, bundle: Any) -> tuple[Any, int, int, bool]:
        scores = state["scores"]
        review = SimpleNamespace(
            criteria_scores=[
                {"criterion": c, "score": s, "note": "seen in the repo"}
                for c, s in zip(project.criteria, scores)
            ],
            feedback="Solid structure, thin on tests.",
        )
        review.model_dump = lambda: {  # type: ignore[attr-defined]
            "criteria_scores": review.criteria_scores,
            "feedback": review.feedback,
        }
        total, max_total = sum(scores), 2 * len(project.criteria)
        return review, total, max_total, total >= math.ceil(settings.REVIEW_PASS_RATIO * max_total)

    monkeypatch.setattr(analysis_pkg, "generate_project", generate_project, raising=False)
    monkeypatch.setattr(analysis_pkg, "review_repo", review_repo, raising=False)
    monkeypatch.setattr(submit_module, "fetch_repo", lambda url: SimpleNamespace(files={}, tree=[]))
    return state


def onboarded(client: TestClient, session: Session) -> tuple[str, dict[str, str]]:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    return student_id, auth_headers(student_id)


def a_role_with_gaps(body: dict[str, Any]) -> dict[str, Any]:
    """The role with the most uncovered skills. roles[0] is the *best-fit* role, which in this
    fixture can be fully covered — picking it would leave nothing to tick."""
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    return max(
        body["roles"],
        key=lambda r: sum(1 for rs in r["skills"] if depth[rs["skill_id"]] is None),
    )


def an_uncovered_skill(client: TestClient, headers: dict[str, str]) -> str:
    """A skill no course covers, so ticking it actually moves a role's fit."""
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    role = a_role_with_gaps(body)
    return next(rs["skill_id"] for rs in role["skills"] if depth[rs["skill_id"]] is None)


def a_fully_covered_skill(client: TestClient, headers: dict[str, str]) -> str:
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    return next(
        rs["skill_id"] for rs in a_role_with_gaps(body)["skills"] if depth[rs["skill_id"]] == "full"
    )


# ------------------------------------------------------------------------------- tick events


def test_a_tick_writes_exactly_one_event(client: TestClient, session: Session) -> None:
    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)

    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    events = session.exec(select(Event)).all()
    assert len(events) == 1
    assert (events[0].type, events[0].skill_id) == ("tick", skill_id)


def test_an_untick_is_its_own_event_type(client: TestClient, session: Session) -> None:
    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)

    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)
    client.post("/api/progress", json={"skill_id": skill_id, "checked": False}, headers=headers)

    assert [e.type for e in session.exec(select(Event)).all()] == ["tick", "untick"]


def test_a_rejected_tick_writes_no_event(client: TestClient, session: Session) -> None:
    """404 on an unknown skill must roll back cleanly — no orphan event for a write that
    never happened."""
    student_id, headers = onboarded(client, session)

    res = client.post(
        "/api/progress", json={"skill_id": "not-a-skill", "checked": True}, headers=headers
    )

    assert res.status_code == 404
    assert session.exec(select(Event)).all() == []
    assert session.exec(select(FitSnapshot)).all() == []


# --------------------------------------------------------------------------------- snapshots


def test_a_tick_snapshots_only_the_roles_whose_fit_moved(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    skill_id = next(
        rs["skill_id"] for rs in a_role_with_gaps(body)["skills"] if depth[rs["skill_id"]] is None
    )
    wants_it = {r["id"] for r in body["roles"] if any(rs["skill_id"] == skill_id for rs in r["skills"])}

    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    rows = session.exec(select(FitSnapshot)).all()
    assert {r.role_id for r in rows} == wants_it, "only roles containing the skill may move"
    after = {r["id"]: r["fit_percent"] for r in client.get("/api/roadmap", headers=headers).json()["roles"]}
    for row in rows:
        assert row.fit_percent == after[row.role_id], "the snapshot must equal what /roadmap says"


def test_ticking_an_already_fully_covered_skill_snapshots_nothing(
    client: TestClient, session: Session
) -> None:
    """fit_percent takes a max (DECISIONS #3), so a full-coverage skill is already worth 1.0.
    Writing a point here would put a flat kink in a chart that should stay straight."""
    student_id, headers = onboarded(client, session)
    skill_id = a_fully_covered_skill(client, headers)

    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    assert len(session.exec(select(Event)).all()) == 1, "the tick still happened, so it's logged"
    assert session.exec(select(FitSnapshot)).all() == [], "but nothing moved, so nothing charted"


def test_snapshots_accumulate_into_a_history(client: TestClient, session: Session) -> None:
    student_id, headers = onboarded(client, session)
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    role = a_role_with_gaps(body)
    uncovered = [rs["skill_id"] for rs in role["skills"] if depth[rs["skill_id"]] is None][:2]
    assert len(uncovered) == 2

    for skill_id in uncovered:
        client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    points = session.exec(
        select(FitSnapshot).where(FitSnapshot.role_id == role["id"])
    ).all()
    fits = [p.fit_percent for p in sorted(points, key=lambda p: (p.created_at, p.id))]
    assert len(fits) == 2 and fits[0] < fits[1], "the line has to go up, not just exist"


# ------------------------------------------------------------------------------- fit_by_role


def test_fit_by_role_agrees_with_the_roadmap_it_shortcuts(
    client: TestClient, session: Session
) -> None:
    """The narrow helper exists so a tick doesn't rebuild the whole roadmap twice. This is the
    test that stops it drifting from build_roadmap's own arithmetic."""
    student_id, headers = onboarded(client, session)
    body = client.get("/api/roadmap", headers=headers).json()
    skill_ids = [s["id"] for s in body["skills"]]
    student = session.get(Student, student_id)
    assert student is not None

    narrow = fit_by_role(session, student, skill_ids)
    full = {r.id: r.fit_percent for r in build_roadmap(session, student).roles}

    assert narrow == full


def test_fit_by_role_is_empty_when_nothing_is_affected(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    student = session.get(Student, student_id)
    assert student is not None

    assert fit_by_role(session, student, []) == {}
    assert fit_by_role(session, student, ["no-such-skill"]) == {}


# ------------------------------------------------------------------------- submission events


def test_a_passing_submission_writes_both_a_submission_and_a_pass_event(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    res = client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    assert res.status_code == 200 and res.json()["review"]["passed"] is True
    events = session.exec(select(Event)).all()
    assert sorted(e.type for e in events) == ["pass", "submission"]
    assert all(e.role_id == role["id"] and e.submission_id for e in events)


def test_a_failing_submission_writes_no_pass_event(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    ai_lane["scores"] = [0, 0, 0]
    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    res = client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    assert res.json()["review"]["passed"] is False
    assert [e.type for e in session.exec(select(Event)).all()] == ["submission"]
    assert session.exec(select(FitSnapshot)).all() == [], "a miss verifies nothing, so fit is flat"


def test_a_passing_submission_snapshots_the_roles_it_moved(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    rows = session.exec(select(FitSnapshot)).all()
    assert rows, "verifying skills has to move at least the role that was submitted"
    after = {
        r["id"]: r["fit_percent"]
        for r in client.get("/api/roadmap", headers=headers).json()["roles"]
    }
    for row in rows:
        assert row.fit_percent == after[row.role_id]


def test_a_failed_fetch_writes_neither_event_nor_snapshot(
    client: TestClient, session: Session, ai_lane: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.github import RepoError

    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    def refuse(url: str) -> Any:
        raise RepoError("That repo isn't public or doesn't exist")

    monkeypatch.setattr(submit_module, "fetch_repo", refuse)
    res = client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    assert res.status_code == 422
    assert session.exec(select(Event)).all() == []
    assert session.exec(select(FitSnapshot)).all() == []


# ------------------------------------------------------------------------------- ownership


def test_events_are_scoped_to_the_account_that_made_them(
    client: TestClient, session: Session
) -> None:
    first_id, first_headers = onboarded(client, session)
    second_id, second_headers = onboarded(client, session)

    client.post(
        "/api/progress",
        json={"skill_id": an_uncovered_skill(client, first_headers), "checked": True},
        headers=first_headers,
    )

    first_user = session.get(Student, first_id)
    second_user = session.get(Student, second_id)
    assert first_user is not None and second_user is not None
    owners = {e.user_id for e in session.exec(select(Event)).all()}
    assert owners == {first_user.user_id}
    assert second_user.user_id not in owners
