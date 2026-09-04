"""GET /api/dashboard — "where am I and what's next" in one payload (docs/TDD-V2.md §4.6).

Reuses `build_roadmap` verbatim rather than re-deriving anything: the Dashboard's numbers must
be the same numbers the Roadmap screen shows, and the cheapest way to guarantee that is to ask
the same function. Everything V2-specific on top of it is bookkeeping — event counts, snapshot
rows, and a humanised feed.

No model call. Fit % here is `scoring.fit_percent`, exactly as everywhere else.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, desc, select

from app.auth import current_student, current_user
from app.db import get_session
from app.models import Event, FitSnapshot, Progress, Role, Skill, Student, User
from app.persistence import verified_skill_ids
from app.routers.roadmap import build_roadmap
from app.schemas import (
    ActivityEvent,
    DashboardResponse,
    DashboardTopRole,
    NextAction,
    RoadmapResponse,
    RoadmapRoleOut,
    SnapshotPoint,
)

router = APIRouter()

RECENT_EVENT_LIMIT = 10
TOP_ROLES = 3


def next_action_for(role: RoadmapRoleOut, roadmap: RoadmapResponse) -> NextAction:
    """The one thing worth doing next for this role.

    A generated project with no passing submission wins: it verifies several skills at once and
    is the only thing that can raise fit past a self-report. Otherwise it's the highest-weight
    unresolved skill — `role.skills` is already sorted core-then-declared-order by
    `build_roadmap`, so "first unresolved" *is* "highest weight".
    """
    if role.project and not (role.latest_review and role.latest_review.passed):
        n = len(role.project.verifies)
        return NextAction(
            role_id=role.id,
            label=f"Finish {role.project.title} — verifies {n} skill{'s' if n != 1 else ''}",
            kind="project",
        )

    by_id = {s.id: s for s in roadmap.skills}
    for member in role.skills:
        skill = by_id.get(member.skill_id)
        if skill and not (skill.checked or skill.verified or skill.coverage_depth):
            return NextAction(role_id=role.id, label=f"Learn {skill.name}", kind="tick")

    # nothing unresolved and nothing to prove — the role is as done as ticking can make it
    return NextAction(role_id=role.id, label=f"Review {role.title}", kind="tick")


def humanize(session: Session, event: Event) -> str:
    """An Event row as one feed sentence.

    Names are joined at read time, never stored on the event: a skill renamed by a later
    re-analysis must not leave a stale sentence in the feed.
    """
    skill = session.get(Skill, event.skill_id) if event.skill_id else None
    role = session.get(Role, event.role_id) if event.role_id else None
    skill_name = skill.name if skill else "a skill"
    role_title = role.title if role else "a role"

    if event.type == "tick":
        return f"Marked {skill_name} as learned"
    if event.type == "untick":
        return f"Unmarked {skill_name}"
    if event.type == "submission":
        return f"Submitted a repo for {role_title}"
    if event.type == "pass":
        return f"Verified skills for {role_title} via repo review"
    return f"{event.type} event"


@router.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard(
    user: User = Depends(current_user),
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    roadmap = build_roadmap(session, student)
    # core roles only, already sorted by (-fit_percent, rank) — adjacent roles are a stretch
    # goal, not a progress line, and mixing them in would make the chart's top-3 jump around
    top = [r for r in roadmap.roles if r.proximity == "core"][:TOP_ROLES]

    # Deltas are measured from last_seen_at, which only a login moves (TDD-V2 §4.4). "Since
    # your last visit" has to mean the visit, not the last request of this one.
    since = user.last_seen_at
    fresh = session.exec(
        select(Event).where(Event.user_id == user.id, Event.created_at >= since)
    ).all()
    verified_delta = sum(1 for e in fresh if e.type == "pass")
    checked_delta = sum(1 for e in fresh if e.type == "tick") - sum(
        1 for e in fresh if e.type == "untick"
    )

    snapshots: dict[str, list[SnapshotPoint]] = {}
    if top:
        rows = session.exec(
            select(FitSnapshot)
            .where(
                FitSnapshot.user_id == user.id,
                col(FitSnapshot.role_id).in_([r.id for r in top]),
            )
            .order_by(col(FitSnapshot.created_at), col(FitSnapshot.id))
        ).all()
        snapshots = {r.id: [] for r in top}
        for row in rows:
            snapshots[row.role_id].append(SnapshotPoint(fit=row.fit_percent, at=row.created_at))

    recent = session.exec(
        select(Event)
        .where(Event.user_id == user.id)
        .order_by(desc(col(Event.created_at)), desc(col(Event.id)))
        .limit(RECENT_EVENT_LIMIT)
    ).all()

    checked = session.exec(select(Progress).where(Progress.student_id == student.id)).all()

    return DashboardResponse(
        top_role=(
            DashboardTopRole(id=top[0].id, title=top[0].title, fit_percent=top[0].fit_percent)
            if top
            else None
        ),
        skills_verified=len(verified_skill_ids(session, student.id)),
        skills_checked=len(checked),
        verified_delta=verified_delta,
        checked_delta=checked_delta,
        snapshots=snapshots,
        next_actions=[next_action_for(r, roadmap) for r in top],
        recent_events=[
            ActivityEvent(text=humanize(session, e), at=e.created_at) for e in recent
        ],
    )
