"""Test rig: an in-memory SQLite DB and a duck-typed analysis payload.

DATABASE_URL is set before app.* is imported because app/db.py builds its engine at import
time. The app's own engine is then bypassed via dependency_overrides so TestClient's
threadpool and the test body share one connection — a default in-memory SQLite pool would
hand each thread its own empty database.
"""

import json
import os
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

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


def create_student(client: TestClient, **overrides: Any) -> str:
    """POST the demo student, returning their id."""
    res = client.post("/api/students", json={**DEMO_STUDENT, **overrides})
    assert res.status_code == 201, res.text
    return res.json()["student_id"]


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
