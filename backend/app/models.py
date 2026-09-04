"""SQLModel tables. Mirror of docs/TDD.md §4.4 — shared file, see .claude/skills/anchor-contract.

Nothing here is ever updated or deleted except Progress rows; Project and Submission rows are
append-only. A returning student who re-onboards gets a new Student row, which removes every
cascade-delete case.

A student's **verified** skills are the union of verified_skill_ids over their passing
submissions. That is derived on read (see app/persistence.py), never stored on Skill.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """A real account (V2). V1's anonymous Student rows keep working and get adopted by one
    of these via claim-on-signup (TDD-V2 §5.1)."""

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(unique=True, index=True)     # always stored lowercased
    password_hash: str                              # bcrypt; the password itself is never stored
    name: str
    created_at: datetime = Field(default_factory=now)
    # Bumped only on login, never per-request: it is the dashboard delta's baseline and must
    # stay fixed for the whole session rather than creeping forward (TDD-V2 §4.4).
    last_seen_at: datetime = Field(default_factory=now)


class Session(SQLModel, table=True):
    """An issued bearer token. Only its SHA-256 hash is stored, so a database leak does not
    hand over live sessions."""

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=now)
    expires_at: datetime


class LoginFailure(SQLModel, table=True):
    """One row per failed login, for the naive rate limit (TDD-V2 §4.3). No Redis."""

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True)
    created_at: datetime = Field(default_factory=now, index=True)


class Student(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    # Nullable: POST /api/students still creates the row, and it is adopted either by
    # onboarding under an account or by claim-on-signup. V1 rows keep user_id = None.
    user_id: str | None = Field(default=None, foreign_key="user.id", index=True)
    name: str
    semester: int
    interests: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


class Course(SQLModel, table=True):
    """Pre-seeded catalog. Read-only at runtime."""

    id: str = Field(primary_key=True)          # "cs301"
    code: str                                  # "CS301"
    name: str
    curriculum_text: str


class StudentCourse(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    student_id: str = Field(foreign_key="student.id", index=True)
    course_id: str | None = Field(default=None, foreign_key="course.id")   # None = custom
    code: str                    # ALWAYS populated: "CS301" or "CUSTOM-1"
    name: str
    curriculum_text: str         # resolved: override > custom paste > catalog default
    semester_tag: str            # "past" | "current"


class Analysis(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    student_id: str = Field(foreign_key="student.id", unique=True, index=True)
    raw_json: str
    created_at: datetime = Field(default_factory=now)


class Skill(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("analysis_id", "slug"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    analysis_id: str = Field(foreign_key="analysis.id", index=True)
    slug: str
    name: str
    real_world: str


class Role(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    analysis_id: str = Field(foreign_key="analysis.id", index=True)
    slug: str
    title: str
    one_liner: str
    proximity: str               # "core" | "adjacent"
    bridge: str                  # "" for core
    rank: int


class RoleSkill(SQLModel, table=True):
    role_id: str = Field(foreign_key="role.id", primary_key=True)
    skill_id: str = Field(foreign_key="skill.id", primary_key=True)
    weight: str                  # "core" | "supporting"


class Coverage(SQLModel, table=True):
    skill_id: str = Field(foreign_key="skill.id", primary_key=True)
    student_course_id: str = Field(foreign_key="studentcourse.id", primary_key=True)
    depth: str                   # "full" | "partial"


class Progress(SQLModel, table=True):
    student_id: str = Field(foreign_key="student.id", primary_key=True)
    skill_id: str = Field(foreign_key="skill.id", primary_key=True)
    checked_at: datetime = Field(default_factory=now)


class Project(SQLModel, table=True):
    """One per (student, role). Written once on first GET /api/project, never regenerated."""

    __table_args__ = (UniqueConstraint("student_id", "role_id"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    student_id: str = Field(foreign_key="student.id", index=True)
    role_id: str = Field(foreign_key="role.id")
    title: str
    spec: str
    criteria: list[str] = Field(sa_column=Column(JSON))
    # skill.id values — the model returns slugs, routers/project.py resolves them before writing
    verifies: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


class Submission(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    student_id: str = Field(foreign_key="student.id", index=True)
    role_id: str = Field(foreign_key="role.id")
    project_id: str = Field(foreign_key="project.id")
    repo_url: str
    review: dict = Field(sa_column=Column(JSON))                    # ReviewOut as stored
    total: int
    max_total: int
    passed: bool
    # a copy of project.verifies when passed, else [] — frozen at submission time
    verified_skill_ids: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
