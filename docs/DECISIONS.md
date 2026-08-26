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
| — | *(Day 1)* measured analysis latency: ____ s | fill in | B |
