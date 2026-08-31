# HANDOFF — Dev B (AI lane), ANCHOR

**Written 2026-08-29. Updated 2026-08-30 after S6, S7 and S8 — the AI lane is now feature-complete.**

> **Blocked, or wondering what to do about it? Read `ai-working/UNBLOCK.md`.** It is the
> companion to this file: what is actually stopping work, what only Umer can decide, and what
> needs Salman. Short version: almost nothing is genuinely blocked. Give this to a fresh session before anything else. It exists so nobody
re-derives what has already been measured, and nobody re-opens decisions that are closed.

---

## 1. Sixty-second orientation

ANCHOR turns a CS student's coursework into 8 ranked career roles, shows covered vs missing
skills, and re-ranks live when they tick a skill or pass a repo review. Three devs, three lanes.

**You are Dev B — the AI lane.** You own `backend/app/analysis/`, the three `run_*_cli.py`
scripts, the `demo_*.json` fixtures, and the prompts. Nothing else.

**The other two lanes are effectively finished.** Salman's backend (all routers, `github.py`,
`scoring.py`) and Wahab's frontend (~50 files, Roadmap/drawer/ProveIt) are built. **This lane is
the only thing standing between the team and a working app.** That framing matters when
deciding what to cut.

Work happens **directly on `main`**, committed and pushed each session. There is no worktree —
one was used early and deliberately deleted.

---

## 2. State as of this handoff

**Tests: 268 passing, 0 skipped.** Frontend: 15. **S0-S8 are all done.** S4 was closed with no change needed (DECISIONS #48; seed postings OUT per #49). S6, S7 and S8 landed 2026-08-30: both modules, both CLIs, the demo repo, and all three demo artefacts, generated live and in agreement.

**Nothing in this lane is outstanding.** What is left for the project is deployment, which is Salman's — see section 7.

| File | State |
|---|---|
| `app/analysis/schema.py` | done — `AnalysisOut`, validators V1-V6 |
| `app/analysis/client.py` | done — `LLMClient`, `GeminiClient`, `transform_schema`, retry |
| `app/analysis/prompt.py` | done — `build_prompt`, mirrored template |
| `app/analysis/__init__.py` | done — exports `run_analysis` |
| `app/analysis/export_schema.py` | done |
| `scripts/run_analysis_cli.py` | done — `--demo --runs N --save` + quality report |
| `app/analysis/demo.py` | done — `applies()` + `load()`, DEMO_MODE branch wired into `run_analysis` |
| `app/analysis/project.py` | done — `ProjectOut`, `SkillState`, `generate_project` |
| `app/analysis/review.py` | done — `ReviewOut`, echo check, `score_review`, `review_repo` |
| `scripts/run_project_cli.py` | done — `--role --runs --save` + quality report |
| `scripts/run_review_cli.py` | done — `--url --save --inject` (live injection probe) |

| Fixture | State |
|---|---|
| `demo_analysis.json` | **real** — 48 skills, 8 roles, 28 coverage rows |
| `analysis.schema.json` + `analysis.provider-schema.json` | **real** |
| `demo_project.json` | **real** — Full-Stack Engineer, 3 criteria, 3 verifies |
| `demo_review.json` | **real** — 6/6, passing, against the live demo repo |

**The demo repo is `https://github.com/Umer-prog/cached-product-search-api`** (public, Umer-prog). `DEMO_REPO_URL` must be set to it on the host or the demo submit path never fires.

---

## 3. Environment — you should need none of this explained twice

```
repo    G:\docs\work\OneDrive - Global Data 365\anchor hackathon\anchor-hackathon
venv    backend/.venv           Python 3.12.1, deps pinned exactly
env     backend/.env            gitignored, real Gemini key already in it
```

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q                       # 268 passing
.venv/Scripts/python.exe scripts/run_analysis_cli.py --demo --runs 3
.venv/Scripts/python.exe scripts/run_analysis_cli.py --demo --save
.venv/Scripts/python.exe -m app.analysis.export_schema
.venv/Scripts/python.exe scripts/run_evals.py --offline    # grade the fixtures, no API
.venv/Scripts/python.exe scripts/run_evals.py --suite review   # LIVE, ~3 calls
```

> **Evals spend the demo's budget.** Free tier is 10 requests/min and 250/day, and a full
> live sweep is 9 calls. It hit 429 RESOURCE_EXHAUSTED on 2026-08-31. Use `--offline` while
> iterating on graders; spend live calls deliberately.

> **The API key in `backend/.env` was pasted into a chat transcript. Treat it as exposed and
> rotate it after the demo.** It is free to regenerate at Google AI Studio. It is gitignored and
> appears in no tracked file — verified.

**Two workflow facts about this environment.** The `Write`/`Edit` tools are blocked outside a
worktree, so files get written with shell heredocs — and long heredocs fail, so write in chunks
of roughly 60 lines. A ~150-line heredoc failed again in S6/S7 with
`unexpected EOF while looking for matching quote`; 30-40 lines is comfortable.

**On backslashes, measured rather than assumed (S7).** The rule is narrower than this file used
to say. A **single** backslash survives a heredoc intact — a raw regex written as
`r"```text\n(.*?)\n```"` came out correct and the existing `test_prompt.py` idiom was
reusable as-is. Only a **doubled** backslash collapses: `\\` arrives as `\`. That is
what bit S7 — a line-continuation written as three quotes plus `\\` plus `n` arrived as a
literal `\n` escape, silently giving the mirrored prompt constant a leading newline. The
mirror test caught it. So: write single escapes freely; reach for `chr(92)` only where you
genuinely need two backslash characters, or where a backslash must sit at end of line.

The reliable way to mirror a prompt is not to type it at all — read the `.md`, extract the
fenced text block, and write the constant from it in the same script. Both mirrors were built
that way and matched on the first try.

---

## 4. Closed decisions — do not re-open these

Full reasoning in `docs/DECISIONS.md`. Summarised so a fresh session does not relitigate:

| # | Decision |
|---|---|
| 39 | Provider is **Google Gemini free tier**, not Anthropic. **LangChain was considered and rejected** — the vendor seam already exists in the three public functions, so a swap is ~50 lines in one file, and LangChain would normalise away the raw finish reason the retry policy depends on. |
| 40 | Entry point is **`run_analysis`**, not `run`. Closes the old #11. |
| 41 | `DEMO_STUDENT_NAME` matched case-insensitively. |
| 42 | `ai-working/` lives at repo root; docs and prompts only, no runtime code, nothing imports it. |
| 43 | **The v3 analysis prompt text is lost.** `prompts/analysis.md` was written from scratch. |
| 44 | `requirements.txt` pinned to exact versions. |
| 45 | Gemini over **raw REST via httpx**, not the `google-genai` SDK. |
| 46 | Model pinned to **`gemini-3.6-flash`**. Never a `-latest` alias. |
| 47 | The schema transform must never filter keys inside `properties`. |

---

## 5. Gotchas — each of these cost real time

1. **`gemini-2.5-flash` cannot be called.** It returns *"no longer available to new users"* while
   still appearing in `models.list`, so it fails confusingly rather than obviously. The model
   named in the original docs is dead. Use `gemini-3.6-flash`.

2. **The `google-genai` SDK 403s with this key**, while the identical key works over REST with an
   `x-goog-api-key` header. Do not "fix" `client.py` by switching it to the SDK.

3. **Never filter keys inside `properties` when transforming a schema.** `title` is both a
   JSON-Schema annotation *and* a field on `RoleOut`. Filtering by name deleted the field while
   leaving it in `required`, and Gemini rejected the request with
   `required[1]: property is not defined`. Two regression tests guard this; both were verified by
   reintroducing the bug on purpose and watching them fail.

4. **Gemini's `responseSchema` rejects** `pattern`, `minLength`, `maxLength`,
   `additionalProperties`, and does not follow `$ref` — everything must be inlined. `const` has
   to become a one-item `enum`. This is why the skill-id regex is re-checked in Python.

5. **The free tier really does fail.** Two different models returned 503 "high demand" in a
   single session. That is why `ProviderError` is retryable. Expect it on demo day.

6. **Latency is 53-102 s and highly variable** across identical requests. Budget for the worst
   case, not the median.

7. **The retry policy earns its place — it fired on 1 of 3 live runs**, catching a role that
   referenced a skill the model never minted. Do not weaken it to save latency.

8. **`test_project_review.py` still passes against monkeypatched stubs** installed with
   `raising=False`, and it always will — S6/S7 landing did **not** change that. Green there is
   not evidence about this lane. `tests/test_router_seam.py` (S7) is the file that drives the
   real lane through his routers with only the `LLMClient` faked; that is the one to watch.
   It passed first run — no shape mismatch anywhere.

8b. **A prompt-injection probe against a repo that already scores maximum proves nothing.**
   The first `--inject` run showed 6/6 clean and 6/6 injected, which reads like a pass and is
   pure arithmetic — there was no room to inflate. Probe a repo that scores low. The CLI now
   prints `INCONCLUSIVE` in that case, but the reflex is worth keeping.

9. **`contracts/` is outside `backend/`.** Both the prompt mirror and `demo.py`'s fixture load
   exist because of this: the deployed backend may ship only `backend/`. `demo.py` raises a
   message naming the cause if the fixture is missing on the host — but the deploy config is
   Salman's to fix, and it fails during the pitch if it is wrong.

10. **The schema transform drops `description`**, so Pydantic docstrings never reach the model.
   The only channel for instructing it is `ai-working/prompts/*.md`.

---

## 6. What to do next

**This lane is finished.** S0-S8 are done, 268 tests pass, and all three demo artefacts are real
and mutually consistent. There is no next session queued for the AI lane.

What is genuinely left, in priority order, and **none of it is this lane's**:

1. **Deploy** the API and frontend (section 7). Still the biggest schedule risk in the project.
2. **Set `DEMO_REPO_URL`** on the host to `https://github.com/Umer-prog/cached-product-search-api`.
   One line; without it the demo submit does a live 12-124 s review on stage instead of the 4 s
   cached one.
3. **Rotate the Gemini key** after the demo — it was pasted into a chat transcript.

If someone does reopen this lane, the two things worth knowing:

- **Do not regenerate one demo artefact alone.** The project spec, the repo and the cached
  review are one artefact in three files. `demo.load_review` will refuse a mismatch with a
  legible error, which is the good case; the bad case is regenerating the project and finding
  out on stage. Regenerate all three, in that order, or none.
- **The prompts are v1 and have never been tuned.** Both produced good output on the first live
  run, which is luck as much as design. `run_project_cli.py` and `run_review_cli.py --inject`
  are the tuning loops if output quality ever needs work.

Session plans, inputs, deliverables and done-checks: `ai-working/SESSIONS.md`.

## 7. Blocked on other people

**Full detail and the decisions you need to make: `ai-working/UNBLOCK.md`.**

Almost nothing is genuinely blocked. Correcting an earlier over-escalation: **`SkillState` was
never a blocker** — the four field names are in Salman's committed code at
`backend/app/routers/project.py:29-37` (`slug`, `name`, `weight`, `state`). **S6 can start now.**

**S6 and S7 need nothing from anyone.** So do the three missing `parity_cases.json` cases and
the `contract:` PR for the provider docs.

Only two things genuinely need Salman, and both are deployment:

1. **Deploying the API and frontend.** Nothing is deployed and there is no deploy config in the
   repo at all — no `Procfile`, `railway.json`, `render.yaml` or `vercel.json`, and
   `frontend/.env.example` still has `VITE_USE_FIXTURE=true`. TDD 10 wanted hello-worlds on Day
   1; PRD 13 wants the core on deployed URLs by Day 3 lunch. **This is the biggest schedule risk
   left in the project, and it is not in this lane.**
2. **TDD Appendix B**, only if the deployed host cuts long requests — it edits his
   `routers/analyze.py`. Untestable until (1) exists. If the pitch runs in DEMO_MODE the
   analysis takes 6 s and this never fires.

Waiting on a decision from Umer, not from Salman: ~~the seed-postings in/out call~~ (closed,
DECISIONS #49 — out), a human read of `ai-working/prompts/analysis.md`, ~~and who builds the S8
demo repo~~ (**done — built and pushed under Umer-prog, 2026-08-30**:
`https://github.com/Umer-prog/cached-product-search-api`).

Two things a human should still eyeball, neither blocking: the three prompt files have never had
a human read, and the demo repo's single commit carries a `Co-Authored-By: Claude` trailer that
a judge clicking through would see.

## 8. Where the truth lives

| Question | File |
|---|---|
| What are we building | `docs/PRD.md` |
| How is it built | `docs/TDD.md` |
| Shapes that cross lanes | `docs/CONTRACT.md` |
| Why is it like this | `docs/DECISIONS.md` |
| My plan and done-checks | `ai-working/SESSIONS.md` |
| What I actually did, honestly | `ai-working/BUILD_LOG.md` |
| The prompts | `ai-working/prompts/*.md` |
| Lane rules and commands | `CLAUDE.md`, `backend/CLAUDE.md` |

**Working rules.** Read `.claude/skills/anchor-analysis/SKILL.md` before touching
`app/analysis/`. Run `/test-first` when starting a module and `/spec-check` before committing.
Every session appends to `BUILD_LOG.md` and never edits a past entry. Never edit a fixture to
make a test pass — fix the producer. Anything crossing a lane boundary is a `contract:` PR plus
a chat ping, never a silent local fix.
