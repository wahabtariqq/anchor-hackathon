# Decisions log

One line per decision. Newest at the bottom. Add a line whenever you add an endpoint, table,
page, package, or deviate from the TDD — that's the whole process.

| # | Decision | Why | Who |
|---|---|---|---|
| 1 | No auth; `X-Student-Id` header + localStorage | New Supabase projects sign JWTs with ES256, v2 HS256 code would 401; auth earns zero judge points | all |
| 2 | Role detail is a drawer on the Roadmap, not a route | Re-sort animation must be on screen at the moment a box is ticked | all |
| 3 | Courses page cut to v2 | Zero seconds in the demo script, half a day of Dev C's time | all |
| 4 | Anthropic structured outputs instead of fence-stripping + prefill | Guaranteed parseable JSON; prefill unsupported on 4.6+ and incompatible with structured outputs | B |
| 5 | `bridge` is a plain string ("" for core), not nullable | Union types are the most expensive thing in the output grammar | B |
| 6 | Persistence commits once, no per-row flush | Ids come from `default_factory`; 60+ pooler round trips were pure waste | A |
| 7 | `DEMO_MODE` gated to `DEMO_STUDENT_NAME` | Judges can try their own inputs live after the pitch | all |
| 8 | Re-onboarding creates a new Student, never updates | Removes every cascade-delete case | A |
| 9 | Three top-level lanes: `app/`, `app/analysis/`, `frontend/features/*` | Three people, zero merge conflicts on `main.py` / routers | all |
