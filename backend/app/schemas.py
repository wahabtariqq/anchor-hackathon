"""API request/response models — the Python mirror of docs/CONTRACT.md §3 and §5.

Shared file. Its siblings are frontend/src/lib/types.ts and app/analysis/schema.py; a change
to any shape here is a `contract:` PR that updates all of them at once.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ---- enumerations (CONTRACT.md §5) ----

Depth = Literal["full", "partial"]
Weight = Literal["core", "supporting"]
Proximity = Literal["core", "adjacent"]
SemesterTag = Literal["past", "current"]
Interest = Literal[
    "Artificial Intelligence",
    "Databases",
    "UI/UX Design",
    "Web Development",
    "Systems & Infrastructure",
    "Data Analysis",
    "Security",
    "Mobile",
]

MIN_CUSTOM_CURRICULUM_CHARS = 50

# ---- GET /api/courses ----


class CatalogCourseOut(BaseModel):
    id: str
    code: str
    name: str
    curriculum_text: str


class CoursesResponse(BaseModel):
    courses: list[CatalogCourseOut]


# ---- POST /api/students ----


class StudentCourseIn(BaseModel):
    """One selected course: either a catalog pick (optionally with a pasted override) or a
    custom course the student typed in. Mirrors the StudentCourseInput union in types.ts.
    """

    semester_tag: SemesterTag
    course_id: str | None = None
    curriculum_override: str | None = None
    custom_name: str | None = None
    curriculum_text: str | None = None

    @model_validator(mode="after")
    def one_source_only(self) -> "StudentCourseIn":
        if bool(self.course_id) == bool(self.custom_name):
            raise ValueError("each course needs exactly one of course_id or custom_name")
        if self.custom_name:
            if self.curriculum_override:
                raise ValueError("curriculum_override applies to catalog courses only")
            if len((self.curriculum_text or "").strip()) < MIN_CUSTOM_CURRICULUM_CHARS:
                raise ValueError(
                    f"custom course '{self.custom_name}' needs curriculum_text of at least "
                    f"{MIN_CUSTOM_CURRICULUM_CHARS} characters"
                )
        elif self.curriculum_text:
            raise ValueError("catalog courses carry their own text; use curriculum_override")
        return self


class StudentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    semester: int = Field(ge=1, le=12)
    interests: list[Interest] = Field(min_length=2)
    courses: list[StudentCourseIn] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def no_duplicates(self) -> "StudentCreateRequest":
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name is required")

        unique_interests = list(dict.fromkeys(self.interests))
        if len(unique_interests) < 2:
            raise ValueError("pick at least 2 different interests")
        self.interests = unique_interests

        picked = [c.course_id for c in self.courses if c.course_id]
        if len(picked) != len(set(picked)):
            raise ValueError("the same catalog course was selected twice")
        return self


class StudentCreateResponse(BaseModel):
    student_id: str


# ---- POST /api/analyze · POST /api/progress ----


class OkResponse(BaseModel):
    ok: Literal[True] = True


class ProgressRequest(BaseModel):
    skill_id: str
    checked: bool


# ---- GET /api/project?role_id=… · POST /api/submit (CONTRACT.md §3) ----

Score = Literal[0, 1, 2]


class ProjectResponse(BaseModel):
    id: str
    role_id: str
    title: str
    spec: str
    criteria: list[str]
    verifies: list[str]                # skill DB ids, not the model's slugs


class SubmitRequest(BaseModel):
    role_id: str
    repo_url: str


class CriterionScore(BaseModel):
    criterion: str
    score: Score
    note: str


class ReviewResponse(BaseModel):
    criteria_scores: list[CriterionScore]
    feedback: str
    total: int                         # Σ score — computed in code, never by the model
    max_total: int                     # 2 × len(criteria)
    passed: bool                       # total ≥ ceil(REVIEW_PASS_RATIO × max_total)


class SubmitResponse(BaseModel):
    review: ReviewResponse
    # the FULL verified set for the student across every passing submission — the client
    # replaces its verifiedIds with this, never merges
    verified_skill_ids: list[str]


# ---- GET /api/roadmap ----


class RoadmapStudentOut(BaseModel):
    name: str
    semester: int
    interests: list[str]


class RoadmapSkillOut(BaseModel):
    id: str
    slug: str
    name: str
    real_world: str
    coverage_depth: Depth | None       # already collapsed to the best depth
    covered_by: list[str]              # course codes, may be empty
    checked: bool
    verified: bool                     # in the union of passing submissions' verified_skill_ids


class RoadmapRoleSkillOut(BaseModel):
    skill_id: str
    weight: Weight


class RoadmapRoleOut(BaseModel):
    id: str
    slug: str
    title: str
    one_liner: str
    proximity: Proximity
    bridge: str                        # "" for core roles
    rank: int
    fit_percent: int
    skills: list[RoadmapRoleSkillOut]
    project: ProjectResponse | None            # null until GET /api/project generates one
    latest_review: ReviewResponse | None       # the most recent submission for this role


class RoadmapCourseOut(BaseModel):
    id: str
    code: str
    name: str
    semester_tag: SemesterTag
    skill_ids: list[str]


class RoadmapResponse(BaseModel):
    student: RoadmapStudentOut
    skills: list[RoadmapSkillOut]
    roles: list[RoadmapRoleOut]
    courses: list[RoadmapCourseOut]
