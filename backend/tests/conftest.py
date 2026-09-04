"""Test rig: an in-memory SQLite DB and a duck-typed analysis payload.

DATABASE_URL is set before app.* is imported because app/db.py builds its engine at import
time. The app's own engine is then bypassed via dependency_overrides so TestClient's
threadpool and the test body share one connection — a default in-memory SQLite pool would
hand each thread its own empty database.
"""

import json
import os
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
# bcrypt at 12 rounds is ~300ms a hash by design; the suite creates dozens of accounts.
os.environ.setdefault("BCRYPT_ROUNDS", "4")

import pytest                                                     # noqa: E402
from fastapi.testclient import TestClient                         # noqa: E402
from sqlalchemy.pool import StaticPool                            # noqa: E402
from sqlmodel import Session, SQLModel, create_engine             # noqa: E402

from app.db import get_session                                    # noqa: E402
from app.main import app                                          # noqa: E402
from app.models import Course                                     # noqa: E402
from seed.courses import CATALOG                                  # noqa: E402

DEMO_STUDENT: dict[str, Any] = {
    "name": "Ayesha",
    "semester": 4,
    "interests": ["Artificial Intelligence", "Databases", "UI/UX Design"],
    "courses": [
        {"course_id": "cs201", "semester_tag": "past"},
        {"course_id": "cs301", "semester_tag": "past"},
        {"course_id": "cs401", "semester_tag": "current"},
        {"course_id": "cs402", "semester_tag": "current"},
    ],
}


# V2: every request carries a bearer token, so a test student needs an account behind it.
# create_student() records the token it used; auth_headers() hands it back, which keeps each
# test reading as "this student's request" rather than plumbing tokens through every call.
_TOKENS: dict[str, str] = {}


def create_account(
    client: TestClient,
    email: str | None = None,
    password: str = "hunter2-strong",
    name: str = "Ayesha",
) -> tuple[str, dict[str, str]]:
    """Signs up and logs in. Returns (token, headers) — signup alone issues no session."""
    email = email or f"user-{uuid.uuid4().hex[:12]}@example.com"
    created = client.post(
        "/api/auth/signup", json={"email": email, "password": password, "name": name}
    )
    assert created.status_code == 200, created.text
    logged_in = client.post("/api/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    token = logged_in.json()["token"]
    return token, {"Authorization": f"Bearer {token}"}


def auth_headers(student_id: str) -> dict[str, str]:
    """The Authorization header for the account that owns this student."""
    return {"Authorization": f"Bearer {_TOKENS[student_id]}"}


def create_student(client: TestClient, **overrides: Any) -> str:
    """Create an account, onboard the demo student under it, return the student id."""
    token, headers = create_account(client)
    res = client.post("/api/students", json={**DEMO_STUDENT, **overrides}, headers=headers)
    assert res.status_code == 201, res.text
    student_id = res.json()["student_id"]
    _TOKENS[student_id] = token
    return student_id


def persist_demo_analysis(session: Session, student_id: str) -> None:
    """Run make_analysis() through the real persist_analysis for this student."""
    from sqlmodel import select

    from app.models import StudentCourse
    from app.persistence import persist_analysis

    courses = session.exec(
        select(StudentCourse).where(StudentCourse.student_id == student_id)
    ).all()
    persist_analysis(session, student_id, make_analysis(), json.dumps({"stub": True}), list(courses))


@pytest.fixture
def engine() -> Iterator[Any]:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all(Course(**row) for row in CATALOG)
        session.commit()
    yield eng
    SQLModel.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine: Any) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine: Any) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_analysis(
    n_skills: int = 40,
    codes: tuple[str, ...] = ("CS201", "CS301", "CS401", "CS402"),
) -> SimpleNamespace:
    """A valid-shaped AnalysisOut: 40 skills, 8 roles (6 core / 2 adjacent), mixed coverage.

    Duck-typed rather than the real app.analysis.schema.AnalysisOut, because that is Dev B's
    lane and contracts/fixtures/demo_analysis.json is still a placeholder. persist_analysis
    reads only the attributes CONTRACT.md §1 documents, so this exercises the real code path.
    """
    skills = [
        SimpleNamespace(id=f"skill-{i:02d}", name=f"Skill {i:02d}", real_world=f"Matters when {i}.")
        for i in range(n_skills)
    ]

    coverage = [
        SimpleNamespace(
            skill_id=f"skill-{i:02d}",
            course_code=codes[i % len(codes)],
            depth="full" if i % 3 else "partial",
        )
        for i in range(24)
    ]
    # Both collapse orders for one skill each: partial-then-full and full-then-partial must
    # both end up "full" (CONTRACT.md §2).
    coverage += [
        SimpleNamespace(skill_id="skill-30", course_code=codes[0], depth="partial"),
        SimpleNamespace(skill_id="skill-30", course_code=codes[1], depth="full"),
        SimpleNamespace(skill_id="skill-31", course_code=codes[0], depth="full"),
        SimpleNamespace(skill_id="skill-31", course_code=codes[1], depth="partial"),
    ]
    # Soft failures persistence must swallow: an unknown code and a repeated pair.
    coverage += [
        SimpleNamespace(skill_id="skill-05", course_code="CS999", depth="full"),
        SimpleNamespace(skill_id="skill-04", course_code=codes[0], depth="partial"),
    ]

    roles = [
        SimpleNamespace(
            id=f"role-{r}",
            title=f"Role {r}",
            one_liner=f"Does the {r} work.",
            proximity="adjacent" if r >= 6 else "core",
            bridge="Your coursework converges here." if r >= 6 else "",
            rank=r + 1,
            skills=[
                SimpleNamespace(
                    skill_id=f"skill-{(r * 5 + k) % n_skills:02d}",
                    weight="core" if k < 5 else "supporting",
                )
                for k in range(11)
            ],
        )
        for r in range(8)
    ]
    return SimpleNamespace(skills=skills, coverage=coverage, roles=roles)
