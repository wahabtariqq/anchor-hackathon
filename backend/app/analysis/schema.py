"""`AnalysisOut` and the V1-V6 semantic validators (docs/CONTRACT.md §1.1, docs/TDD.md §4.5).

Structured outputs constrain decoding to the schema, so the shape is guaranteed: every field is
present, with the right type. What the grammar *cannot* express is meaning — that a role must
not reference a skill nobody minted, that eight roles must include five or six core ones, that
an adjacent role without a bridge line has nothing to say to the student. Those are V1-V6, and
each one corresponds to a way the roadmap breaks silently rather than loudly.

This module imports nothing from the provider. It is pure Pydantic and is unaffected by
DECISIONS #39 (Gemini instead of Anthropic) — the validators are the reason a vendor swap is
survivable at all.

Length bounds live here rather than in `Field(min_length=...)` because the provider strips
those constraints from the sent schema (verified: Gemini's `response_schema` does not support
`pattern`, `minLength`, or `maxLength`). Keeping them in one place avoids two sources of truth
that silently disagree.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Kept on the field for documentation and post-hoc enforcement. The provider strips it from the
# schema it is sent, so this regex only ever runs here, on the way back in.
SKILL_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

MIN_SKILLS, MAX_SKILLS = 35, 70
MIN_ROLE_SKILLS, MAX_ROLE_SKILLS = 8, 16
MIN_CORE_ROLES, MAX_CORE_ROLES = 5, 6
N_ROLES = 8


class SkillOut(BaseModel):
    """One atomic capability. `id` is the vocabulary the whole product is keyed to."""

    id: str = Field(pattern=SKILL_ID_PATTERN)
    name: str
    real_world: str


class CoverageOut(BaseModel):
    """One (skill, course) pair the student's coursework covers.

    `course_code` is deliberately *not* validated against the student's codes here — this model
    does not know them. `persistence.py` drops unknown codes with a warning (TDD §4.9), because
    a soft data-quality issue is the wrong thing to fail a live analysis over.
    """

    skill_id: str
    course_code: str
    depth: Literal["full", "partial"]


class RoleSkillOut(BaseModel):
    skill_id: str
    weight: Literal["core", "supporting"]


class RoleOut(BaseModel):
    """One career role: a weighted subset of the skill vocabulary.

    `bridge` is a plain `str`, `""` for core roles, never `None` — union types are the most
    expensive thing in the output grammar (DECISIONS #5).
    """

    id: str
    title: str
    one_liner: str
    proximity: Literal["core", "adjacent"]
    bridge: str
    rank: int
    skills: list[RoleSkillOut]

    @model_validator(mode="after")
    def checks(self) -> "RoleOut":
        # V6 — an adjacent role is only interesting because of its bridge line. Without one the
        # student sees an unexplained job title and the "the system found this for you" beat
        # in the demo has nothing behind it. Whitespace is not a bridge.
        if self.proximity == "adjacent" and not self.bridge.strip():
            raise ValueError(f"adjacent role '{self.id}' missing bridge")

        skill_ids = [s.skill_id for s in self.skills]

        # V5 — a repeat would violate the RoleSkill primary key on insert, so this fails here
        # with a readable message instead of as an IntegrityError inside persistence.
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError(f"role '{self.id}' repeats a skill")

        if not MIN_ROLE_SKILLS <= len(skill_ids) <= MAX_ROLE_SKILLS:
            raise ValueError(
                f"role '{self.id}' has {len(skill_ids)} skills, "
                f"want {MIN_ROLE_SKILLS}-{MAX_ROLE_SKILLS}"
            )
        return self


class AnalysisOut(BaseModel):
    """The whole analysis payload. One per student, immutable once persisted."""

    skills: list[SkillOut]
    coverage: list[CoverageOut]
    roles: list[RoleOut]

    @model_validator(mode="after")
    def integrity(self) -> "AnalysisOut":
        # Order matters. Duplicate ids are checked before dangling references, because a
        # duplicate necessarily *creates* a dangling reference — the shadowed id disappears from
        # the vocabulary — and reporting the symptom instead of the cause sends prompt tuning
        # after the wrong problem.

        # V1 — count
        if not MIN_SKILLS <= len(self.skills) <= MAX_SKILLS:
            raise ValueError(
                f"{len(self.skills)} skills, want {MIN_SKILLS}-{MAX_SKILLS}"
            )

        # V2 — role count
        if len(self.roles) != N_ROLES:
            raise ValueError(f"{len(self.roles)} roles, want {N_ROLES}")

        # V1 — uniqueness
        skill_ids = [s.id for s in self.skills]
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError("duplicate skill ids")

        known = set(skill_ids)

        # V3 — every role skill exists. A dangling reference means a card whose fit % is
        # computed from a skill the student can never tick, so the number can never move.
        for role in self.roles:
            for role_skill in role.skills:
                if role_skill.skill_id not in known:
                    raise ValueError(
                        f"role '{role.id}' references unknown skill '{role_skill.skill_id}'"
                    )

        # V4 — every coverage row points at a real skill. A dangling one would credit the
        # student for coursework that maps to nothing.
        for cov in self.coverage:
            if cov.skill_id not in known:
                raise ValueError(f"coverage references unknown skill '{cov.skill_id}'")

        # V2 — the core/adjacent split. Too few core roles and the ranking looks arbitrary; too
        # few adjacent and the product loses the roles the student never thought to ask for.
        n_core = sum(r.proximity == "core" for r in self.roles)
        if not MIN_CORE_ROLES <= n_core <= MAX_CORE_ROLES:
            raise ValueError(
                f"expected {MIN_CORE_ROLES}-{MAX_CORE_ROLES} core roles, got {n_core}"
            )
        return self
