# Decisions log

One line per decision. Newest at the bottom. Add a line whenever you add an endpoint, table,
page, package, or deviate from the TDD — that's the whole process.

`Who` below uses the original lane letters at the time each decision was made: **A = Salman**
(backend), **B = Umer** (AI). Entries after #18 postdate the team settling into Salman/backend,
Umer/AI, Wahab/entire-frontend — see `CLAUDE.md` for the current ownership map.

| # | Decision | Why | Who |
|---|---|---|---|
| 1 | No auth; `X-Student-Id` header + localStorage | New Supabase projects sign JWTs with ES256, v2 HS256 code would 401; auth earns zero judge points | all |
| 2 | Role detail is a drawer on the Roadmap, not a route | Re-sort animation must be on screen at the moment a box is ticked | all |
| 3 | Courses page cut to v2 | Zero seconds in the demo script, half a day of frontend's time | all |
| 4 | Anthropic structured outputs instead of fence-stripping + prefill | Guaranteed parseable JSON; prefill unsupported on 4.6+ and incompatible with structured outputs | B |
| 5 | `bridge` is a plain string ("" for core), not nullable | Union types are the most expensive thing in the output grammar | B |
| 6 | Persistence commits once, no per-row flush | Ids come from `default_factory`; 60+ pooler round trips were pure waste | A |
| 7 | `DEMO_MODE` gated to `DEMO_STUDENT_NAME` | Judges can try their own inputs live after the pitch | all |
| 8 | Re-onboarding creates a new Student, never updates | Removes every cascade-delete case | A |
| 9 | Three top-level lanes: `app/`, `app/analysis/`, `frontend/features/*` | Three people, zero merge conflicts on `main.py` / routers | all |
| 10 | `ANTHROPIC_API_KEY` is optional in `Settings` | Nothing outside `app/analysis/` reads it; the backend must boot for Salman without Umer's key | A |
| 11 | `analyze.py` resolves `app.analysis`'s entry point at call time, accepting `run` or `run_analysis`; 503 until it exists | TDD §4.8 and root `CLAUDE.md` name it differently and the package is still empty — an import-time binding takes `main.py` down with it. **B: pick one name.** | A |
| 12 | `POST /progress` uses select-then-insert/delete, not postgres `ON CONFLICT DO NOTHING` | Same idempotency at one-user concurrency, and it runs on SQLite so persistence has tests | A |
| 13 | `GET /health` added | Railway/Render want a healthcheck; TDD §10 has none | A |
| 14 | `tests/test_api.py` + `httpx`, beyond TDD §12's three files | §12 leaves `persistence.py` and `build_roadmap` — the trickiest code in the lane — with no coverage | A |
| 15 | `backend/pytest.ini` sets `pythonpath = .` | So `pytest -q` from `backend/` works as `backend/CLAUDE.md` documents; there was no pytest config at all | A |
| 16 | `pool_size`/`max_overflow` applied only to postgres URLs | SQLite's pool class rejects them, and local run-throughs and tests use SQLite | A |
| 17 | Catalog curriculum text rewritten to 127-141 words each | The seed shipped at ~53 words against PRD §6.2's 120-200; it is the only course input the one model call gets | A |
| 18 | A missing `X-Student-Id` returns 404, not FastAPI's default 422 | TDD §11 treats missing and unknown alike, and `lib/api.ts` omits the header when localStorage is empty | A |
| 19 | v4: Prove It — project generation + repo review are separate calls; project lazy per (student, role), cached forever | Analysis call at token/quality budget; lazy targets current gaps; pre-baked projects go stale | all |
| 20 | v4: Tick = 0.5, verified = 1.0, combined with `max` not `if/elif` | Self-report ≠ proof; `max` keeps every signal monotonic (the CR's elif chain let a tick lower a covered skill) | all |
| 21 | v4: Verified skills = union over ALL passing submissions, not the latest | Skills are shared across roles; proof via one role's project must count everywhere | all |
| 22 | v4: Repo review reads via GitHub REST only — no clone, no execution; UI says so | Safety + scope; honest about what's scored | B |
| 23 | v4: `passed` threshold (0.6) lives in code, `REVIEW_PASS_RATIO` | Tunable without re-prompting | B |
| 24 | v4: `GITHUB_TOKEN` required; 60 KB input cap; repo contents delimited as untrusted data | 60 req/h unauthenticated would break judge trials; latency; prompt injection | A |
| 25 | v4: GitHub fetch lives in `app/github.py` (Salman), not in `app/analysis/` | Plain HTTP, no AI; balances Umer's Day 3 | all |
| 26 | v4: Prove It gated on Day 2 exit criteria; requires Day 4; cut order per PRD §13 | Core must deploy before any Prove It work | all |
| 27 | v4: Job signal = hand-curated posting excerpt seed set, in only if in the prompt from the start of Day 2 tuning | Grounds requirements without scraping; late context can re-break dedup | all |
| 28 | v4: Rejected — tick 1.0 + verified 1.5× bonus | Exceeds 100 or needs renormalising; doesn't fix tick-everything | all |
| 29 | v4 formula change lands on top of a v3 backend (entries 10-18) not yet migrated | Backend (Salman) built out under v3 before the v4 CR landed; `schemas.py`/`models.py`/`scoring.py`/routers still need the v4 migration — see CONTRACT.md §1b/1c/2/3 | all |
| 30 | v4 migration of entries 10-18 done: `scoring.py`, `models.py`, `schemas.py`, `roadmap.py`, config | Closes #29 — the v3 backend now speaks v4 (`max` formula, `verified`, Project/Submission, project/latest_review) | Salman |
| 31 | `verified_skill_ids()` lives in `persistence.py`, not a new module | Both `roadmap.py` and `submit.py` need the union query; persistence.py already owns analysis rows, and a router importing another router is worse | Salman |
| 32 | `latest_review` is the newest submission per role by `(created_at, id)` | Two submissions in one clock tick must still resolve the same way on every read | Salman |
| 33 | `SkillState` is duplicated in `routers/project.py` rather than imported from `app/analysis/project.py` | Same four field names, matched structurally; importing Umer's empty module at import time would take `main.py` down | Salman |
| 34 | `state` precedence: verified > covered:full > ticked > covered:partial > missing | Contract fixes the five labels, not their order. Tick and partial are both 0.5, so a self-claim is ranked as the thing worth proving | Salman |
| 35 | A project whose `verifies` don't resolve to the role's skills is a 502 with no row written | The AI lane cross-checks too, but a `Project` row pointing at nothing would silently verify nothing forever | Salman |
| 36 | `GITHUB_TOKEN` optional in `Settings`, one warning per process when unset | Same reason as #10 — the API must boot without it; #24's requirement is a deploy checklist item, not a startup crash | Salman |
| 37 | `fetch_repo(url, *, client=None)` accepts an injected httpx client | Tests drive the whole fetch path through `MockTransport` with no monkeypatching and no network | Salman |
| 38 | A role outside the caller's own analysis is 404 on `/project` | TDD §4.15 says "404 if not this student's analysis"; without the check a guessed role id leaks another student's project | Salman |
| 39 | **Model provider is Google Gemini 2.5 Flash (free tier), not Anthropic** — behind a thin `LLMClient` adapter in `client.py`. Claude stays pinned as the declared fallback | Budget: the project is running on free APIs. Gemini is the only free option whose structured output is *schema-constrained decoding* (`response_schema`), which is the assumption the whole lane rests on — validators V1–V6 stay semantic checks instead of also having to defend against malformed JSON. Free tier measured at 10 RPM / 250 RPD / 250k TPM / 1M context. **Rejected: LangChain** — the vendor seam already exists (the three public functions), so a swap is ~50 lines in one file; LangChain would add a large dependency to solve that, while normalising away the raw `finish_reason` the truncation-retry policy depends on and complicating the `(parsed, raw)` return the fixtures need. **Reverses #4** as to vendor; keeps #4's *substance* (constrained decoding over fence-stripping). See `ai-working/BUILD_LOG.md` 2026-08-27 for measured evidence | B |
| 40 | Entry point is **`run_analysis`**, not `run` — closes #11 | #11 assigned "pick one name" to B. `run_analysis` matches `CLAUDE.md` seam #1, the `anchor-analysis` skill, and Salman's call-time resolution which already accepts either. TDD §4.8 still writes `run`, and §4.7/§4.8 additionally disagree on its *arity* (`(student, courses)` vs a pre-built prompt string) — both need a `contract:` PR | B |
| 41 | `DEMO_STUDENT_NAME` matched **case-insensitively** | PRD §12.1 writes `==`; the `anchor-analysis` skill says case-insensitive. A demo lost to a lowercase `ayesha` is not a trade worth making | B |
| 42 | `ai-working/` added at repo root: lane planning, prompt source, append-only build log | Prompt text becomes reviewable in git as prose diffs instead of churn inside a Python string literal. No runtime code, nothing imports it; `backend/app/analysis/` is unchanged per TDD §3 | B |
| 43 | **The v3 analysis prompt text is lost**; `ai-working/prompts/analysis.md` is written from scratch | PRD §8.1 defers to "v3 §8.3", but §8.3 in the v4 PRD is *Repo review call* and no v3 doc is in the repo. Team confirmed nobody has it. Reconstructed from CONTRACT §1, V1–V6, and the skill's four tuning priorities — **review as new work, not as a transcription** | B |
| 44 | `requirements.txt` pinned to exact versions | A transitive dependency changing behaviour between Day 1 and the demo slot is an unforced error. Verified green at 80 passed / 1 skipped on Python 3.12.1 | B |
| — | *(Day 1)* measured analysis latency: ____ s | fill in | B |
