"""AnalysisOut -> rows, in one transaction (docs/TDD.md §4.9).

Every id comes from default_factory in Python, so the whole object graph is built in memory
and committed once. v2's per-row flush() was 60+ round trips to a remote pooler for nothing
(DECISIONS #6).

`parsed` is annotated but never imported at runtime: app/analysis/ is the AI lane and may not
be written yet. This module only reads the documented AnalysisOut attributes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models import Analysis, Coverage, Role, RoleSkill, Skill, StudentCourse, Submission

if TYPE_CHECKING:                                   # pragma: no cover
    from app.analysis.schema import AnalysisOut

log = logging.getLogger(__name__)


def persist_analysis(
    session: Session,
    student_id: str,
    parsed: AnalysisOut,
    raw: str,
    student_courses: list[StudentCourse],
) -> Analysis:
    analysis = Analysis(student_id=student_id, raw_json=raw)
    session.add(analysis)

    skills = {
        s.id: Skill(analysis_id=analysis.id, slug=s.id, name=s.name, real_world=s.real_world)
        for s in parsed.skills
    }
    session.add_all(skills.values())

    for r in parsed.roles:
        role = Role(
            analysis_id=analysis.id,
            slug=r.id,
            title=r.title,
            one_liner=r.one_liner,
            proximity=r.proximity,
            bridge=r.bridge,
            rank=r.rank,
        )
        session.add(role)
        session.add_all(
            RoleSkill(role_id=role.id, skill_id=skills[rs.skill_id].id, weight=rs.weight)
            for rs in r.skills
        )

    code_to_sc = {sc.code: sc.id for sc in student_courses}
    seen: set[tuple[str, str]] = set()
    for c in parsed.coverage:
        if c.course_code not in code_to_sc:
            # Soft data-quality issue; the wrong thing to fail a demo over (CONTRACT.md §1.1).
            log.warning("dropping coverage for unknown code %s", c.course_code)
            continue
        key = (skills[c.skill_id].id, code_to_sc[c.course_code])
        if key in seen:
            continue                                # the model occasionally repeats a pair
        seen.add(key)
        session.add(Coverage(skill_id=key[0], student_course_id=key[1], depth=c.depth))

    session.commit()
    return analysis


def verified_skill_ids(session: Session, student_id: str) -> set[str]:
    """The student's verified skills: the union over **all** their passing submissions.

    Union, not the latest submission — skills are shared across roles, so proving one through
    a Data Engineer project must count everywhere it appears (DECISIONS #21). Derived on every
    read; never stored on Skill.
    """
    rows = session.exec(
        select(Submission.verified_skill_ids).where(
            Submission.student_id == student_id,
            Submission.passed == True,  # noqa: E712 — SQLAlchemy needs ==, not `is`
        )
    ).all()
    return {skill_id for row in rows for skill_id in (row or [])}
