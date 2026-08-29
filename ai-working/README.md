# `ai-working/` — Dev B (AI lane) planning and prompt source

**This directory contains no runtime code and is never imported.** It is the planning,
prompt-authoring, and audit surface for the AI lane. Runtime code lives in
`backend/app/analysis/` per TDD §3 and stays there.

| Question | Answer |
|---|---|
| Who owns this? | Dev B (the AI lane) |
| Does anything import it? | No. Nothing here is on `sys.path`. |
| Where is the actual code? | `backend/app/analysis/` — unchanged, per TDD §3 |
| Where do fixtures live? | `contracts/fixtures/` — unchanged, per CONTRACT §4 |

## What lives here vs. `backend/app/analysis/`

| Here (`ai-working/`) | There (`backend/app/analysis/`) |
|---|---|
| `prompts/analysis.md` — the canonical prompt **text** | `prompt.py` — the code that renders it with student data |
| `prompts/project.md` | `project.py` |
| `prompts/review.md` | `review.py` |
| `HANDOFF.md` — briefing for a fresh session: state, closed decisions, gotchas | — |
| `SESSIONS.md` — the work plan | — |
| `BUILD_LOG.md` — append-only record of what was actually done | — |
| `fixtures_notes.md` — what each fixture is, who regenerates it, how | `contracts/fixtures/*.json` — the fixtures themselves |

**The prompts here are the source of truth for prompt text.** `prompt.py` renders these
strings with the student's semester, interests, and courses. When you tune a prompt, edit the
`.md` here first, then mirror it into the module — so prompt history is reviewable in git as
prose diffs rather than as churn inside a Python string literal.

## Public surface — the only thing other lanes import

Fixed by `CLAUDE.md` integration seam #1 and `.claude/skills/anchor-analysis/SKILL.md`.
Salman's routers depend on these signatures; do not change them without a `contract:` PR.

```python
from app.analysis import run_analysis, generate_project, review_repo, AnalysisFailed

parsed, raw                         = run_analysis(student, courses)
project, raw                        = generate_project(role_title, one_liner, skill_states)
review, total, max_total, passed    = review_repo(project, bundle)
```

All three raise `AnalysisFailed` after one retry. `passed` is computed in `review.py`, never
by the model. Fit % is computed in `scoring.py` — **not this lane's code at all.**

> **Naming note.** TDD §4.8 writes the entry point as `run`; `CLAUDE.md` and the
> `anchor-analysis` skill write `run_analysis`. DECISIONS #11 logged this as unresolved and
> assigned it to Dev B. **Resolved: `run_analysis`** — it matches `CLAUDE.md`, the skill, and
> Salman's call-time resolution, which already accepts either. See DECISIONS #40.

## Model provider

**Google Gemini 2.5 Flash, free tier**, behind a thin `LLMClient` adapter that makes the
provider a one-class swap. Claude is the declared fallback and stays pinned in
`requirements.txt` so the fallback is real rather than theoretical.

Full reasoning, alternatives rejected, and the measured risks: **DECISIONS #39**. Do not
re-litigate the choice from this file — it is a summary, not the record.

## Working rules for this lane

1. **Read `.claude/skills/anchor-analysis/SKILL.md` before any task in `app/analysis/`.**
2. **Use `/test-first`** when starting any new module, validator, or prompt.
3. **Use `/spec-check`** after finishing any session, before committing.
4. **Every session appends to `BUILD_LOG.md`.** Append only — never edit a past entry.
5. **Never edit a fixture to make a test pass.** Fix the producer. (`contracts/fixtures/README.md`)
6. **Anything crossing a lane boundary** — schemas, contract shapes, API signatures — is a
   `contract:` PR plus a chat ping, never a silent local fix.
