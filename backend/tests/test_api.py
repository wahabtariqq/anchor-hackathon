"""The endpoints, end to end on in-memory SQLite.

Beyond TDD §12's three files (logged in DECISIONS.md): persistence.py and build_roadmap are
the trickiest code in the lane and §12 leaves both uncovered. Everything here is fast and
hits real HTTP + real SQL, no mocks.
"""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Coverage, Progress, Skill, Student, StudentCourse
from app.persistence import persist_analysis
from tests.conftest import DEMO_STUDENT, make_analysis


def create_demo(client: TestClient, **overrides: Any) -> str:
    body = {**DEMO_STUDENT, **overrides}
    res = client.post("/api/students", json=body)
    assert res.status_code == 201, res.text
    return res.json()["student_id"]


def analyse(session: Session, student_id: str) -> None:
    courses = session.exec(
        select(StudentCourse).where(StudentCourse.student_id == student_id)
    ).all()
    persist_analysis(session, student_id, make_analysis(), json.dumps({"stub": True}), list(courses))


# ---- GET /api/courses ----


def test_courses_is_public_and_returns_the_catalog(client: TestClient) -> None:
    res = client.get("/api/courses")
    assert res.status_code == 200
    courses = res.json()["courses"]
    assert len(courses) == 10
    assert [c["id"] for c in courses] == sorted(c["id"] for c in courses)
    assert set(courses[0]) == {"id", "code", "name", "curriculum_text"}


# ---- POST /api/students ----


def test_create_student_resolves_codes_and_curriculum(client: TestClient, session: Session) -> None:
    student_id = create_demo(
        client,
        courses=[
            {"course_id": "cs201", "semester_tag": "past"},
            {"course_id": "cs301", "semester_tag": "past", "curriculum_override": "Our own outline."},
            {"course_id": "cs401", "semester_tag": "current"},
            {
                "custom_name": "  Human-Computer Interaction  ",
                "semester_tag": "current",
                "curriculum_text": "Heuristic evaluation, wireframing, usability testing, interaction design.",
            },
        ],
    )
    rows = session.exec(
        select(StudentCourse).where(StudentCourse.student_id == student_id)
    ).all()
    by_code = {r.code: r for r in rows}
    assert set(by_code) == {"CS201", "CS301", "CS401", "CUSTOM-1"}
    assert by_code["CS301"].curriculum_text == "Our own outline."          # override wins
    assert by_code["CS201"].curriculum_text.startswith("Arrays, linked lists")  # catalog default
    assert by_code["CUSTOM-1"].name == "Human-Computer Interaction"        # stripped
    assert by_code["CUSTOM-1"].course_id is None


def test_each_onboarding_creates_a_new_student(client: TestClient, session: Session) -> None:
    first, second = create_demo(client), create_demo(client)
    assert first != second
    assert len(session.exec(select(Student)).all()) == 2


def test_student_validation_rejects(client: TestClient) -> None:
    too_few = DEMO_STUDENT["courses"][:2]
    too_many = DEMO_STUDENT["courses"] + [
        {"course_id": c, "semester_tag": "past"} for c in ("cs202", "cs303", "cs403")
    ]
    cases = {
        "2 courses": {"courses": too_few},
        "7 courses": {"courses": too_many},
        "1 interest": {"interests": ["Databases"]},
        "1 distinct interest": {"interests": ["Databases", "Databases"]},
        "invalid interest": {"interests": ["Databases", "Underwater Basket Weaving"]},
        "invalid semester_tag": {
            "courses": [{"course_id": "cs201", "semester_tag": "next"}, *DEMO_STUDENT["courses"][1:]]
        },
        "unknown course_id": {
            "courses": [{"course_id": "cs999", "semester_tag": "past"}, *DEMO_STUDENT["courses"][1:]]
        },
        "duplicate course": {
            "courses": [*DEMO_STUDENT["courses"], {"course_id": "cs201", "semester_tag": "current"}]
        },
        "short custom text": {
            "courses": [
                *DEMO_STUDENT["courses"][:3],
                {"custom_name": "HCI", "semester_tag": "current", "curriculum_text": "too short"},
            ]
        },
        "both course_id and custom_name": {
            "courses": [
                *DEMO_STUDENT["courses"][:3],
                {"course_id": "cs403", "custom_name": "HCI", "semester_tag": "current"},
            ]
        },
        "neither course_id nor custom_name": {
            "courses": [*DEMO_STUDENT["courses"][:3], {"semester_tag": "current"}]
        },
        "blank name": {"name": "   "},
        "semester 0": {"semester": 0},
    }
    for label, override in cases.items():
        res = client.post("/api/students", json={**DEMO_STUDENT, **override})
        assert res.status_code == 422, f"{label} was accepted: {res.status_code} {res.text}"


# ---- identity ----


def test_missing_or_unknown_student_id_is_404(client: TestClient) -> None:
    for headers in ({}, {"X-Student-Id": "not-a-real-id"}):
        for call in (
            lambda: client.get("/api/roadmap", headers=headers),
            lambda: client.post("/api/analyze", headers=headers),
            lambda: client.post(
                "/api/progress", json={"skill_id": "x", "checked": True}, headers=headers
            ),
        ):
            res = call()
            assert res.status_code == 404, res.text
            assert res.json()["detail"] == "Unknown student — start over"


# ---- POST /api/analyze ----


def test_analyze_is_409_once_an_analysis_exists(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    res = client.post("/api/analyze", headers={"X-Student-Id": student_id})
    assert res.status_code == 409
    assert res.json()["detail"] == "Analysis already exists"


def test_analyze_is_422_for_a_student_with_no_courses(client: TestClient, session: Session) -> None:
    bare = Student(name="No Courses", semester=1, interests=["Security", "Mobile"])
    session.add(bare)
    session.commit()
    res = client.post("/api/analyze", headers={"X-Student-Id": bare.id})
    assert res.status_code == 422
    assert res.json()["detail"] == "Student has no courses"


# ---- persistence ----


def test_persistence_drops_unknown_codes_and_duplicate_pairs(
    client: TestClient, session: Session
) -> None:
    student_id = create_demo(client)
    parsed = make_analysis()
    analyse(session, student_id)

    assert len(session.exec(select(Skill)).all()) == len(parsed.skills)
    # one entry names CS999 (not the student's), one repeats an existing (skill, course) pair
    assert len(session.exec(select(Coverage)).all()) == len(parsed.coverage) - 2


# ---- GET /api/roadmap ----


def test_roadmap_is_404_before_an_analysis(client: TestClient) -> None:
    student_id = create_demo(client)
    res = client.get("/api/roadmap", headers={"X-Student-Id": student_id})
    assert res.status_code == 404
    assert res.json()["detail"] == "No analysis yet"


def test_roadmap_payload(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    body = client.get("/api/roadmap", headers={"X-Student-Id": student_id}).json()

    assert set(body) == {"student", "skills", "roles", "courses"}
    assert body["student"] == {
        "name": "Ayesha",
        "semester": 4,
        "interests": ["Artificial Intelligence", "Databases", "UI/UX Design"],
    }
    assert len(body["skills"]) == 40
    assert len(body["roles"]) == 8
    assert len(body["courses"]) == 4
    assert sum(r["proximity"] == "core" for r in body["roles"]) == 6
    assert all(r["bridge"] == "" for r in body["roles"] if r["proximity"] == "core")
    assert all(r["bridge"] for r in body["roles"] if r["proximity"] == "adjacent")
    assert all(s["checked"] is False for s in body["skills"])
    # v4: nothing is verified and no project exists until Prove It runs
    assert all(s["verified"] is False for s in body["skills"])
    assert all(r["project"] is None and r["latest_review"] is None for r in body["roles"])
    # roles and courses reference the flat skill table by DB id, never by slug
    skill_ids = {s["id"] for s in body["skills"]}
    assert all(rs["skill_id"] in skill_ids for r in body["roles"] for rs in r["skills"])
    assert all(sid in skill_ids for c in body["courses"] for sid in c["skill_ids"])


def test_roadmap_collapses_coverage_to_the_best_depth(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    body = client.get("/api/roadmap", headers={"X-Student-Id": student_id}).json()
    by_slug = {s["slug"]: s for s in body["skills"]}

    # skill-30 is covered partial-then-full, skill-31 full-then-partial: both are "full"
    assert by_slug["skill-30"]["coverage_depth"] == "full"
    assert by_slug["skill-31"]["coverage_depth"] == "full"
    assert by_slug["skill-30"]["covered_by"] == ["CS201", "CS301"]
    # skill-05's only other entry named an unknown course, so CS999 never appears
    assert "CS999" not in by_slug["skill-05"]["covered_by"]
    # an uncovered skill is null, not absent, and carries an empty list
    assert by_slug["skill-39"]["coverage_depth"] is None
    assert by_slug["skill-39"]["covered_by"] == []


def test_roadmap_is_ordered_deterministically(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    headers = {"X-Student-Id": student_id}
    body = client.get("/api/roadmap", headers=headers).json()

    assert body["roles"] == sorted(body["roles"], key=lambda r: (-r["fit_percent"], r["rank"]))
    assert [s["name"] for s in body["skills"]] == sorted(s["name"] for s in body["skills"])
    assert [c["code"] for c in body["courses"]] == ["CS201", "CS301", "CS401", "CS402"]
    assert [c["semester_tag"] for c in body["courses"]] == ["past", "past", "current", "current"]
    weights = {"core": 0, "supporting": 1}
    for role in body["roles"]:
        order = [weights[s["weight"]] for s in role["skills"]]
        assert order == sorted(order), f"{role['slug']} does not list core skills first"
    # same request, same bytes
    assert client.get("/api/roadmap", headers=headers).json() == body


def test_roadmap_fit_matches_the_scoring_module(client: TestClient, session: Session) -> None:
    from app.scoring import ScoredSkill, fit_percent

    student_id = create_demo(client)
    analyse(session, student_id)
    body = client.get("/api/roadmap", headers={"X-Student-Id": student_id}).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    checked = {s["id"] for s in body["skills"] if s["checked"]}
    verified = {s["id"] for s in body["skills"] if s["verified"]}
    for role in body["roles"]:
        expected = fit_percent(
            [
                ScoredSkill(
                    rs["skill_id"],
                    rs["weight"],
                    depth[rs["skill_id"]],
                    rs["skill_id"] in checked,
                    rs["skill_id"] in verified,
                )
                for rs in role["skills"]
            ]
        )
        assert role["fit_percent"] == expected


# ---- POST /api/progress ----


def test_progress_is_idempotent_both_ways(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    headers = {"X-Student-Id": student_id}
    skill_id = client.get("/api/roadmap", headers=headers).json()["skills"][0]["id"]

    for _ in range(2):
        res = client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)
        assert res.status_code == 200
        assert res.json() == {"ok": True}
    assert len(session.exec(select(Progress)).all()) == 1

    for _ in range(2):
        res = client.post("/api/progress", json={"skill_id": skill_id, "checked": False}, headers=headers)
        assert res.status_code == 200
        assert res.json() == {"ok": True}
    assert session.exec(select(Progress)).all() == []


def test_progress_rejects_a_skill_from_another_analysis(client: TestClient, session: Session) -> None:
    mine, theirs = create_demo(client), create_demo(client)
    analyse(session, mine)
    analyse(session, theirs)
    their_skill = client.get("/api/roadmap", headers={"X-Student-Id": theirs}).json()["skills"][0]["id"]

    res = client.post(
        "/api/progress", json={"skill_id": their_skill, "checked": True}, headers={"X-Student-Id": mine}
    )
    assert res.status_code == 404
    assert session.exec(select(Progress)).all() == []


def test_ticking_a_skill_raises_fit_and_can_reorder_roles(client: TestClient, session: Session) -> None:
    student_id = create_demo(client)
    analyse(session, student_id)
    headers = {"X-Student-Id": student_id}
    before = client.get("/api/roadmap", headers=headers).json()

    depth = {s["id"]: s["coverage_depth"] for s in before["skills"]}
    target, missing = max(
        (
            (role, [rs["skill_id"] for rs in role["skills"] if not depth[rs["skill_id"]]])
            for role in before["roles"]
        ),
        key=lambda pair: len(pair[1]),
    )
    assert len(missing) >= 3, "fixture should leave a role with missing skills"

    position_before = [r["id"] for r in before["roles"]].index(target["id"])
    for skill_id in missing[:3]:
        client.post("/api/progress", json={"skill_id": skill_id, "checked": True}, headers=headers)

    after = client.get("/api/roadmap", headers=headers).json()
    moved = next(r for r in after["roles"] if r["id"] == target["id"])
    position_after = [r["id"] for r in after["roles"]].index(target["id"])

    assert moved["fit_percent"] > target["fit_percent"]
    assert position_after < position_before, "three ticks should move the role up the ranking"
    assert {s["id"] for s in after["skills"] if s["checked"]} == set(missing[:3])
