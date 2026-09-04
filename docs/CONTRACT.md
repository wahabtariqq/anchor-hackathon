# ANCHOR — Shared Contract (v4)

This file is the single source of truth for every shape that crosses a lane boundary.
Its mirrors are `backend/app/schemas.py`, `backend/app/analysis/schema.py`,
`frontend/src/lib/types.ts`, and the fixtures in `contracts/fixtures/`. A change here is a
`contract:` PR that updates all of them at once.

---

## 1. Model output — `AnalysisOut`

Produced by `backend/app/analysis/`. Guaranteed parseable by structured outputs; semantics
enforced by validators (§1.1).

```jsonc
{
  "skills": [                                  // 40–60
    { "id": "sql-query-optimization",          // kebab-case, unique
      "name": "SQL Query Optimization",
      "real_world": "Cutting a 4-second dashboard query to 40ms is usually one missing composite index." }
  ],
  "coverage": [
    { "skill_id": "sql-query-optimization",    // must exist in skills[]
      "course_code": "CS301",                  // one of the student's codes, else dropped with warning
      "depth": "full" }                        // "full" | "partial"
  ],
  "roles": [                                   // exactly 8
    { "id": "data-engineer",
      "title": "Data Engineer",
      "one_liner": "Builds the pipelines that move and reshape data for analysts and models.",
      "proximity": "core",                     // "core" (5–6) | "adjacent" (2–3)
      "bridge": "",                            // "" for core; non-empty sentence for adjacent
      "rank": 1,                               // 1..8, model's ordering, tiebreaker only
      "skills": [                              // 10–14, no repeats
        { "skill_id": "sql-query-optimization", "weight": "core" },      // "core" | "supporting"
        { "skill_id": "python-scripting",       "weight": "supporting" }
      ] }
  ]
}
```

All fields required. No nulls anywhere.

### 1.1 Validation rules (hard-fail → retry once → 502)

| # | Rule |
|---|---|
| V1 | 35 ≤ `skills.length` ≤ 70; ids unique; ids match `^[a-z0-9]+(-[a-z0-9]+)*$` |
| V2 | `roles.length == 8`; 5 ≤ core roles ≤ 6 |
| V3 | every `roles[].skills[].skill_id` exists in `skills[]` |
| V4 | every `coverage[].skill_id` exists in `skills[]` |
| V5 | no `skill_id` repeated within one role; 8 ≤ skills per role ≤ 16 |
| V6 | adjacent roles have non-empty `bridge` |

Soft (warn + skip): `coverage[].course_code` not in the student's codes; duplicate `(skill, course)` coverage pair.

---

## 1b. Project generation output — `ProjectOut`

```jsonc
{ "title": "Build a log-ingestion pipeline",
  "spec": "3–4 sentences: what to build, what done looks like.",
  "criteria": ["…", "…", "…"],                     // 3–4, each checkable by READING the repo
  "verifies": ["containerization", "etl-basics"] }  // 2–4 skill SLUGS from the role; prefer missing/ticked
```
Hard-fail: 3–4 criteria · 2–4 verifies · no duplicates · every slug in the role's skill list. Resolved to DB ids before storage.

## 1c. Repo review output — `ReviewOut`

```jsonc
{ "criteria_scores": [ { "criterion": "…", "score": 1, "note": "one sentence" } ],   // same count + order as project.criteria; score ∈ {0,1,2}
  "feedback": "One short paragraph to the student." }
```
Hard-fail: count/order mismatch (case-insensitive compare) · score outside 0–2.
**Computed in code:** `total = Σ score`, `max_total = 2 × criteria`, `passed = total ≥ ceil(REVIEW_PASS_RATIO × max_total)` with `REVIEW_PASS_RATIO = 0.6`.

## 2. Fit % formula (v4)

Identical in `backend/app/scoring.py` and `frontend/src/lib/scoring.ts`. Tested against
`contracts/fixtures/parity_cases.json` in both.

```
WEIGHT = { core: 3, supporting: 1 }
DEPTH  = { full: 1.0, partial: 0.5 }

TICK   = 0.5          # self-report earns half
PROOF  = 1.0          # passing repo submission earns full

earned = total = 0
for each skill in role:
    w = WEIGHT[weight]
    total += w
    earned += w * max( PROOF if verified else 0,
                       TICK  if checked  else 0,
                       DEPTH[coverage_depth] if coverage_depth else 0 )
fit = half_up(earned / total * 100)   # 0 when total == 0
```

`max`, never `if/elif`: no action a student takes may lower a score. A tick on a fully-covered skill changes nothing; proof on a fully-covered skill changes nothing.
`verified` = the skill id is in the union of `verified_skill_ids` over **all** of the student's passing submissions (any role).

- `coverage_depth` is the **best** depth across all courses covering that skill (full > partial > none). Collapsed once when building the roadmap payload, not inside the formula.
- Rounding: Python `round()` and JS `Math.round()` differ on exact `.5` (banker's vs half-up). Use `Math.floor(x + 0.5)` in TS and `int(x + 0.5)` in Python so both are half-up. Include a `.5` case in the parity fixture.
- Sort: `fit_percent` desc, then `rank` asc.
- Below 15%: still shown, labelled "Not enough foundation yet."

---

## 3. HTTP API

Base `/api`. JSON in and out. All routes except `GET /courses` require header `X-Student-Id: <uuid>`.
Unknown id → `404 {"detail": "Unknown student — start over"}`.

### `GET /courses` → 200

```json
{ "courses": [
  { "id": "cs301", "code": "CS301", "name": "Database Management Systems",
    "curriculum_text": "Relational model, ER design, normalisation…" }
]}
```

### `POST /students` → 201

Request:
```json
{
  "name": "Ayesha",
  "semester": 4,
  "interests": ["Artificial Intelligence", "Databases", "UI/UX Design"],
  "courses": [
    { "course_id": "cs201", "semester_tag": "past" },
    { "course_id": "cs301", "semester_tag": "past", "curriculum_override": "Our DBMS course also covers…" },
    { "course_id": "cs401", "semester_tag": "current" },
    { "custom_name": "Human-Computer Interaction", "semester_tag": "current",
      "curriculum_text": "Heuristic evaluation, wireframing, usability testing…" }
  ]
}
```
Response: `{ "student_id": "6f1c…" }`

Validation → 422: 3 ≤ courses ≤ 6 · interests ≥ 2 · every `course_id` in catalog · custom courses need `custom_name` and `curriculum_text` ≥ 50 chars.
Server resolves `curriculum_text` as override → custom → catalog, and assigns `code` = catalog code or `CUSTOM-1`, `CUSTOM-2`…

### `POST /analyze` → 200 `{ "ok": true }`

Errors: `409` analysis exists · `422` no courses · `502` model failed after retry.
Slow (1–3 min live; 6 s in demo mode). Client timeout 240 s.

### `GET /roadmap` → 200

```jsonc
{
  "student": { "name": "Ayesha", "semester": 4, "interests": ["Artificial Intelligence", "Databases", "UI/UX Design"] },
  "skills": [                                          // flat, global — roles & courses reference by id
    { "id": "sk_a1", "slug": "sql-query-optimization", "name": "SQL Query Optimization",
      "real_world": "Cutting a 4-second dashboard query to 40ms is usually one missing composite index.",
      "coverage_depth": "full",                        // "full" | "partial" | null  (already collapsed to best)
      "covered_by": ["CS301"],                         // course codes, may be empty
      "checked": false,
      "verified": true }                               // in the union of passing submissions' verified_skill_ids
  ],
  "roles": [                                           // pre-sorted by (-fit_percent, rank)
    { "id": "ro_b2", "slug": "data-engineer", "title": "Data Engineer",
      "one_liner": "Builds the pipelines that move and reshape data.",
      "proximity": "core", "bridge": "", "rank": 1,
      "fit_percent": 64,
      "skills": [ { "skill_id": "sk_a1", "weight": "core" } ],
      "project": null,                                 // or the GET /project shape once generated
      "latest_review": null }                          // or the review object from POST /submit
  ],
  "courses": [
    { "id": "sc_c3", "code": "CS301", "name": "Database Management Systems",
      "semester_tag": "past", "skill_ids": ["sk_a1"] }
  ]
}
```

`404` if no analysis yet. Note ids here are DB ids (`sk_…`, `ro_…`), not the model's slugs.

### `GET /project?role_id=…` → 200

```json
{ "id": "pr_9d", "role_id": "ro_b2", "title": "…", "spec": "…", "criteria": ["…","…","…"], "verifies": ["sk_a1", "sk_f4"] }
```
Generates on first call (3–10 s), cached after. `404` unknown role.

### `POST /submit` → 200

Request `{ "role_id": "ro_b2", "repo_url": "https://github.com/owner/repo" }`

```jsonc
{ "review": { "criteria_scores": [ { "criterion": "…", "score": 2, "note": "…" } ],
              "feedback": "…", "total": 5, "max_total": 6, "passed": true },
  "verified_skill_ids": ["sk_a1", "sk_f4", "sk_c2"] }   // FULL set for the student — client replaces, never merges
```
`409` no project yet · `422` `{detail: <user-facing repo message>}` · `502` review failed twice. 15–60 s live, 4 s demo.

### `POST /progress` → 200 `{ "ok": true }`

Request: `{ "skill_id": "sk_a1", "checked": true }`. Idempotent both ways.

---

## 4. Fixtures in `contracts/fixtures/`

| File | Shape | Written by | Read by |
|---|---|---|---|
| `demo_analysis.json` | §1 `AnalysisOut` | Umer, `run_analysis_cli.py --demo` | `DEMO_MODE`; persistence tests |
| `roadmap_response.json` | §3 `GET /roadmap` | Wahab hand-writes Day 1 from this doc; Salman regenerates Day 2 via `dump_roadmap.py` | frontend with `VITE_USE_FIXTURE=true` |
| `parity_cases.json` | list of `{ name, skills[{weight, coverage_depth, checked, verified}], expected }` | all three, Day 2 morning | `test_parity.py`, `scoring.test.ts` |
| `demo_project.json` | §1b `ProjectOut` for the demo student's top role | Umer, `run_project_cli.py` (live, Day 4 morning) | `DEMO_MODE` |
| `demo_review.json` | §1c `ReviewOut` + total/max_total/passed for `DEMO_REPO_URL` | Umer, `run_review_cli.py` (live, Day 4 morning) | `DEMO_MODE` |
| `analysis.schema.json` | JSON Schema of §1 | Umer, `export_schema.py` | reference; optional frontend validation of fixtures |
| `project.schema.json`, `review.schema.json` | JSON Schema of §1b, §1c | Umer, `export_schema.py` | reference; added once S6/S7 landed |
| `*.provider-schema.json` | the same three, as the provider actually receives them | Umer, `export_schema.py` | shows which keywords the transform strips (`pattern`, length bounds) |

**Integration is done when** `GET /roadmap` from the deployed backend, for the demo student, has
the exact shape of `roadmap_response.json` and the frontend renders it with `VITE_USE_FIXTURE` removed.

---

## 5. Enumerations

| Field | Values |
|---|---|
| `score` | `0`, `1`, `2` |
| `depth`, `coverage_depth` | `full`, `partial` (+ `null` only in the roadmap response) |
| `weight` | `core`, `supporting` |
| `proximity` | `core`, `adjacent` |
| `semester_tag` | `past`, `current` |
| `interests` | `Artificial Intelligence`, `Databases`, `UI/UX Design`, `Web Development`, `Systems & Infrastructure`, `Data Analysis`, `Security`, `Mobile` |
| catalog `course_id` | `cs201`, `cs202`, `cs301`, `cs302`, `cs303`, `cs401`, `cs402`, `cs403`, `cs404`, `cs405` |

---

## 6. V2 addendum — accounts and sessions

Mirrors: `backend/app/schemas.py`, `frontend/src/lib/types.ts`. Design: `docs/TDD-V2.md` §4.3-§4.4, §6.

**Authentication changed.** V1's `X-Student-Id: <uuid>` header is gone. Every route except
`GET /api/courses`, `POST /api/auth/signup` and `POST /api/auth/login` requires:

```
Authorization: Bearer <token>
```

Two failures, and they mean different things:

| Status | Meaning | Client does |
|---|---|---|
| `401` | no token, malformed header, unknown token, or expired session | clear the token → `/login` |
| `404 {"detail": "No student profile yet — complete onboarding"}` | authenticated, but this account has no `Student` yet | → `/onboarding` |

### `POST /api/auth/signup` → 200

```json
{ "email": "ayesha@example.com", "password": "at-least-8-chars", "name": "Ayesha",
  "claim_student_id": "6f1c…" }
```
→ `{ "user": { "id": "…", "email": "…", "name": "Ayesha", "created_at": "…" } }`

**No token.** Signup creates the account; a login establishes the session, signup included.
`claim_student_id` is optional and adopts a V1 anonymous student **only if it is unclaimed** —
an already-owned or unknown id is ignored silently, not an error.
Errors: `409` email already registered · `422` password under 8 characters or over 72 **bytes**
(bcrypt's hard limit), malformed email, blank name.

### `POST /api/auth/login` → 200

```json
{ "email": "ayesha@example.com", "password": "…" }
```
→ `{ "token": "…", "user": { … } }` — the only response that carries a token.

Errors: `401 "Wrong email or password"` — identical for a wrong password and an unknown email,
deliberately, so this is not an account-enumeration oracle · `429` after
`LOGIN_RATE_LIMIT` failures for that email within `LOGIN_RATE_WINDOW_MIN` minutes.

### `POST /api/auth/logout` → 200 `{ "ok": true }`

Deletes the calling token's session. Idempotent: a stale, missing or unknown token still
returns 200, because the caller's goal — no usable session — is already met.

### `POST /api/auth/logout_all` → 200 `{ "ok": true }`

Deletes every session for the caller. Requires a valid token (`401` otherwise).

### `POST /api/students` — changed

Now requires a bearer token and attaches the created `Student` to the caller's account. Request
and response shapes are unchanged from §3. An account that re-onboards gets a **new** `Student`
row (DECISIONS #8) and the newest one is the live one.

### Unchanged

`GET /courses` (still public), `POST /analyze`, `GET /roadmap`, `POST /progress`,
`GET /project`, `POST /submit` — same request and response shapes as §3, only the auth header
differs. The roadmap payload is byte-for-byte what V1 returned.

---

## 7. V2 addendum — events, snapshots, and the three aggregation reads

Mirrors: `backend/app/schemas.py`, `frontend/src/lib/types.ts`. Design: `docs/TDD-V2.md`
§4.5-§4.8. All three require `Authorization: Bearer`, and all three answer `404 {"detail": "No
student profile yet — complete onboarding"}` for an authenticated account that has not onboarded
(§6's table) — which is a different answer from `401`.

### Write side: `POST /api/progress` and `POST /api/submit` — changed

Request and response shapes are **unchanged**. Both now additionally write, inside their own
existing transaction:

- one `event` row per action — `tick` / `untick` for progress; `submission` plus, when it
  passed, `pass` for submit;
- one `fit_snapshot` row per role whose `fit_percent` **actually changed**. A tick on a skill a
  course already covers in full moves nothing (`fit_percent` takes a `max`, §2), so it writes an
  event and no snapshot. A rejected request writes neither.

Events are keyed to the **account**, not the student, so a re-onboarding student keeps their
activity feed. Snapshots reference the analysis's role ids, so a re-analysis starts a fresh
chart rather than splicing two different role sets into one line.

### `GET /api/dashboard` → 200

```json
{
  "top_role": { "id": "ro_b2", "title": "Data Engineer", "fit_percent": 71 },
  "skills_verified": 6, "skills_checked": 11,
  "verified_delta": 2, "checked_delta": 9,
  "snapshots": { "ro_b2": [ { "fit": 48, "at": "2026-08-20T…" }, { "fit": 71, "at": "…" } ] },
  "next_actions": [ { "role_id": "ro_b2", "label": "Learn Airflow Basics", "kind": "tick" } ],
  "recent_events": [ { "text": "Verified skills for Data Engineer via repo review", "at": "…" } ]
}
```

- `snapshots` and `next_actions` cover the **top three core roles**, in the same order, so a
  client can walk either one and stay aligned with the other. Adjacent roles are never charted.
- Snapshot points are oldest-first. A key with `[]` means "no movement recorded yet" — there is
  no backfill, history starts at V2 deploy.
- `kind` is `"project"` when the role has a generated project with no passing submission
  (`"Finish {title} — verifies {n} skills"`), else `"tick"` (`"Learn {skill}"`, the
  highest-weight unresolved skill). A role with nothing unresolved and nothing to prove falls
  back to `"Review {role}"`, still `kind: "tick"`.
- Deltas count events since `user.last_seen_at`, which only a **login** moves. `recent_events`
  is the last 10, newest first, and its `text` is joined to skill/role names at read time — a
  later rename never leaves a stale sentence behind.

### `GET /api/skills` → 200

```json
{ "skills": [ { "id": "sk_a1", "slug": "sql-query-optimization",
               "name": "SQL Query Optimization", "real_world": "…",
               "coverage_depth": "full", "checked": false, "verified": true,
               "roles": [ { "id": "ro_b2", "title": "Data Engineer" } ] } ] }
```

Every skill in the student's analysis, in `GET /roadmap`'s own `(name, slug)` order, each with
every role that wants it (best-fit role first). The four state fields are the same values
`/roadmap` reports for that skill — **there is deliberately no server-side status enum**; the
Verified/Learned/Covered/Partial/Missing pill is derived on the client from these, so the
Skills screen and the roadmap drawer cannot disagree.

### `GET /api/projects` → 200

```json
{ "projects": [ { "project": { "id": "pr_9d", "role_id": "ro_b2", "title": "…", "spec": "…",
                              "criteria": ["…"], "verifies": ["sk_a1"] },
                 "submissions": [ { "id": "sb_1", "repo_url": "…", "total": 5, "max_total": 6,
                                   "passed": true, "created_at": "…",
                                   "criteria_scores": [ { "criterion": "…", "score": 2,
                                                         "note": "…" } ],
                                   "feedback": "…" } ] } ] }
```

Every project the student has generated, newest first, each with its full submission history
newest-first. `project` is byte-identical to what `GET /api/project?role_id=` returns for that
role — the plural view never reshapes it. `{"projects": []}` before Prove It is ever opened.
Submissions are append-only: a failed attempt stays in the history after a later pass.
