---
name: spec-check
description: Use after completing any section or session of ANCHOR work, before committing. Re-reads the specific PRD/CONTRACT/TDD sections the finished work implements, compares the actual files against them point by point, and appends an honest result to ai-working/BUILD_LOG.md. Use it when a session is done, before a commit, before marking anything green, or whenever you are about to say a piece of ANCHOR work is finished.
---

# spec-check

Verify that what was **actually built** matches what the docs **actually say** — then write down
the answer, including when the answer is no.

This exists because the expensive failures on a 3-lane, 4-day build are not bugs. They are
quiet divergences: a field renamed, a return shape changed, a validator relaxed to make a test
pass. Each is individually reasonable and invisible until integration day.

**A deviation is not a failure.** Shipping one without recording it is.

---

## Step 1 — Name the scope

State in one line what work is being checked, and list the **specific doc sections** it
implements. Not "the docs" — section numbers.

Typical mappings in this repo:

| Work | Governing sections |
|---|---|
| `schema.py`, validators V1–V6 | CONTRACT §1, §1.1 · TDD §4.5 |
| `client.py`, retry, truncation | TDD §4.7 · `anchor-analysis` skill "How the call must be made" |
| `prompt.py`, prompt text | PRD §8.1 · `ai-working/prompts/analysis.md` |
| `project.py` | PRD §8.2 · CONTRACT §1b · TDD §4.12 |
| `review.py` | PRD §8.3, §8.4 · CONTRACT §1c · TDD §4.14 |
| `demo.py`, demo fixtures | PRD §12.1, §12.2 · CONTRACT §4 |
| Anything touching fit % | PRD §9 · CONTRACT §2 · TDD §4.6 |

**Re-read those sections now.** Do not check from memory of having read them earlier — that is
the exact mechanism this skill exists to defeat.

## Step 2 — Compare point by point

Walk the requirements in the order the doc states them and check each against the file as it
exists on disk. Read the code; do not infer it from the commit message or from what was
intended.

Where a requirement is testable, **run the test** rather than asserting it passes. "The
validators reject duplicate ids" is a claim; `pytest -q` is evidence.

## Step 3 — Output the table

| Requirement | Source | Status | Note |
|---|---|---|---|
| exactly 8 roles, 5–6 core | CONTRACT §1.1 V2 | met | `test_validation.py::test_role_count` |
| skill ids match kebab pattern | CONTRACT §1.1 V1 | deviated | pattern re-checked post-hoc; provider strips it |
| `run_analysis` returns `(parsed, raw)` | CLAUDE.md seam 1 | met | |

Status is exactly one of **met** / **not met** / **deviated**.

- **met** — implemented as specified.
- **not met** — specified, not implemented. Say whether it is deferred (and to which session)
  or simply missing.
- **deviated** — implemented differently from the spec. Requires Step 4.

Do not pad the table with requirements that were never in scope. Do not report **met** for
something not actually verified — write **not met** and say it was not checked.

## Step 4 — Classify every deviation

For each **deviated** row, state plainly which of these it is:

- **Conscious choice** — decided during development. Record *why the planned path did not work*.
  "The SDK strips `pattern` from the sent schema, so an in-schema regex is unenforceable and the
  check has to be post-hoc" is a reason. "Cleaner this way" is not.
- **Accidental drift** — nobody decided this; it happened. Say so. Then either fix it or open it
  as an explicit question. Accidental drift that is *kept* becomes a conscious choice and needs
  the reason written.

## Step 5 — Lane-boundary check ⚠

For each deviation, ask: **does this change anything another lane can observe?**

Escalate if it touches:

- a **schema** or field name in `AnalysisOut` / `ProjectOut` / `ReviewOut`
- any **contract shape** in CONTRACT §1, §1b, §1c, §3
- a **public signature** — `run_analysis`, `generate_project`, `review_repo`
- the **fixtures** other lanes read (`demo_analysis.json`, `parity_cases.json`)
- anything in `contracts/**`, `models.py`, `schemas.py`, `types.ts`

If it touches any of them, mark the row:

> **needs contract: PR + team ping**

and say which mirrors must change together — `docs/CONTRACT.md`, `backend/app/schemas.py`,
`backend/app/analysis/schema.py`, `frontend/src/lib/types.ts`, and the fixtures.

**Never silently absorb a lane-boundary deviation.** The lanes only work because the seams are
stable; a seam that moves without a ping is how Day 3 integration fails. Two structural traps in
this repo specifically:

- `SkillState` is **duplicated, not imported** (DECISIONS #33), matched by field name only.
  Renaming a field breaks Salman's caller with **no test failure**.
- `test_project_review.py` monkeypatches the AI lane with `raising=False`, so it passes against
  stubs. Green there does **not** mean the real implementation matches.

## Step 6 — Append to BUILD_LOG

Append one entry to `ai-working/BUILD_LOG.md` in the file's template. **Append only — never edit
a past entry.** Fill `Matches spec:` honestly:

- `yes` — every row met.
- `DEVIATION` — one or more deviated rows, each explained per Step 4.

An entry saying `DEVIATION` with a clear reason is a good entry. An entry saying `yes` that
turns out to be wrong on Day 4 costs the demo.

---

## Anti-patterns

- Checking from memory instead of re-reading the sections.
- Marking **met** because a test passes, when the test is monkeypatched against a stub.
- Silently "fixing" the doc to match the code. That is a `contract:` PR, deliberately made.
- Editing a fixture so a check passes. Fix the producer.
- Reporting no deviations because none were found without looking.
