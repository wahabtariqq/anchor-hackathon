"""GET /api/roadmap — one payload with everything the Roadmap page and drawer need.

Seven queries, assembled in Python, no lazy loading (docs/TDD.md §4.10). The client fetches
this once and recomputes fit % locally on every tick, so there is no refetch path.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.db import get_session
from app.identity import current_student
from app.models import (
    Analysis,
    Coverage,
    Progress,
    Project,
    Role,
    RoleSkill,
    Skill,
    Student,
    StudentCourse,
    Submission,
)
from app.persistence import verified_skill_ids
from app.schemas import (
    ProjectResponse,
    ReviewResponse,
    RoadmapCourseOut,
    RoadmapResponse,
    RoadmapRoleOut,
    RoadmapRoleSkillOut,
    RoadmapSkillOut,
    RoadmapStudentOut,
)
from app.scoring import ScoredSkill, fit_percent

router = APIRouter()

# DB ids are UUIDs, so anything the payload lists has to be ordered explicitly or the
# response jitters between calls and the frontend fixture stops being comparable.
_TAG_ORDER = {"past": 0, "current": 1}
_WEIGHT_ORDER = {"core": 0, "supporting": 1}


def project_response(row: Project) -> ProjectResponse:
    return ProjectResponse(
        id=row.id,
        role_id=row.role_id,
        title=row.title,
        spec=row.spec,
        criteria=list(row.criteria),
        verifies=list(row.verifies),
    )


def review_response(row: Submission) -> ReviewResponse:
    """The stored ReviewOut plus the three numbers scoring computed at submit time."""
    return ReviewResponse(
        **row.review,
        total=row.total,
        max_total=row.max_total,
        passed=row.passed,
    )


def build_roadmap(session: Session, student: Student) -> RoadmapResponse:
    analysis = session.exec(select(Analysis).where(Analysis.student_id == student.id)).first()
    if not analysis:
        raise HTTPException(404, "No analysis yet")

    skills = session.exec(select(Skill).where(Skill.analysis_id == analysis.id)).all()
    roles = session.exec(select(Role).where(Role.analysis_id == analysis.id)).all()
    courses = session.exec(
        select(StudentCourse).where(StudentCourse.student_id == student.id)
    ).all()
    role_skills = (
        session.exec(
            select(RoleSkill).where(col(RoleSkill.role_id).in_([r.id for r in roles]))
        ).all()
        if roles
        else []
    )
    coverage = (
        session.exec(
            select(Coverage).where(col(Coverage.student_course_id).in_([c.id for c in courses]))
        ).all()
        if courses
        else []
    )
    checked = {
        p.skill_id
        for p in session.exec(select(Progress).where(Progress.student_id == student.id)).all()
    }
    verified = verified_skill_ids(session, student.id)

    project_of = {
        pr.role_id: project_response(pr)
        for pr in session.exec(select(Project).where(Project.student_id == student.id)).all()
    }
    # latest submission per role — ordered ascending so the last write wins, with id breaking
    # a created_at tie so two submissions in the same tick still resolve the same way
    review_of: dict[str, ReviewResponse] = {}
    for sub in session.exec(
        select(Submission)
        .where(Submission.student_id == student.id)
        .order_by(Submission.created_at, Submission.id)
    ).all():
        review_of[sub.role_id] = review_response(sub)

    # Collapse coverage to the best depth per skill — full beats partial — before any
    # scoring. fit_percent never sees more than one depth for a skill (CONTRACT.md §2).
    code_of = {c.id: c.code for c in courses}
    best: dict[str, str] = {}
    covered_by: dict[str, list[str]] = defaultdict(list)
    skills_of_course: dict[str, list[str]] = defaultdict(list)
    for cv in coverage:
        if best.get(cv.skill_id) != "full":
            best[cv.skill_id] = cv.depth
        covered_by[cv.skill_id].append(code_of[cv.student_course_id])
        skills_of_course[cv.student_course_id].append(cv.skill_id)

    skills_sorted = sorted(skills, key=lambda s: (s.name, s.slug))
    skill_rank = {s.id: i for i, s in enumerate(skills_sorted)}
    last = len(skills_sorted)

    by_role: dict[str, list[RoleSkill]] = defaultdict(list)
    for rs in role_skills:
        by_role[rs.role_id].append(rs)

    role_out: list[RoadmapRoleOut] = []
    for r in roles:
        members = sorted(
            by_role[r.id],
            key=lambda rs: (_WEIGHT_ORDER.get(rs.weight, 2), skill_rank.get(rs.skill_id, last)),
        )
        scored = [
            ScoredSkill(
                rs.skill_id,
                rs.weight,
                best.get(rs.skill_id),
                rs.skill_id in checked,
                rs.skill_id in verified,
            )
            for rs in members
        ]
        role_out.append(
            RoadmapRoleOut(
                id=r.id,
                slug=r.slug,
                title=r.title,
                one_liner=r.one_liner,
                proximity=r.proximity,      # type: ignore[arg-type]  # validated on the way in
                bridge=r.bridge,
                rank=r.rank,
                fit_percent=fit_percent(scored),
                skills=[
                    RoadmapRoleSkillOut(skill_id=rs.skill_id, weight=rs.weight)  # type: ignore[arg-type]
                    for rs in members
                ],
                project=project_of.get(r.id),
                latest_review=review_of.get(r.id),
            )
        )
    role_out.sort(key=lambda r: (-r.fit_percent, r.rank))

    return RoadmapResponse(
        student=RoadmapStudentOut(
            name=student.name,
            semester=student.semester,
            interests=list(student.interests or []),
        ),
        skills=[
            RoadmapSkillOut(
                id=s.id,
                slug=s.slug,
                name=s.name,
                real_world=s.real_world,
                coverage_depth=best.get(s.id),       # type: ignore[arg-type]
                covered_by=sorted(set(covered_by[s.id])),
                checked=s.id in checked,
                verified=s.id in verified,
            )
            for s in skills_sorted
        ],
        roles=role_out,
        courses=[
            RoadmapCourseOut(
                id=c.id,
                code=c.code,
                name=c.name,
                semester_tag=c.semester_tag,          # type: ignore[arg-type]
                skill_ids=sorted(
                    set(skills_of_course[c.id]), key=lambda sid: skill_rank.get(sid, last)
                ),
            )
            for c in sorted(courses, key=lambda c: (_TAG_ORDER.get(c.semester_tag, 2), c.code))
        ],
    )


@router.get("/api/roadmap", response_model=RoadmapResponse)
def get_roadmap(
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> RoadmapResponse:
    return build_roadmap(session, student)
