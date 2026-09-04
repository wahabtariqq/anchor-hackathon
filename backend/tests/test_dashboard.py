"""The three V2 read endpoints: /api/dashboard, /api/skills, /api/projects.

Governing docs: TDD-V2 §4.6-§4.8, §6 · PRD-V2 §4.3, §4.5, §4.6.

These are views over tables the V1 lane already fills, so the assertions are mostly about
agreement: what the Dashboard says must be what /api/roadmap says, and what /api/skills reports
about a skill must be what the drawer would show for it.
"""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.analysis as analysis_pkg
import app.routers.submit as submit_module
from app.config import settings
from tests.conftest import (
    DEMO_STUDENT,
    auth_headers,
    create_student,
    persist_demo_analysis,
)


@pytest.fixture
def ai_lane(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"scores": [2, 2, 2]}

    def generate_project(title: str, one_liner: str, skills: list[Any]) -> tuple[Any, str]:
        return (
            SimpleNamespace(
                title="Build a log-ingestion pipeline",
                spec="Ingest, transform and store log lines.",
                criteria=["Has a README", "Parses input", "Stores output"],
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


# The demo student's three best-fit core roles are *fully covered* by their coursework, so no
# tick can move them and every charted next action is the "Review ..." fallback. Enrolling in
# courses the analysis has no coverage rows for leaves every role with real gaps — which is
# what the "Learn X" branch and the chart need in order to be exercised at all.
SPARSE_COURSES = [
    {"course_id": "cs201", "semester_tag": "past"},
    {"course_id": "cs202", "semester_tag": "past"},
    {"course_id": "cs302", "semester_tag": "current"},
]


def onboarded_with_gaps(client: TestClient, session: Session) -> tuple[str, dict[str, str]]:
    student_id = create_student(client, courses=SPARSE_COURSES)
    persist_demo_analysis(session, student_id)
    return student_id, auth_headers(student_id)


def a_role_with_gaps(body: dict[str, Any]) -> dict[str, Any]:
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    return max(
        body["roles"],
        key=lambda r: sum(1 for rs in r["skills"] if depth[rs["skill_id"]] is None),
    )


def an_uncovered_skill(client: TestClient, headers: dict[str, str]) -> str:
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    return next(
        rs["skill_id"] for rs in a_role_with_gaps(body)["skills"] if depth[rs["skill_id"]] is None
    )


def unresolved(skill: dict[str, Any]) -> bool:
    return not (skill["checked"] or skill["verified"] or skill["coverage_depth"])


def a_charted_role_with_gaps(roadmap: dict[str, Any]) -> dict[str, Any]:
    """A role the Dashboard actually charts (a top-3 core role) that still has an unresolved
    skill. The *best*-fit core role can be fully covered in this fixture, in which case its
    next action is the "Review ..." fallback and there is nothing left to tick."""
    by_id = {s["id"]: s for s in roadmap["skills"]}
    top3 = [r for r in roadmap["roles"] if r["proximity"] == "core"][:3]
    return next(
        r for r in top3 if any(unresolved(by_id[rs["skill_id"]]) for rs in r["skills"])
    )


# ------------------------------------------------------------------------------ auth on all 3


@pytest.mark.parametrize("path", ["/api/dashboard", "/api/skills", "/api/projects"])
def test_the_v2_endpoints_401_without_a_token(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ["/api/dashboard", "/api/skills", "/api/projects"])
def test_the_v2_endpoints_404_before_onboarding(client: TestClient, path: str) -> None:
    """Authenticated but no Student yet — the client reads this as "go to /onboarding"
    (docs/CONTRACT.md §6), which is a different answer from 401."""
    from tests.conftest import create_account

    _, headers = create_account(client)
    res = client.get(path, headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"].startswith("No student profile yet")


# --------------------------------------------------------------------------- GET /api/dashboard


def test_dashboard_agrees_with_the_roadmap_about_the_top_role(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    best = next(r for r in roadmap["roles"] if r["proximity"] == "core")

    body = client.get("/api/dashboard", headers=headers).json()

    assert body["top_role"] == {
        "id": best["id"],
        "title": best["title"],
        "fit_percent": best["fit_percent"],
    }


def test_dashboard_counts_match_what_the_student_actually_has(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)
    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    body = client.get("/api/dashboard", headers=headers).json()

    assert body["skills_checked"] == 1
    assert body["skills_verified"] == 0


def test_deltas_are_measured_from_last_seen_at_not_since_ever(
    client: TestClient, session: Session
) -> None:
    """last_seen_at is the login's baseline, and only a login moves it (TDD-V2 §4.4). Events
    from before this visit are history, not "new since your last visit"."""
    email, password = f"delta-{uuid.uuid4().hex[:8]}@example.com", "hunter2-strong"
    client.post("/api/auth/signup", json={"email": email, "password": password, "name": "Ayesha"})
    first = client.post("/api/auth/login", json={"email": email, "password": password}).json()
    headers = {"Authorization": f"Bearer {first['token']}"}
    student_id = client.post("/api/students", json=DEMO_STUDENT, headers=headers).json()["student_id"]
    persist_demo_analysis(session, student_id)

    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    uncovered = [
        rs["skill_id"] for rs in a_role_with_gaps(body)["skills"] if depth[rs["skill_id"]] is None
    ][:2]
    assert len(uncovered) == 2

    client.post("/api/progress", json={"skill_id": uncovered[0], "checked": True}, headers=headers)
    assert client.get("/api/dashboard", headers=headers).json()["checked_delta"] == 1

    # log in again: a new visit begins, so the first tick is now history
    second = client.post("/api/auth/login", json={"email": email, "password": password}).json()
    headers = {"Authorization": f"Bearer {second['token']}"}
    assert client.get("/api/dashboard", headers=headers).json()["checked_delta"] == 0

    client.post("/api/progress", json={"skill_id": uncovered[1], "checked": True}, headers=headers)
    assert client.get("/api/dashboard", headers=headers).json()["checked_delta"] == 1


def test_an_untick_cancels_a_tick_in_the_delta(client: TestClient, session: Session) -> None:
    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)

    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)
    client.post("/api/progress", json={"skill_id": skill_id, "checked": False}, headers=headers)

    assert client.get("/api/dashboard", headers=headers).json()["checked_delta"] == 0


def test_the_chart_starts_empty_and_gains_a_point_per_move(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded_with_gaps(client, session)
    first = client.get("/api/dashboard", headers=headers).json()
    assert all(points == [] for points in first["snapshots"].values()), "no backfill (PRD-V2 §6.1)"

    roadmap = client.get("/api/roadmap", headers=headers).json()
    by_id = {s["id"]: s for s in roadmap["skills"]}
    role = a_charted_role_with_gaps(roadmap)
    skill_id = next(rs["skill_id"] for rs in role["skills"] if unresolved(by_id[rs["skill_id"]]))
    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    after = client.get("/api/dashboard", headers=headers).json()
    assert len(after["snapshots"][role["id"]]) == 1
    assert after["snapshots"][role["id"]][0]["fit"] > 0


def test_snapshots_are_keyed_by_the_top_three_core_roles(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    expected = [r["id"] for r in roadmap["roles"] if r["proximity"] == "core"][:3]

    body = client.get("/api/dashboard", headers=headers).json()

    assert list(body["snapshots"].keys()) == expected
    assert [a["role_id"] for a in body["next_actions"]] == expected


def test_next_action_names_the_highest_weight_unresolved_skill(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded_with_gaps(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    by_id = {s["id"]: s for s in roadmap["skills"]}
    role = a_charted_role_with_gaps(roadmap)
    # build_roadmap sorts role.skills core-first, so "first unresolved" is "highest weight"
    expected = next(
        by_id[rs["skill_id"]]["name"] for rs in role["skills"] if unresolved(by_id[rs["skill_id"]])
    )

    actions = client.get("/api/dashboard", headers=headers).json()["next_actions"]
    action = next(a for a in actions if a["role_id"] == role["id"])

    assert action == {"role_id": role["id"], "label": f"Learn {expected}", "kind": "tick"}


def test_a_fully_covered_role_falls_back_to_review(
    client: TestClient, session: Session
) -> None:
    """Nothing unresolved and nothing to prove - the role is as done as ticking can make it,
    so the card says "Review" rather than inventing work."""
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    by_id = {s["id"]: s for s in roadmap["skills"]}
    top3 = [r for r in roadmap["roles"] if r["proximity"] == "core"][:3]
    done = [r for r in top3 if not any(unresolved(by_id[rs["skill_id"]]) for rs in r["skills"])]
    assert done, "the demo student's top core roles are fully covered — that is the case here"

    payload = client.get("/api/dashboard", headers=headers).json()
    actions = {a["role_id"]: a for a in payload["next_actions"]}

    for role in done:
        assert actions[role["id"]] == {
            "role_id": role["id"],
            "label": f"Review {role['title']}",
            "kind": "tick",
        }


def test_next_action_stops_naming_a_skill_once_it_is_ticked(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded_with_gaps(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    role = a_charted_role_with_gaps(roadmap)
    actions = client.get("/api/dashboard", headers=headers).json()["next_actions"]
    first = next(a for a in actions if a["role_id"] == role["id"])
    named = next(s for s in roadmap["skills"] if first["label"] == f"Learn {s['name']}")

    client.post("/api/progress", json={"skill_id": named["id"], "checked": True}, headers=headers)

    actions = client.get("/api/dashboard", headers=headers).json()["next_actions"]
    second = next(a for a in actions if a["role_id"] == role["id"])
    assert second["label"] != first["label"], "a ticked skill cannot still be the next thing to learn"


def test_an_unfinished_project_outranks_a_missing_skill(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    """A project verifies several skills at once and is the only thing that can push fit past
    a self-report, so it's the better "what now" (TDD-V2 §4.6)."""
    ai_lane["scores"] = [0, 0, 0]
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    role = next(r for r in roadmap["roles"] if r["proximity"] == "core")
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    action = next(
        a
        for a in client.get("/api/dashboard", headers=headers).json()["next_actions"]
        if a["role_id"] == role["id"]
    )

    assert action["kind"] == "project"
    assert action["label"].startswith("Finish Build a log-ingestion pipeline — verifies ")


def test_a_passed_project_stops_being_the_next_action(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    role = next(r for r in roadmap["roles"] if r["proximity"] == "core")
    client.get(f"/api/project?role_id={role['id']}", headers=headers)
    client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    action = next(
        a
        for a in client.get("/api/dashboard", headers=headers).json()["next_actions"]
        if a["role_id"] == role["id"]
    )

    assert action["kind"] == "tick"


def test_the_activity_feed_is_newest_first_and_capped_at_ten(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    skill_ids = [s["id"] for s in roadmap["skills"]][:12]

    for skill_id in skill_ids:
        client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    feed = client.get("/api/dashboard", headers=headers).json()["recent_events"]

    assert len(feed) == 10
    assert [e["at"] for e in feed] == sorted((e["at"] for e in feed), reverse=True)
    names = {s["id"]: s["name"] for s in roadmap["skills"]}
    assert feed[0]["text"] == f"Marked {names[skill_ids[-1]]} as learned"


def test_the_feed_reads_names_at_read_time_not_write_time(
    client: TestClient, session: Session
) -> None:
    """humanize joins ids back to names on every read, so a rename can't leave a stale
    sentence in the feed."""
    from app.models import Skill

    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)
    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    skill = session.get(Skill, skill_id)
    assert skill is not None
    skill.name = "Renamed Skill"
    session.add(skill)
    session.commit()

    feed = client.get("/api/dashboard", headers=headers).json()["recent_events"]
    assert feed[0]["text"] == "Marked Renamed Skill as learned"


def test_a_submission_reads_as_two_sentences(
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

    texts = [e["text"] for e in client.get("/api/dashboard", headers=headers).json()["recent_events"]]

    assert f"Submitted a repo for {role['title']}" in texts
    assert f"Verified skills for {role['title']} via repo review" in texts


def test_one_account_never_sees_another_accounts_dashboard(
    client: TestClient, session: Session
) -> None:
    first_id, first_headers = onboarded(client, session)
    second_id, second_headers = onboarded(client, session)
    client.post(
        "/api/progress",
        json={"skill_id": an_uncovered_skill(client, first_headers), "checked": True},
        headers=first_headers,
    )

    second = client.get("/api/dashboard", headers=second_headers).json()

    assert second["skills_checked"] == 0
    assert second["recent_events"] == []
    assert all(points == [] for points in second["snapshots"].values())


# ------------------------------------------------------------------------------ GET /api/skills


def test_skills_returns_every_skill_in_roadmap_order(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()

    body = client.get("/api/skills", headers=headers).json()

    assert [s["id"] for s in body["skills"]] == [s["id"] for s in roadmap["skills"]]


def test_a_skill_row_cannot_disagree_with_the_drawer(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)
    skill_id = an_uncovered_skill(client, headers)
    client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)
    roadmap = client.get("/api/roadmap", headers=headers).json()

    rows = {s["id"]: s for s in client.get("/api/skills", headers=headers).json()["skills"]}

    for skill in roadmap["skills"]:
        row = rows[skill["id"]]
        assert (row["checked"], row["verified"], row["coverage_depth"]) == (
            skill["checked"],
            skill["verified"],
            skill["coverage_depth"],
        )


def test_each_skill_lists_every_role_that_wants_it(
    client: TestClient, session: Session
) -> None:
    """One row, many roles — invariant #1 made visible (PRD-V2 §4.5)."""
    student_id, headers = onboarded(client, session)
    roadmap = client.get("/api/roadmap", headers=headers).json()
    expected: dict[str, list[str]] = {s["id"]: [] for s in roadmap["skills"]}
    for role in roadmap["roles"]:
        for member in role["skills"]:
            expected[member["skill_id"]].append(role["id"])

    body = client.get("/api/skills", headers=headers).json()

    for row in body["skills"]:
        assert [r["id"] for r in row["roles"]] == expected[row["id"]]
    assert any(len(row["roles"]) > 1 for row in body["skills"]), "a shared skill must exist"


# ---------------------------------------------------------------------------- GET /api/projects


def test_projects_is_empty_before_prove_it_is_opened(
    client: TestClient, session: Session
) -> None:
    student_id, headers = onboarded(client, session)

    assert client.get("/api/projects", headers=headers).json() == {"projects": []}


def test_a_generated_project_appears_with_no_submissions(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    single = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()

    body = client.get("/api/projects", headers=headers).json()

    assert len(body["projects"]) == 1
    assert body["projects"][0]["project"] == single, "the plural view must not reshape a project"
    assert body["projects"][0]["submissions"] == []


def test_submission_history_is_newest_first_with_its_notes(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id, headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    ai_lane["scores"] = [0, 0, 0]
    client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/first"},
        headers=headers,
    )
    ai_lane["scores"] = [2, 2, 2]
    client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/second"},
        headers=headers,
    )

    history = client.get("/api/projects", headers=headers).json()["projects"][0]["submissions"]

    assert [s["repo_url"] for s in history] == [
        "https://github.com/o/second",
        "https://github.com/o/first",
    ], "newest first — a resubmit belongs at the top"
    assert [s["passed"] for s in history] == [True, False], "a failed attempt is never erased"
    assert history[0]["feedback"] == "Solid structure, thin on tests."
    assert len(history[0]["criteria_scores"]) == 3
    assert history[0]["total"] == 6 and history[0]["max_total"] == 6


def test_projects_covers_every_role_at_once(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    """The whole reason the plural endpoint exists: /api/project?role_id= answers for one role
    at a time, and this screen renders them all (PRD-V2 §4.6)."""
    student_id, headers = onboarded(client, session)
    roles = client.get("/api/roadmap", headers=headers).json()["roles"][:3]
    for role in roles:
        client.get(f"/api/project?role_id={role['id']}", headers=headers)

    body = client.get("/api/projects", headers=headers).json()

    assert {p["project"]["role_id"] for p in body["projects"]} == {r["id"] for r in roles}


def test_one_account_never_sees_another_accounts_projects(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    first_id, first_headers = onboarded(client, session)
    second_id, second_headers = onboarded(client, session)
    role = a_role_with_gaps(client.get("/api/roadmap", headers=first_headers).json())
    client.get(f"/api/project?role_id={role['id']}", headers=first_headers)

    assert client.get("/api/projects", headers=second_headers).json() == {"projects": []}
