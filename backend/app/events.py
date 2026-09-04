"""Event log and fit-history writes (docs/TDD-V2.md §4.5).

Bookkeeping only — no model calls, no new skill semantics. Everything here is called from
*inside* an existing router transaction and committed by that router's own `session.commit()`,
so an event or a snapshot can never describe a write that rolled back.

`fit_by_role` is deliberately narrow: it scores only the roles that contain the skills which
just changed, not the whole roadmap. A tick is on the demo's hot path, and two full
`build_roadmap()` calls per tick would be ~14 queries to learn something about 1-8 roles.
`test_events.py` pins it against `build_roadmap`'s own numbers so the shortcut can't drift.
"""

from collections import defaultdict
from collections.abc import Iterable

from sqlmodel import Session, col, select

from app.models import (
    Analysis,
    Coverage,
    Event,
    FitSnapshot,
    Progress,
    Role,
    RoleSkill,
    Student,
    StudentCourse,
)
from app.persistence import verified_skill_ids
from app.scoring import ScoredSkill, fit_percent


def record_tick(session: Session, user_id: str, skill_id: str, checked: bool) -> None:
    session.add(Event(user_id=user_id, type="tick" if checked else "untick", skill_id=skill_id))


def record_submission(
    session: Session, user_id: str, role_id: str, submission_id: str, passed: bool
) -> None:
    """Two rows for a pass, one for a miss. The feed wants to say "submitted" and "verified"
    as separate sentences, and the Dashboard's verified-delta counts `pass` rows alone."""
    session.add(
        Event(
            user_id=user_id,
            type="submission",
            role_id=role_id,
            submission_id=submission_id,
        )
    )
    if passed:
        session.add(
            Event(user_id=user_id, type="pass", role_id=role_id, submission_id=submission_id)
        )


def snapshot_changed_roles(
    session: Session, user_id: str, before: dict[str, int], after: dict[str, int]
) -> None:
    """One row per role whose fit actually moved.

    The `!=` is the whole point: ticking a skill a course already covers in full changes
    nothing (`fit_percent` takes a `max`, DECISIONS #3), and writing a flat point for it would
    put a visible kink in a chart that should stay straight.
    """
    for role_id, new_fit in after.items():
        if before.get(role_id) != new_fit:
            session.add(FitSnapshot(user_id=user_id, role_id=role_id, fit_percent=new_fit))


def fit_by_role(session: Session, student: Student, skill_ids: Iterable[str]) -> dict[str, int]:
    """Fit % for exactly the roles containing any of `skill_ids`, keyed by role id.

    Four queries regardless of how many roles come back. Returns `{}` when the student has no
    analysis yet or none of their roles want these skills — `snapshot_changed_roles` then
    writes nothing, which is correct.
    """
    wanted = list(skill_ids)
    if not wanted:
        return {}

    analysis = session.exec(select(Analysis).where(Analysis.student_id == student.id)).first()
    if not analysis:
        return {}

    affected_role_ids = set(
        session.exec(
            select(RoleSkill.role_id)
            .join(Role, col(Role.id) == col(RoleSkill.role_id))
            .where(Role.analysis_id == analysis.id, col(RoleSkill.skill_id).in_(wanted))
        ).all()
    )
    if not affected_role_ids:
        return {}

    # every member skill of those roles, not just the changed ones — fit is a ratio over the
    # whole role, so scoring one skill in isolation would be meaningless
    members = session.exec(
        select(RoleSkill).where(col(RoleSkill.role_id).in_(affected_role_ids))
    ).all()

    checked = {
        p.skill_id
        for p in session.exec(select(Progress).where(Progress.student_id == student.id)).all()
    }
    verified = verified_skill_ids(session, student.id)

    # same collapse GET /api/roadmap does before scoring: best depth per skill, full beats
    # partial, so fit_percent never sees a skill twice (docs/CONTRACT.md §2)
    course_ids = session.exec(
        select(StudentCourse.id).where(StudentCourse.student_id == student.id)
    ).all()
    best: dict[str, str] = {}
    if course_ids:
        for cv in session.exec(
            select(Coverage).where(col(Coverage.student_course_id).in_(list(course_ids)))
        ).all():
            if best.get(cv.skill_id) != "full":
                best[cv.skill_id] = cv.depth

    by_role: dict[str, list[RoleSkill]] = defaultdict(list)
    for rs in members:
        by_role[rs.role_id].append(rs)

    return {
        role_id: fit_percent(
            [
                ScoredSkill(
                    rs.skill_id,
                    rs.weight,
                    best.get(rs.skill_id),
                    rs.skill_id in checked,
                    rs.skill_id in verified,
                )
                for rs in role_members
            ]
        )
        for role_id, role_members in by_role.items()
    }
