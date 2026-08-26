"""GET /api/project — the role's project, generated on first ask and cached forever.

Lazy per (student, role): the spec targets the gaps the student has *now*, so generating
every role up front would be both wasteful and stale (DECISIONS #19). Written once; a
second call returns the same row.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.db import get_session
from app.identity import current_student
from app.models import Analysis, Coverage, Progress, Project, Role, RoleSkill, Skill, Student, StudentCourse
from app.persistence import verified_skill_ids
from app.routers.roadmap import project_response
from app.schemas import ProjectResponse

router = APIRouter()
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillState:
    """Mirrors app.analysis.project.SkillState — matched by attribute name, not by import,
    because app/analysis/ is Umer's lane and may not be written yet."""

    slug: str
    name: str
    weight: str
    state: str      # "verified" | "ticked" | "covered:full" | "covered:partial" | "missing"


def _resolve(name: str) -> Callable[..., Any]:
    """Look up an app.analysis entry point at call time (see routers/analyze.py, DECISIONS #11)."""
    try:
        import app.analysis as analysis
    except ImportError as e:
        log.warning("app.analysis is not importable: %s", e)
        raise HTTPException(503, "Project generation not available yet") from e
    entry = getattr(analysis, name, None)
    if not callable(entry):
        log.warning("app.analysis does not export %s yet", name)
        raise HTTPException(503, "Project generation not available yet")
    return entry


def _optional(name: str) -> Callable[..., Any] | None:
    try:
        import app.analysis as analysis
    except ImportError:
        return None
    entry = getattr(analysis, name, None)
    return entry if callable(entry) else None


def role_for_student(session: Session, student: Student, role_id: str) -> Role:
    """A role the student's own analysis produced. Anything else is a 404, not someone
    else's role rendered under their name."""
    role = session.get(Role, role_id)
    if role:
        analysis = session.get(Analysis, role.analysis_id)
        if analysis and analysis.student_id == student.id:
            return role
    raise HTTPException(404, "Unknown role")


def skill_states_for_role(session: Session, student: Student, role: Role) -> list[SkillState]:
    """One label per role skill, for the prompt to aim `verifies` at real gaps."""
    members = session.exec(select(RoleSkill).where(RoleSkill.role_id == role.id)).all()
    skills = {
        s.id: s
        for s in session.exec(
            select(Skill).where(col(Skill.id).in_([m.skill_id for m in members]))
        ).all()
    } if members else {}

    checked = {
        p.skill_id
        for p in session.exec(select(Progress).where(Progress.student_id == student.id)).all()
    }
    verified = verified_skill_ids(session, student.id)

    course_ids = [
        c.id
        for c in session.exec(
            select(StudentCourse).where(StudentCourse.student_id == student.id)
        ).all()
    ]
    best: dict[str, str] = {}
    if course_ids:
        for cv in session.exec(
            select(Coverage).where(col(Coverage.student_course_id).in_(course_ids))
        ).all():
            if best.get(cv.skill_id) != "full":
                best[cv.skill_id] = cv.depth

    states: list[SkillState] = []
    for member in members:
        skill = skills.get(member.skill_id)
        if not skill:
            continue
        # Ordered by how much the student already has. `ticked` outranks `covered:partial`
        # so a self-claim reads as a claim worth proving, which is what the prompt aims at.
        if member.skill_id in verified:
            state = "verified"
        elif best.get(member.skill_id) == "full":
            state = "covered:full"
        elif member.skill_id in checked:
            state = "ticked"
        elif best.get(member.skill_id) == "partial":
            state = "covered:partial"
        else:
            state = "missing"
        states.append(SkillState(slug=skill.slug, name=skill.name, weight=member.weight, state=state))
    return states


def _demo_applies(student: Student, session: Session, role: Role) -> bool:
    """DEMO_MODE, the demo student, and their top-ranked role (PRD §12.1)."""
    from app.config import settings

    if not settings.DEMO_MODE or student.name.strip().lower() != settings.DEMO_STUDENT_NAME.strip().lower():
        return False
    top = session.exec(
        select(Role).where(Role.analysis_id == role.analysis_id).order_by(Role.rank)
    ).first()
    return bool(top and top.id == role.id)


@router.get("/api/project", response_model=ProjectResponse)
def get_project(
    role_id: str,
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> ProjectResponse:
    role = role_for_student(session, student, role_id)

    existing = session.exec(
        select(Project).where(Project.student_id == student.id, Project.role_id == role.id)
    ).first()
    if existing:
        return project_response(existing)

    load_demo = _optional("load_demo_project") if _demo_applies(student, session, role) else None
    states = skill_states_for_role(session, student, role)
    try:
        if load_demo:
            out = load_demo()
        else:
            out, _raw = _resolve("generate_project")(role.title, role.one_liner, states)
    except HTTPException:
        raise
    except Exception as e:
        log.warning("project generation failed for role %s: %s", role.id, e)
        raise HTTPException(502, str(e) or "Project generation failed") from e

    slug_to_id = {s.slug: s.id for s in _role_skills(session, role)}
    unknown = [slug for slug in out.verifies if slug not in slug_to_id]
    if unknown:
        # the AI lane cross-checks this too; a 502 beats writing a row that references nothing
        log.warning("project verifies unknown slugs %s for role %s", unknown, role.id)
        raise HTTPException(502, f"Project referenced skills outside the role: {', '.join(unknown)}")

    row = Project(
        student_id=student.id,
        role_id=role.id,
        title=out.title,
        spec=out.spec,
        criteria=list(out.criteria),
        verifies=[slug_to_id[slug] for slug in out.verifies],
    )
    session.add(row)
    session.commit()
    return project_response(row)


def _role_skills(session: Session, role: Role) -> list[Skill]:
    members = session.exec(select(RoleSkill).where(RoleSkill.role_id == role.id)).all()
    if not members:
        return []
    return list(
        session.exec(select(Skill).where(col(Skill.id).in_([m.skill_id for m in members]))).all()
    )
