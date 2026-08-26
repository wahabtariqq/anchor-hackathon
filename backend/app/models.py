"""SQLModel tables. Mirror of docs/TDD.md §4.4 — shared file, see .claude/skills/anchor-contract.

Nothing here is ever updated or deleted except Progress rows. A returning student who
re-onboards gets a new Student row, which removes every cascade-delete case.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Student(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
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
