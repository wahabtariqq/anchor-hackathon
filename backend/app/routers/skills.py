"""GET /api/skills — the whole skill inventory, one row per skill (docs/TDD-V2.md §4.7).

This is invariant #1 made visible: one skill row, many roles. The payload is `build_roadmap`'s
own `skills[]` plus the inverted role→skill map, so this screen physically cannot disagree with
the drawer about whether something is covered.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import current_student
from app.db import get_session
from app.models import Student
from app.routers.roadmap import build_roadmap
from app.schemas import SkillInventoryRow, SkillRoleRef, SkillsResponse

router = APIRouter()


@router.get("/api/skills", response_model=SkillsResponse)
def list_skills(
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> SkillsResponse:
    roadmap = build_roadmap(session, student)

    roles_by_skill: dict[str, list[SkillRoleRef]] = defaultdict(list)
    # roadmap.roles is sorted by (-fit_percent, rank), so each skill's role chips come out
    # best-fit first for free — the order the Skills screen wants to show them in
    for role in roadmap.roles:
        for member in role.skills:
            roles_by_skill[member.skill_id].append(SkillRoleRef(id=role.id, title=role.title))

    return SkillsResponse(
        skills=[
            SkillInventoryRow(
                id=s.id,
                slug=s.slug,
                name=s.name,
                real_world=s.real_world,
                coverage_depth=s.coverage_depth,
                checked=s.checked,
                verified=s.verified,
                roles=roles_by_skill.get(s.id, []),
            )
            # already sorted by (name, slug) upstream; keeping that order means the screen's
            # A-Z list needs no client-side sort
            for s in roadmap.skills
        ]
    )
