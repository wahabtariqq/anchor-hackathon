# Project-generation prompt — canonical text

**Status:** v1 draft, written from PRD §8.2, CONTRACT §1b, TDD §4.12. **Not yet run** — S6 is
gated on the Day-2 exit criteria (PRD §13).

Rendered by `app/analysis/project.py:build_project_prompt(role_title, one_liner, skills) -> str`.
Called at ~2000 max tokens, temperature 0.5.

---

## Design notes

- **This call fires lazily**, the first time a student opens a role's Prove It panel, and the
  result is cached per (student, role) **forever**. It is never regenerated. So it must be good
  the first time, and it must target the student's gaps *at that moment* — which is the entire
  reason project generation is a separate call rather than being folded into the analysis.
- **`verifies` are slugs from THIS role only.** The grammar cannot express set membership, so
  `generate_project` cross-checks `set(verifies) - allowed` and retries on violation. Salman
  independently 502s a project whose verifies do not resolve (DECISIONS #35) — two checks
  because a `Project` row pointing at nothing would silently verify nothing, forever.
- **Prefer `missing` and `ticked` skills.** Under the v4 formula, proof on an already-covered
  skill changes nothing at all (`max(1.0, …)` is still 1.0). A project verifying skills the
  student already has full coverage of is worth exactly zero percentage points, which on stage
  reads as the feature not working.
- **Criteria must be checkable by reading.** The reviewer cannot run anything. A criterion like
  "the tests pass" is unscoreable and will produce a garbage review.

---

## Prompt text

```text
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
            would not actually be demonstrated by building this, leave it out and claim fewer.
```

---

## Rendering contract for `project.py`

| Placeholder | Rendered as |
|---|---|
| `{role_title}` | `role.title` |
| `{one_liner}` | `role.one_liner` |
| `{skill_lines}` | one line per skill: `{slug} — {name} — {weight} — {state}` |

`SkillState.state` is one of `verified` / `ticked` / `covered:full` / `covered:partial` /
`missing`. Salman's precedence when a skill qualifies for more than one is
`verified > covered:full > ticked > covered:partial > missing` (DECISIONS #34).

> ⚠ **`SkillState` is structurally duplicated, not imported.** Salman re-declared it in
> `routers/project.py` rather than import this package at import time (DECISIONS #33). The two
> definitions are matched **by field name only** — nothing enforces agreement. Renaming a field
> here breaks his caller with no test failure to warn either of us. **Confirm the four names
> with him before writing the dataclass in S6.**
