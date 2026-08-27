# Fixtures — what they are, who regenerates them, how

Companion to `contracts/fixtures/README.md`, which is the shared-lane summary. This file is
Dev B's working detail: what actually breaks when a fixture is wrong, and current state.

**The rule that overrides everything here:** *never edit a fixture to make a test pass — fix the
producer.* A fixture edited to satisfy a test stops being evidence of anything.

`contracts/**` is the **shared lane**. Three of these six files are mine to regenerate; the
other three are not mine to touch.

---

## State as of the scaffold commit

| File | Size | State |
|---|---|---|
| `demo_analysis.json` | 75 B | ❌ `{"_todo": …}` placeholder — **mine, S3** |
| `demo_project.json` | 100 B | ❌ `{"_todo": …}` placeholder — **mine, S8** |
| `demo_review.json` | 105 B | ❌ `{"_todo": …}` placeholder — **mine, S8** |
| `courses.json` | 11.7 KB | ✅ real (Salman) |
| `roadmap_response.json` | 24.6 KB | ✅ real (Wahab, hand-written Day 1) |
| `parity_cases.json` | 4.2 KB | ⚠ real but **12 cases, spec asks ~18** — see below |
| `analysis.schema.json` | — | ❌ does not exist yet — **mine, S3** |

**All three demo fixtures are placeholders. All three are mine.** Nothing in the demo path
works until S3 and S8 replace them.

---

## `demo_analysis.json` — mine (S3, refreshed S5)

The validated `AnalysisOut` for the demo student. Written by
`scripts/run_analysis_cli.py --demo --save`.

Read by **two** consumers, which is the thing to remember:
1. `DEMO_MODE` — `load_demo()` serves it for the demo student, with a 6 s sleep.
2. **Salman's persistence tests** — they build DB rows from it.

So a malformed or stale payload does not just degrade the demo, it breaks someone else's test
suite in a lane I do not own.

> **Its coverage `course_code` values must be exactly `CS201`, `CS301`, `CS401`, `CS402`** —
> the demo student's courses. `persistence.py` drops coverage rows whose code is not in the
> student's set, with a log warning and no error. The visible symptom is every fit percentage
> being quietly lower than it should be, on stage, with nothing in the UI indicating why.

Regenerate when the prompt changes materially. Save after every good run — git holds the last one.

## `demo_project.json` — mine (S8, live, Day 4 morning)

`ProjectOut` for the demo student's **top role**. Written by
`scripts/run_project_cli.py --role <slug> --save`, generated live once and then frozen.

## `demo_review.json` — mine (S8, live, Day 4 morning)

A real passing `ReviewOut` of the real repo at `DEMO_REPO_URL`, plus `total` / `max_total` /
`passed`. Written by `scripts/run_review_cli.py --url $DEMO_REPO_URL --save`.

> **These three artefacts must agree, and are regenerated together or not at all:** the project
> spec, the repo Salman builds to satisfy it, and the cached review of that repo. Changing any
> one invalidates the other two. PRD §14 lists "demo repo doesn't pass the cached review on the
> day" as a live risk with exactly this as the mitigation. **Blocked on Salman's repo.**

## `analysis.schema.json` — mine (S3)

JSON Schema of `AnalysisOut`, written by `python -m app.analysis.export_schema`. Reference
material, and optional frontend validation of fixtures. Regenerate whenever `schema.py` changes
— a stale copy is worse than none, because it looks authoritative.

---

## Not mine

### `courses.json` — Salman
Copy of `GET /courses`; feeds the Setup screen in fixture mode.

### `roadmap_response.json` — Wahab, then Salman
Hand-written Day 1 from CONTRACT §3; regenerated Day 2 by `scripts/dump_roadmap.py`. Wahab
builds the entire UI against it with `VITE_USE_FIXTURE=true`. **Integration is defined as done
when the real `GET /roadmap` matches this shape and the flag comes out.**

### `parity_cases.json` — all three, Day 2 morning
Read by both `test_parity.py` and `scoring.test.ts`. Not mine to change alone; a change is a
`contract:` PR.

> **Two discrepancies worth raising with the team — flagged, not fixed:**
>
> 1. **Shape.** CONTRACT §4 describes it as a *list* of `{name, skills, expected}`. The file is
>    `{_comment, cases: [...]}` and `test_parity.py` reads `["cases"]`. Code and file agree; the
>    **contract text is stale**. Documentation fix, no behaviour change.
> 2. **Coverage.** TDD §8 asks for ~18 cases and names **mixed depths**, **core-only**, and
>    **supporting-only** as required. The file has 12 and the test asserts only `>= 12`, so the
>    three named cases are **absent and nothing fails**. The 12 present are good ones — they do
>    include the `max`-semantics proofs (`tick on full = no change`, `verified beats tick`) and
>    a `.5` boundary, which are the cases that actually matter.
>
> PRD §13's cut list ends with **"Never cut the formula parity tests."** Worth ten minutes on
> Day 2 morning while all three are in the room anyway.
