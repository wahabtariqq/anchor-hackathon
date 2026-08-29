"""Renders the analysis prompt (PRD 8.1) with one student's real coursework.

The canonical text lives in `ai-working/prompts/analysis.md` and is MIRRORED into the constant
below rather than read from disk at runtime: the deployed backend ships `backend/` only, and a
runtime dependency on a docs directory outside it would work locally and fail on Railway.
`tests/test_prompt.py` asserts the two never drift, so the mirror cannot rot silently.

The v3 prompt text is lost (DECISIONS #43) -- PRD 8.1 defers to "v3 8.3", but 8.3 in the v4 PRD
is *Repo review call* and no v3 document exists in the repo. This text was written from scratch
against CONTRACT 1, the V1-V6 validators, and the tuning priorities in the anchor-analysis skill.

Substitution is `str.replace`, not `str.format`: the prompt is prose that may grow braces (JSON
examples, set notation) and `format` would raise on the first one.
"""

from __future__ import annotations

from typing import Any, Iterable

# --- mirrored from ai-working/prompts/analysis.md - edit THERE first, then here -----------
ANALYSIS_PROMPT = """\
You are mapping a computer-science student's completed coursework onto the career roles they
are genuinely closest to, and onto the specific skills that separate them from those roles.

Your entire output is a single structured object. Its shape is enforced for you — spend your
effort on the quality of the content, not on the format.

## The student

Semester: {semester}
Interest areas they chose: {interests}

Courses they have taken or are taking, each with its real syllabus:

{courses}

## What you are producing

### 1. skills — 45 to 55 atomic capabilities

Each skill is one named, testable capability with a stable kebab-case id.

The skill list is the vocabulary the entire product is built on. Roles reference it, courses
reference it, and student progress is stored against it. Everything downstream depends on this
list being clean.

CRITICAL — no near-duplicates. This is the single most important constraint in this task.
Two entries that a practitioner would call the same skill must be ONE entry. Before you emit
the list, read it back and merge anything that overlaps.

  Wrong: "sql", "sql-querying", "relational-databases", "database-queries"  → these are ONE skill
  Wrong: "git", "version-control", "git-workflows"                          → these are ONE skill
  Wrong: "rest-apis", "api-design", "http-services"                         → these are ONE skill
  Right: "sql-query-optimization" and "database-schema-design" — genuinely different work

Prefer the specific, useful name over the broad category. "sql-query-optimization" is a skill
a person can learn and demonstrate; "databases" is a topic, not a skill.

Granularity: a skill should be something a person could plausibly learn in one to three weeks
of focused work and then show evidence of. Not "programming". Not "knows what an index is".

Each skill needs:
  - id        kebab-case, lowercase letters, digits and single hyphens only. Unique.
  - name      how a practitioner would say it out loud. "SQL Query Optimization".
  - real_world  ONE sentence. A concrete situation, number, or consequence from actual work.

  real_world is what the student reads next to a checkbox. Make it land.

  Good: "Cutting a 4-second dashboard query to 40ms is usually one missing composite index."
  Good: "The first time a queue backs up at 3am, you learn why idempotent consumers matter."
  Bad:  "Used in many software engineering jobs."      ← says nothing
  Bad:  "Important for backend developers."            ← says nothing
  Bad:  "A key skill for working with databases."      ← says nothing

  If a sentence would still be true with the skill name swapped out, rewrite it.

### 2. coverage — which of THEIR courses taught which skill

For each skill their coursework genuinely covers, one entry:
  - skill_id      must be an id from your skills list
  - course_code   must be exactly one of: {course_codes}
  - depth         "full" if the course teaches it properly and they can do it now
                  "partial" if the course introduces or touches it

Read each syllabus above and be honest. Do not credit a course for a skill it merely mentions
in passing — mark that "partial", or leave it out. Coverage is what makes the fit percentage
defensible, and a student reading their own roadmap will immediately notice if you claim their
intro course taught them distributed systems.

Leave genuinely uncovered skills out of coverage entirely. Gaps are the product. A roadmap
where everything is already covered tells the student nothing and shows them nowhere to go.

### 3. roles — exactly 8

Five or six with proximity "core", and the remaining two or three with proximity "adjacent".

  core      roles their coursework and interests point at directly
  adjacent  roles they did not ask for and probably have not considered, but are genuinely
            close to given what they have actually studied

The adjacent roles are the most interesting thing in this product. They should make the
student think "I hadn't considered that, but I can see it." Not a random pivot, and not a
near-copy of a core role with a different title.

Each role needs:
  - id         kebab-case, unique across roles
  - title      the job title a company would post. "Data Engineer".
  - one_liner  one sentence on what the person actually does day to day
  - proximity  "core" or "adjacent"
  - bridge     "" for core roles.
               For adjacent roles: one sentence, addressed to the student as "you", naming
               the SPECIFIC course or interest that connects them to this role.

               Good: "Your DBMS coursework and your UI/UX interest converge here — analytics
                      engineers spend their days making data legible to people."
               Bad:  "This role is related to your interests."     ← names nothing, cut it

  - rank       1 to 8, your honest ordering, best fit first. Each number used exactly once.
               This is only a tiebreaker downstream; the displayed percentage is computed
               arithmetically from coverage, not from your ranking.

  - skills     10 to 14 entries, no skill repeated within a role, each with:
                 skill_id  an id from your skills list
                 weight    "core"       — you cannot hold this job without it
                           "supporting" — makes you better at it

               About 4 to 6 core-weighted per role; the rest supporting.

REUSE SKILLS ACROSS ROLES. This matters as much as the dedup rule.

These eight roles are neighbouring regions of one field, not eight unrelated jobs. A skill
that matters to a Data Engineer usually also matters to a Backend Engineer and an ML Engineer.
Most skills should appear in two, three, or four roles. If almost every skill appears in
exactly one role, you have written eight isolated lists and the result is wrong — the whole
premise is that these paths overlap and that progress on one moves the others.

Every role must include some skills the student already has covered and some they do not. A
role where they have everything, or nothing, is not a useful destination.

## Before you answer

Check your own output:
  - Any two skills that mean the same thing? Merge them.
  - Any real_world sentence that would survive swapping in a different skill name? Rewrite it.
  - Do most skills appear in more than one role? If not, redistribute.
  - Does every adjacent bridge name a specific course or interest of theirs?
  - Does every coverage entry use a course code from {course_codes}?
  - Are the ranks 1 through 8, each used once?
{postings_block}"""
# -----------------------------------------------------------------------------------------


def render_courses(courses: Iterable[Any]) -> str:
    """One block per course: `CS301 - Database Management Systems (past)` then its syllabus.

    `curriculum_text` is already resolved server-side as override > custom paste > catalog
    default. The catalog entries were rewritten to 127-141 words each (DECISIONS #17) precisely
    because this prompt is the only place that text is ever used.
    """
    return "\n\n".join(
        f"{c.code} - {c.name} ({c.semester_tag})\n{c.curriculum_text}" for c in courses
    )


def build_prompt(student: Any, courses: Iterable[Any], *, postings_block: str = "") -> str:
    """The AI lane's prompt for one student. `courses` are that student's StudentCourse rows.

    `postings_block` is empty unless the seed set is adopted (PRD 8.6). If it is used at all it
    must be present from the START of Day-2 tuning: adding grounding context after dedup is
    tuned can re-break dedup, which is why that deadline is a gate and not a preference.
    """
    courses = list(courses)
    return (
        ANALYSIS_PROMPT.replace("{semester}", str(student.semester))
        .replace("{interests}", ", ".join(student.interests))
        .replace("{courses}", render_courses(courses))
        .replace("{course_codes}", ", ".join(c.code for c in courses))
        .replace("{postings_block}", postings_block)
    )
