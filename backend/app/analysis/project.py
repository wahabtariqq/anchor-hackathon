"""`ProjectOut` and the project-generation call (CONTRACT §1b, PRD §8.2, TDD §4.12).

This call fires lazily, the first time a student opens a role's Prove It panel, and Salman
caches the result per (student, role) **forever** — it is never regenerated. So it has to be
good the first time, and it has to target the student's gaps *at that moment*, which is the
whole reason project generation is a separate call rather than part of the analysis.

`verifies` are skill **slugs**, not ids. The DB speaks ids; this package never sees them
(CONTRACT §1b). Salman resolves slug -> id and 502s a project whose slugs do not resolve
(DECISIONS #35). This module cross-checks the same rule first, because the grammar cannot
express set membership and a `Project` row that verifies nothing would do so silently, forever.

`SkillState` is duplicated in `app/routers/project.py` rather than imported, matched by field
name only (DECISIONS #33). `tests/test_project.py` compares the two dataclasses so a rename
fails a test instead of breaking GET /api/project in silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pydantic import BaseModel, model_validator

from app.analysis.client import LLMClient, complete_validated

# CONTRACT §1b. Bounds live here, not in `Field(...)`: the provider strips length keywords from
# the schema it is sent (client.py `_DROP_KEYWORDS`), so one source of truth is the only kind
# that cannot silently disagree with itself.
MIN_CRITERIA, MAX_CRITERIA = 3, 4
MIN_VERIFIES, MAX_VERIFIES = 2, 4

# Small next to the analysis call's 16k: one title, four sentences, four criteria, four slugs.
PROJECT_MAX_TOKENS = 2000
PROJECT_RETRY_MAX_TOKENS = 3000
# Higher than the analysis call's 0.3. This is a design task, not an extraction task -- two
# students on the same role should not get the identical repo idea.
PROJECT_TEMPERATURE = 0.5


# --- mirrored from ai-working/prompts/project.md - edit THERE first, then here --------
# Mirrored rather than read from disk for the same reason as the analysis prompt: the
# deployed backend ships backend/ only, and a runtime dependency on ai-working/ would work
# locally and fail on the host. tests/test_project.py asserts the two never drift.
PROJECT_PROMPT = """\
Design one small project that will let a student prove they have specific skills.

## The role they are working toward

{role_title} — {one_liner}

## Their current standing on this role's skills

Each line is: slug — name — weight — their current state.

{skill_lines}

  verified        already proven with a passing repo. Nothing left to prove here.
  ticked          they say they have it, but have not proven it. PRIME TARGET.
  covered:full    their coursework covers it properly.
  covered:partial their coursework touches it.
  missing         no coverage, no claim. PRIME TARGET.

## What to produce

A project this student could finish over a weekend. One repository. Nothing beyond a laptop —
no cloud accounts, no paid services, no cluster, no GPU, no team.

  title     what the repo is. Concrete and specific.
            Good: "Build a log-ingestion pipeline with replay"
            Bad:  "Data Engineering Project"

  spec      three or four sentences: what to build, and what "done" looks like. Concrete
            enough that two different students would build recognisably the same thing.

  criteria  three or four things the finished repository will be scored on.

            HARD REQUIREMENT: each criterion must be checkable by READING the repository.
            Whoever scores this cannot run the code, cannot install it, cannot run its tests.
            They see the file tree and the contents of a handful of files.

            Good: "Ingestion and storage are separated into distinct modules with a defined
                   interface between them."
            Good: "The README documents the replay procedure, including how duplicates are
                   handled."
            Bad:  "The pipeline works correctly."        ← cannot be seen by reading
            Bad:  "The tests pass."                      ← nothing is executed
            Bad:  "The code is efficient."               ← not observable, not scoreable

            Each criterion is scored 0, 1, or 2, so write each one so that a partial attempt
            can honestly earn a 1.

  verifies  two to four skill slugs from the list above, that completing this project would
            genuinely be evidence for.

            Choose skills marked missing or ticked. Those are what the student needs to prove.
            Do NOT choose skills marked verified — there is nothing left to prove.
            Choosing covered:full skills is close to worthless to them.

            Every slug must appear exactly as written in the list above. Do not invent slugs,
            do not reword them, do not include a slug twice.

            The project must genuinely exercise every skill it claims to verify. If a skill
            would not actually be demonstrated by building this, leave it out and claim fewer."""
# -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillState:
    """One role skill plus what the student already has on it.

    ⚠ Structurally duplicated in `app/routers/project.py:29-37` (DECISIONS #33) — Salman builds
    that copy, this package reads it, and nothing but `tests/test_project.py` connects them.
    Renaming a field here is a lane-boundary change: `contract:` PR, not a local edit.

    `state` is one of: verified · ticked · covered:full · covered:partial · missing.
    """

    slug: str
    name: str
    weight: str
    state: str


class ProjectOut(BaseModel):
    """One project spec. `verifies` are slugs from the role that asked for it."""

    title: str
    spec: str
    criteria: list[str]
    verifies: list[str]

    @model_validator(mode="after")
    def checks(self) -> "ProjectOut":
        if not self.title.strip():
            raise ValueError("title is blank")
        if not self.spec.strip():
            raise ValueError("spec is blank")

        if not MIN_CRITERIA <= len(self.criteria) <= MAX_CRITERIA:
            raise ValueError(
                f"{len(self.criteria)} criteria, want {MIN_CRITERIA}-{MAX_CRITERIA}"
            )
        # A blank criterion still counts toward `max_total`, so it cannot be scored above 0 and
        # silently drags every review down by up to a third.
        if any(not c.strip() for c in self.criteria):
            raise ValueError("a criterion is blank")
        # Case-folded, matching how review.py compares the echo back: a criterion repeated in a
        # different case is still scored twice, quietly doubling its weight in the total.
        folded = [c.strip().lower() for c in self.criteria]
        if len(set(folded)) != len(folded):
            raise ValueError("criteria repeat")

        if not MIN_VERIFIES <= len(self.verifies) <= MAX_VERIFIES:
            raise ValueError(
                f"verifies has {len(self.verifies)} slugs, want {MIN_VERIFIES}-{MAX_VERIFIES}"
            )
        # Two identical slugs resolve to one id, so the project claims to verify more than it
        # does and the badge count on screen disagrees with the roadmap.
        if len(set(self.verifies)) != len(self.verifies):
            raise ValueError("verifies repeats a slug")
        return self


def render_skill_lines(skills: Iterable[SkillState]) -> str:
    """`slug — name — weight — state`, one per line (project.md, rendering contract).

    The state labels are the entire reason this is a separate call: they are what lets the
    prompt aim `verifies` at skills the student has not proven yet. Under the v4 fit formula a
    project verifying an already-covered skill is worth exactly zero percentage points, which
    on stage reads as the feature not working.
    """
    return "\n".join(f"{s.slug} — {s.name} — {s.weight} — {s.state}" for s in skills)


def build_project_prompt(role_title: str, one_liner: str, skills: Iterable[SkillState]) -> str:
    """Render the project prompt for one role. `str.replace`, not `str.format`: the text is
    prose containing braces, and `format` would raise on the first one."""
    return (
        PROJECT_PROMPT.replace("{role_title}", role_title)
        .replace("{one_liner}", one_liner)
        .replace("{skill_lines}", render_skill_lines(skills))
    )


def generate_project(
    role_title: str,
    one_liner: str,
    skills: Iterable[SkillState],
    *,
    client: LLMClient | None = None,
) -> tuple[ProjectOut, str]:
    """One project for one role. Returns `(validated ProjectOut, raw JSON text)`.

    `raw` is returned alongside the parsed model for the same reason `run_analysis` does it: it
    is what gets committed as `contracts/fixtures/demo_project.json`, and re-serialising the
    model would reorder keys and stop the fixture being a faithful record of the run.

    The `verifies ⊆ role slugs` rule goes through `complete_validated`'s `cross_check` hook,
    which exists for exactly this. It has to reject *inside* the retry loop rather than after
    it: a slug the role does not contain is the one failure a second attempt genuinely fixes,
    and letting it reach Salman's router costs the student a 502 instead of a project.

    Comparison is exact — no case folding, no whitespace stripping. He resolves slugs by
    dictionary lookup, so `ETL-Pipelines` 502s exactly as hard as `not-a-skill` does, and
    rejecting it here buys a retry that may come back right.
    """
    skills = list(skills)
    allowed = {s.slug for s in skills}

    def cross_check(parsed: ProjectOut) -> None:
        unknown = [slug for slug in parsed.verifies if slug not in allowed]
        if unknown:
            raise ValueError(f"verifies names slugs outside the role: {', '.join(unknown)}")

    return complete_validated(
        ProjectOut,
        build_project_prompt(role_title, one_liner, skills),
        client=client,
        max_tokens=PROJECT_MAX_TOKENS,
        retry_max_tokens=PROJECT_RETRY_MAX_TOKENS,
        temperature=PROJECT_TEMPERATURE,
        cross_check=cross_check,
    )
