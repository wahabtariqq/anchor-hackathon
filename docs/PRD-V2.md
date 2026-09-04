# ANCHOR — Product Requirements Document V2

**"From a form to a product" · 3 people · 2 days, after V1's core is frozen**
**Baseline:** V1 complete (analysis → roadmap → ticks → Prove It), dark mode, single-flow UI, three screens only.
**Status:** Proposed. This is the planned continuation of `docs/PRD.md` §16 ("v2 — README only, do not build [yet]"); it is not yet team-ratified the way `docs/PRD.md` is Locked.
**Build status (2026-09-04):** V2 is **complete end to end.** The frontend (§3, §4, §8) was
built first against fixtures; the auth lane (§5) landed next; the events/aggregation lane
(§6-§7 — `event`, `fit_snapshot`, `/api/dashboard`, `/api/skills`, `/api/projects`) landed last
and the frontend was cut over to it, deleting the fixture shim and the simulated event log that
stood in for it. Every item in §11's gap checklist is built. See `docs/TDD-V2.md` §7.5.

*Why V2: V1 proves the engine, but it reads as a one-shot form — you fill it in, you see a result, you leave. Nothing invites you back. V2's single job is to make ANCHOR a place a student returns to: an account they log into, a dashboard that shows what changed since last time, and screens that feel like an application, not a wizard. No new AI work. The engine is done; V2 is identity, memory, and skin.*

---

## 0. Current-state audit

Before scoping V2, this section checks the assumptions above and everywhere below against what's actually in the repo today. Every other section keeps the original V2 draft's wording; treat this table as the correction layer.

| V2 assumes | Actual state | Evidence |
|---|---|---|
| Accounts / sessions | **Don't exist.** Identity is the anonymous `X-Student-Id` header + `localStorage`, unchanged from V1. No `user`, `session`, `bcrypt`, `jwt`, or password anywhere in `backend/app`. | `backend/app/identity.py` ("a student id is a capability"); `frontend/src/lib/identity.ts` |
| `event` / `fit_snapshot` tables | **Don't exist.** Fit % is recomputed on every `GET /api/roadmap` read, never persisted. | `backend/app/models.py` (only `Student`, `Course`, `StudentCourse`, `Analysis`, `Skill`, `Role`, `RoleSkill`, `Coverage`, `Progress`, `Project`, `Submission`); `backend/app/scoring.py` |
| `/api/dashboard`, `/api/skills`, `/api/auth/*` | **Don't exist.** Seven routes total today: `/api/courses`, `/api/students`, `/api/analyze`, `/api/roadmap`, `/api/progress`, `/api/project` (singular), `/api/submit`. | `backend/app/main.py` router mounts |
| Left sidebar + topbar app shell | **Doesn't exist.** `AppShell.tsx` is a minimal top bar (wordmark + student name) with an explicit code comment that this is deliberate: *"PRD §10 mandates exactly these three screens... no nav links, no settings, no login."* Router has exactly 4 routes: `/`, `/setup`, `/analyzing`, `/roadmap`. | `frontend/src/app/router.tsx`, `frontend/src/app/AppShell.tsx` |
| One `tokens.css` (colors, type scale, spacing, radii) | **Partial.** Color tokens already exist and are used consistently — `frontend/src/index.css` + `tailwind.config.js` define ANCHOR's semantic HSL tokens (`--anchor-good`, `--anchor-critical`, `--anchor-adjacent`, ring fill/track), and dark mode is already pinned (`forcedTheme="dark"` in `App.tsx`, matching the `df43478` "converted into dark mode" commit). No explicit type-scale, spacing, or radii token layer exists yet — that part of G5 is real net-new work. | `frontend/src/index.css`, `frontend/tailwind.config.js`, `frontend/src/App.tsx` |
| SQLite storage (§6.3, §10 risk) | Kept as-is below per V2's own framing — this draft still targets SQLite. **Footnote:** `backend/app/db.py` already supports a Postgres/Supabase connection string via `psycopg` (`requirements.txt`), which `docs/PRD.md` §4.3 states as the actual deploy target. If the team deploys on Postgres/Supabase instead of SQLite, the ephemeral-disk risk in §10 doesn't apply and §6.3's volume/WAL notes are for local dev only. | `backend/app/db.py`, `backend/requirements.txt`, `backend/.env.example`, `docs/PRD.md` §4.3 |
| Prove It / "submit a GitHub link, app evaluates it" | **Already fully built, end to end — not new work.** `backend/app/github.py.fetch_repo()` fetches a public repo read-only (repo tree + capped file bodies, no clone, no execution) → `backend/app/analysis/review.py.review_repo()` calls the model for criteria scores, then `score_review()` computes `total` / `max_total` / `passed` in code, never via the model → `backend/app/routers/submit.py` (`POST /api/submit`) stores the `Submission` and returns `verified_skill_ids`. On the frontend, `frontend/src/features/roadmap/ProveIt.tsx` already renders the project spec, a validated repo-URL input, staged "Fetching… / Reading… / Scoring…" progress, and the full result (score, pass/not-yet badge, per-criterion notes, feedback, verified badges). See §4.6 for the one real gap this leaves for V2. | `backend/app/github.py`, `backend/app/analysis/review.py`, `backend/app/routers/submit.py`, `frontend/src/features/roadmap/ProveIt.tsx` |
| Auth is in scope for V2 | `docs/PRD.md` §2 lists **"Authentication of any kind"** as an explicit V1 non-goal, with `docs/DECISIONS.md` #1 explaining why (Supabase Auth signs ES256 JWTs; custom HS256 verification code would 401 against it; "auth earns zero judge points" for the hackathon). `docs/PRD.md` §16 already anticipates this exact next phase under "v2 (README only — do not build [yet])." V2's design below uses **custom bcrypt + opaque bearer tokens**, not Supabase Auth — it doesn't hit the ES256 problem #1 called out, so it isn't blocked by that decision. This document is the planned continuation PRD.md §16 pointed to, not a violation of it. | `docs/PRD.md` §2, §16; `docs/DECISIONS.md` #1 |

---

## 1. What changes in one paragraph

A student signs up with email + password. After login they land on a **Dashboard** that answers "where am I and what's next" in five seconds. A **left sidebar** navigates between Dashboard, Roadmap, Skills, and Projects. Every tick and every submission is recorded as an **event**, and fit % is **snapshotted over time**, so the Dashboard can show a real progress chart — the thing that makes returning worthwhile. Everything persists under the user's account, on every device they log in from. The dark UI gets a proper design system pass so the four screens look like one product.

~~A fifth screen, `/profile`, and a "Profile" sidebar item~~ — removed 2026-09-04, DECISIONS #85: no
screen shows account info, and there is no self-serve password reset to point to from one either.
Log out is a dedicated icon in the sidebar's account row (avatar + name, non-interactive text next
to it).

---

## 2. Goals & non-goals

### Goals

| # | Goal | Done when |
|---|---|---|
| G1 | Real accounts | Sign up, log in, log out, session survives refresh, works from a second browser |
| G2 | App shell | Left sidebar + top bar on every authenticated screen; active state; user menu with logout |
| G3 | A reason to return | Dashboard shows fit-over-time chart, activity feed, and one "next action" per top role |
| G4 | Progress is a first-class object | Every tick/untick/submission/pass is an event row; fit history is queryable |
| G5 | Looks designed, not defaulted | One token file (colors, type scale, spacing, radii); all five screens use it; zero raw-Tailwind-gray forms left |

### Non-goals (V2 will fail if these creep in)

- **No new model calls, no prompt changes, no re-analysis.** The V1 pipeline is frozen.
- No OAuth / social login, no email verification, no password reset, ~~(Profile shows "contact us to reset" — V3)~~ no account screen at all — removed 2026-09-04, DECISIONS #85
- No teams, sharing, public profiles, notifications, or emails
- No mobile layout (still desktop; the shell may collapse to icons at narrow widths but don't spend time on it)
- No Postgres migration — see §0's footnote: Postgres/Supabase is already available and is `docs/PRD.md`'s stated deploy target; whether V2 stays on SQLite for local dev or deploys straight to the existing Postgres connection is an implementation choice, not new scope either way
- No editing courses/interests after analysis; "Start over" (new analysis) is V3
- No admin panel, no analytics, no theming toggle (dark only)

---

## 3. Information architecture

```
Unauthenticated                    Authenticated (app shell: sidebar, no topbar)
/login                             /            Dashboard
/signup                            /roadmap     Roadmap (V1 two-column, restyled)
                                   /skills      Skill inventory
                                   /projects    Projects & submissions
/onboarding  (post-signup, no sidebar: the V1 Setup + Analyzing flow, restyled as steps)
```

**Sidebar** (fixed left, 232 px): logo · Dashboard · Roadmap · Skills · Projects · account row
(avatar and name, non-interactive) and a log-out icon, at the bottom. Icons + labels, active route
highlighted. No topbar — corrected 2026-09-04, DECISIONS #83; no `/profile` route or nav item —
corrected 2026-09-04, DECISIONS #85 (original draft had both a topbar with a user-chip menu and a
dedicated Profile screen; neither survived direct feedback).
**Routing rule:** unauthenticated hit on any app route → `/login`. Authenticated user with no analysis yet → `/onboarding`. Authenticated with analysis → requested page.

This replaces V1's current router (`frontend/src/app/router.tsx`: `/`, `/setup`, `/analyzing`, `/roadmap` only, no shell beyond a top bar) — see §12.

---

## 4. Screens

### 4.1 `/login` and `/signup`

Centered card on a dark backdrop with some restraint-level brand presence (a big logo lockup + a short in-card subtitle, no separate tagline line). Email, password, one button, link to the other page, inline errors ("Wrong email or password" — never which one). **Corrected (2026-09-04):** signup asks name + email + password only — semester is asked once, during onboarding's Courses step, not here (it belongs to the `Student` record, not the `User` account; asking it twice was the original draft's mistake). **Signup never auto-logs in** — success → `/login` (email prefilled), not `/onboarding` directly; a session is only ever established by an actual login, signup included. On login → `/` (or `/onboarding` if no analysis).

**Claim-on-signup:** if V1's anonymous `student_id` is in `localStorage`, signup attaches that existing student (analysis, ticks, submissions) to the new account and clears the key. Returning V1 users keep their data. Login never claims.

### 4.2 `/onboarding`

The V1 Setup + Analyzing flow, restyled as a real 3-step header (Courses → Interests → Analysis) — **corrected (2026-09-04): Courses and Interests are genuinely separate steps** with a Continue/Back transition between them (state persists across the transition), not one continuous scrolling form with the header only decorating it. The "Your name" field is gone — the account's name (from signup) is reused, never asked twice. Semester is asked once here, at the top of the Courses step. Completes → `/`.

**Course outline selection, redesigned (2026-09-04) on direct feedback that the old single-outline-per-course flow wasn't good enough:** every catalog course's full outline is viewable on demand (a "Read full outline" toggle — not just the 2-line preview), whether or not the course is picked yet. Once picked, a course with more than one authored outline shows an outline picker — **Standard** plus one or more named alternates (e.g. "Applied Data Engineering Track") representing a different instructor's or track's version of the same course code — plus **"Write my own"**, which reveals a free-text box. Whichever is chosen, the resolved outline text is shown back, read-only, so what will be analyzed is never a guess. This costs no new backend surface: picking a named alternate just sets the same `curriculum_override` a hand-typed override already used (`docs/CONTRACT.md`'s `StudentCourseInput`, unchanged) — the catalog gained an optional `curriculum_variants` list per course, nothing else.

### 4.3 `/` Dashboard — the reason V2 exists

Answering, in order top-to-bottom:

1. **Header row — "Where am I":** greeting + three stat cards: *Top role fit* (e.g. "Data Engineer · 71%"), *Skills verified* (n), *Skills self-reported* (n). Each with its delta since last login ("+9 since last visit") computed from events.
2. **Progress chart — "Am I moving":** line chart of fit % over time for the student's top 3 roles (from `fit_snapshot`, §6.2). One glance shows the line going up. Empty state for day-one users: "Your progress will chart here — tick a skill or submit a project."
3. **Next actions — "What now":** one card per top-3 role: the highest-weight unresolved skill or, if a project exists with no passing submission, "Finish *{project title}* — verifies {n} skills". Click-through deep-links to `/roadmap?role=…` with the drawer open.
4. **Recent activity:** last 10 events, humanised ("Verified *SQL Query Optimization* via repo review · 2 d ago", "Marked *Docker Basics* as learned · 5 d ago").

No new computation anywhere here — everything derives from existing tables plus the two new ones in §6.

### 4.4 `/roadmap`

V1's two-column roadmap and drawer, functionally untouched, restyled with the token system: consistent card treatment, refined fit rings, the adjacent section clearly differentiated, the "what moved" strip kept. The drawer still opens in place; `?role=` still works. **Do not rebuild this screen; re-skin it.**

One removal, not a rebuild: V1's "Start over" header button (`clearStudentId()` → `/setup`) is gone — `/setup` isn't a top-level route in V2, and §2 already lists re-analysis ("Start over") as V3 scope, so the button had nowhere left to send a student.

### 4.5 `/skills`

The full skill inventory as a table/list: name · status pill (**Verified** / Learned / Covered / Partial / Missing) · source ("CS301", "repo review", "self-reported") · which roles need it (chips, click → roadmap drawer). Filter tabs by status, text search. Ticking is allowed here too (same optimistic path as the drawer). This is the screen that makes "skills are the source of truth" *visible* — one row, many roles.

### 4.6 `/projects` — includes the repo-submit-and-evaluate requirement

**The submit-a-GitHub-link-and-evaluate-it pipeline is already built and is unchanged by V2.** `POST /api/submit` already fetches a public repo (`app/github.py`) and scores it against the project's criteria (`app/analysis/review.py`), computing `total`/`max_total`/`passed` in code — this is how "prove it" already works today from inside the Roadmap drawer's `ProveIt.tsx`. V2 does not rebuild that; it makes the *history* of that pipeline visible as its own screen, and lets a student manage it across all roles at once instead of one drawer at a time.

One card per generated project: role, title, spec (collapsed), verifies badges, and its submission history (each: repo link, score `total/max`, Passed/Not yet, date, expandable per-criterion notes + feedback). Resubmit from here — reuses the existing `POST /api/submit`. Empty state: "Projects appear when you open Prove It on a role."

**The one real gap:** today's backend only exposes `GET /api/project?role_id=` — a single project for a single role. There is no endpoint that returns *all* of a student's projects and their full submission histories across every role, which this screen needs to render in one view. That's the only new backend surface this screen requires — see `GET /api/projects` in §7.

### 4.7 ~~`/profile`~~ — removed

~~Name, email, account created date, the analysed course list with codes, interests as chips.
Buttons: Log out, Log out everywhere (revokes all sessions). Password reset: "V3 — contact us."~~
The whole screen is gone — removed 2026-09-04, DECISIONS #85, direct feedback ("remove profile
page"). Log out is a dedicated icon in the sidebar's account row (§3); there is no "log out
everywhere" (it was never more than an alias for log out in this mock single-session store, so it
had nowhere else to live once the screen holding it was cut) and no other surface shows account
info.

---

## 5. Authentication

Deliberately simple, honestly scoped, and correct where it counts:

- **Signup:** email (unique, lowercased) + password (min 8 chars) + name + semester. Password hashed with **bcrypt** (passlib). Never stored or logged in plain.
- **Session:** on login/signup the server creates an opaque random token (32 bytes, `secrets.token_urlsafe`), stores its **SHA-256 hash** in a `session` table with a 30-day expiry, and returns the token once. The client keeps it in `localStorage` and sends `Authorization: Bearer <token>` on every request. Logout deletes the session row; "log out everywhere" deletes all of the user's rows.
- **Why bearer token, not cookie:** the SPA and API are on different origins; `SameSite=None` cookie + credentialed CORS is a day of fiddling we don't have. The XSS trade-off is accepted and noted in DECISIONS.md. (V3: httpOnly cookie once domains are unified.)
- **Why not Supabase Auth:** `docs/DECISIONS.md` #1 rejected Supabase Auth for V1 because it signs ES256 JWTs that custom verification code wasn't built to check. This design sidesteps that specific problem by not using Supabase Auth at all — plain bcrypt + opaque bearer tokens, verified against our own `session` table.
- **Server:** every route except `/auth/*` swaps V1's `current_student` for `current_user` — resolves the token hash → `User` row → 401 otherwise. All queries scope by `user_id` exactly as they scoped by student before.
- 401 anywhere → client clears the token → `/login`.
- Naive rate limit on `/auth/login`: 10 failures per email per 15 min (a counter table; no Redis).

---

## 6. Data model changes

### 6.1 New tables

- **`user`** — id, email (unique), password_hash, name, semester, created_at
- **`session`** — id, user_id, token_hash (unique), created_at, expires_at
- **`event`** — id, user_id, type (`tick` | `untick` | `submission` | `pass`), skill_id?, role_id?, submission_id?, created_at. **Append-only; written by the same endpoints that already handle those actions.**
- **`fit_snapshot`** — id, user_id, role_id, fit_percent, created_at. Written server-side after any tick/untick change and after any submission, for **every** role whose fit changed (compare before/after in the request; typically 1–8 rows). This is the chart's data. No backfill; history starts at V2 deploy.

None of these four tables exist today (§0).

### 6.2 Changed

- `student` gains nullable `user_id` FK. Onboarding under an account sets it; claim-on-signup sets it on the old row. All V1 tables stay untouched — they already hang off `student`, and `current_user` resolves user → student in one lookup.
- Login-delta on the Dashboard: `user.last_seen_at`, updated once per session creation; deltas = events since that timestamp.

### 6.3 Storage specifics

`sqlite:///data/anchor.db` on a **persistent volume** (Railway volume / Render disk — without one, every deploy wipes all users). Enable WAL (`PRAGMA journal_mode=WAL`) and `busy_timeout=5000` on connect; SQLModel/SQLAlchemy with `check_same_thread=False`. Single writer is fine at this scale. Nightly copy of the file is the whole backup story.

*Footnote (see §0):* `backend/app/db.py` already branches on `settings.DATABASE_URL` and supports a Postgres/Supabase connection via `psycopg` — the pooler URI is already commented into `backend/.env.example` for deployed use, and `docs/PRD.md` §4.3 names Postgres/Supabase as V1's actual deploy target. If V2 is deployed the same way V1 already is, the WAL/volume notes above only matter for local SQLite dev, and the "SQLite file on ephemeral disk" risk in §10 doesn't apply to the deployed environment at all.

---

## 7. API changes

New, under `/api/auth`: `POST /signup` `{email, password, name, semester, claim_student_id?}` → `{token, user}` · `POST /login` → same · `POST /logout` · `POST /logout_all`.

New for screens: `GET /api/dashboard` → stats + deltas + snapshots (top 3 roles) + next actions + last 10 events, one payload · `GET /api/skills` → the inventory view · `GET /api/projects` → **all of the student's projects with full submission history, across every role** (net-new; today's `GET /api/project?role_id=` only returns one project for one role — see §4.6).

Changed: everything drops `X-Student-Id` for `Authorization: Bearer`. `/progress` and `/submit` additionally write `event` rows and `fit_snapshot` rows in the same transaction. Response shapes otherwise unchanged — **the roadmap screen must not need a single frontend data change.**

---

## 8. Design direction (dark, but designed)

One pass, applied everywhere, driven by a single `tokens.css` / Tailwind theme extension. Colors are already partly there (§0) — this section is the fuller pass:

- **Surfaces:** near-black base (~`#0B0D10`), raised card surface (~`#14171C`), one hover step. Borders at low-alpha white, not gray-700. No pure `#000`, no default Tailwind `gray-800` cards.
- **One accent** (the brand color) used for: active nav, primary buttons, fit rings, the progress line. **Semantic colors** reserved: green = verified only, amber = self-reported, red = missing core. If everything glows, nothing does. (V1 already has this mapping as `--anchor-good` / `--anchor-adjacent` / `--anchor-critical` — extend, don't replace.)
- **Type scale:** one display size (dashboard greeting, fit %), one heading, one body, one caption — a distinctive display face for numbers/headings is the cheapest way to stop looking like a template; body stays a workhorse sans. *Not yet defined anywhere in the codebase — new work.*
- **Numbers are the heroes:** fit percentages and the chart get the size and weight; labels recede.
- **Depth from light, not shadows:** subtle top-edge highlight on cards reads better on dark than drop shadows.
- **States:** every screen gets a real empty state (one sentence + one action) and a skeleton loading state. No spinners on full pages.
- **Motion:** keep V1's translateY re-sort and ring animations; add 150 ms ease on nav/page transitions and nothing else.

Definition of done: put all five screens side by side — same surfaces, same accent logic, same type scale, and the login page could be a screenshot in a landing page.

---

## 9. Two-day plan

**Dev A — auth + data (backend) · Dev B — dashboard data + events/snapshots (backend) then Projects/Skills screens · Dev C — shell, tokens, restyle (frontend)**

### Day 1 — identity, shell, memory

| Who | Work |
|---|---|
| A | `user`/`session` tables, bcrypt, token issue/verify, `/api/auth/*`, `current_user` dependency swapped in everywhere, claim-on-signup, rate-limit counter, storage setup per §6.3 |
| B | `event` + `fit_snapshot` tables; `/progress` and `/submit` write them transactionally; `last_seen_at`; `GET /api/dashboard`, `/api/skills`, `GET /api/projects` (§7) |
| C | `tokens.css` + Tailwind theme (extending the existing color tokens, §0); app shell (sidebar, topbar, user menu, route guards, 401 handling) replacing the current minimal `AppShell`; Login/Signup screens; Onboarding re-skinned as steps |

**Exit criteria:** sign up in browser A, tick a skill, log in from browser B and see it. Old V1 localStorage student claims correctly on signup. Every authenticated request 401s cleanly without a token.

### Day 2 — the screens

| Who | Work |
|---|---|
| C | Dashboard UI: stat cards + deltas, snapshot line chart, next-action cards (deep link opens the drawer), activity feed. Then the roadmap re-skin. |
| B | Skills and Projects screens against Day 1's endpoints; ticking from `/skills` shares the drawer's optimistic path; Projects screen renders `GET /api/projects` history + resubmit via the existing `/api/submit` |
| A | ~~Profile screen, logout-everywhere~~ (screen removed 2026-09-04, DECISIONS #85), empty/skeleton states sweep, deploy, seed a fresh account and click every screen |
| All (last 2 h) | Cross-browser run of the whole loop: signup → onboarding → dashboard → roadmap tick → submit repo → dashboard shows the jump on the chart. **Freeze.** |

**Cut order if Day 2 slips:** activity feed → skills search/filters → next-action cards (keep the chart — it *is* G3) → Projects screen collapses to a list. Never cut auth correctness or the snapshot writes; missing history can't be backfilled later.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Storage on ephemeral disk (SQLite only) → accounts vanish on deploy | Applies only if V2 deploys on SQLite rather than the Postgres/Supabase connection V1's stack already supports (§0, §6.3). If deploying on SQLite: volume mounted Day 1, verified by deploying twice and logging back in. |
| Auth swap breaks V1 endpoints subtly | `current_user` resolves to the same `student` object shape; roadmap frontend needs zero data changes — verify by diffing `/api/roadmap` before/after |
| Restyle turns into a redesign | Tokens first, then re-skin; the roadmap screen is re-skinned, never rebuilt |
| Snapshot writes slow down ticks | 1–8 tiny inserts in the same transaction; measured, not assumed |
| Two days become three | The cut order in §9; auth + shell + chart is the irreducible core |
| `GET /api/projects` (plural) has no precedent to copy | It's a straight join over existing `Project` + `Submission` tables (§4.6) — no new model call, no schema design beyond aggregating what `GET /api/project` and `POST /api/submit` already produce per-role |

---

## 11. Gap checklist

Everything below does not exist yet (§0) and is net-new for V2, grouped by `CLAUDE.md`'s lane ownership so it can be handed directly to whoever picks it up.

**Backend**
- `user`, `session`, `event`, `fit_snapshot` tables
- bcrypt password hashing + token issue/verify
- `current_user` dependency, swapped in everywhere `current_student` is used today
- `POST /api/auth/signup`, `/login`, `/logout`, `/logout_all`
- `GET /api/dashboard`
- `GET /api/skills`
- `GET /api/projects` (plural — the one net-new surface §4.6 needs; `GET /api/project` singular already exists and is unaffected)
- Rate-limit counter table for `/auth/login`
- `event` + `fit_snapshot` writes added to the existing `/progress` and `/submit` transactions

**Frontend**
- Sidebar app shell (no topbar — DECISIONS #83), replacing the current minimal `AppShell.tsx`
- `/login`, `/signup` screens
- `/onboarding` (restyle of existing Setup + Analyzing flow as 3 steps — behavior unchanged)
- `/` Dashboard screen (stat cards, chart, next actions, activity feed)
- `/skills` screen
- `/projects` screen (§4.6)
- ~~`/profile` screen~~ — removed, DECISIONS #85
- Route guards + 401 → `/login` handling
- Type-scale, spacing, and radii tokens alongside the color tokens that already exist

**Shared / unaffected**
- `contracts/`, `backend/app/schemas.py`, `frontend/src/lib/types.ts`: no changes beyond what §6–§7 above define. The roadmap response shape is explicitly unchanged (§7) — the roadmap screen needs zero frontend data changes, only a re-skin (§4.4).
- The Prove It pipeline itself (`github.py`, `review.py`, `ProveIt.tsx`) — already built, untouched by V2 (§0, §4.6).

---

## 12. V3 (README only)

Password reset + email verification · httpOnly cookie sessions on a unified domain · re-analysis preserving ticks/verifications ("my semester ended") · add courses over time · streaks and weekly goals on the dashboard · public shareable profile ("proof of skills") · light mode · mobile layout.
