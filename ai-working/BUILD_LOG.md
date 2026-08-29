# Build log — Dev B (AI lane)

**Append only. Never edit a past entry.** A log that gets tidied up is not evidence of anything.

If something was done differently from the spec, the entry says `DEVIATION` and explains why.
A deviation that is written down is a decision; a deviation that is not is a bug waiting for
Day 4.

## Entry template

```
## [date time] — [session id] — [what was attempted]
Result: done / partial / failed
Matches spec: yes / DEVIATION
Deviation (if any): what I did differently, why, and which doc section it conflicts with
Files touched:
Tests added/updated:
Open question for the team (if any):
```

---

## 2026-08-27 — Phase 2 + 3 — Scaffold `ai-working/`, add `spec-check` and `test-first` skills

Result: **done**
Matches spec: **DEVIATION** (five, all conscious, one needs a contract PR)

Environment set up first: branch `worktree-dev-b-ai-lane`, `backend/.venv` on Python 3.12.1,
dependencies installed and pinned to exact versions. Baseline test run before any change:
**80 passed, 1 skipped in 1.61s**. The single skip is `test_validation.py`, which
`importorskip`s my still-empty `app.analysis.schema` — that skip flipping to green is S1's
done-check.

### spec-check result

| # | Requirement | Source | Status | Note |
|---|---|---|---|---|
| 1 | Lane dir has README, SESSIONS, BUILD_LOG, `prompts/{analysis,project,review}.md`, `fixtures_notes.md` | kickoff Phase 2 | **deviated** | all six present; directory named `ai-working/`, not `ai/` |
| 2 | Docs and planning only — runtime code stays in `backend/app/analysis/`, do not move it | kickoff Phase 2 | met | no `.py` written; `app/analysis/` untouched, still 8 empty files |
| 3 | SESSIONS covers my work only, each with goal / inputs+source / deliverable / done-check | kickoff Phase 2 | met | S0–S8; other lanes appear only as inputs or consumers |
| 4 | Sessions derived from PRD day plan, at minimum S1–S8 | kickoff Phase 2 | **deviated** | S0 added ahead of S1 |
| 5 | BUILD_LOG uses the given template | kickoff Phase 2 | met | template at top, verbatim |
| 6 | Two skills, each a dir under `.claude/skills/` with frontmatter `name:` + `description:` | kickoff Phase 3 | met | `spec-check/SKILL.md`, `test-first/SKILL.md` |
| 7 | Run spec-check once against the scaffold, append first entry | kickoff Phase 3 | met | this entry |
| 8 | No implementation code before Phase 3; do not begin S1 | kickoff | met | zero `.py` files created or edited |
| 9 | New package / structure noted in DECISIONS | CLAUDE.md Conventions | met | #39–#44 added |
| 10 | Repo layout as documented | TDD §3 | **deviated** | `ai-working/` is not in the documented tree; logged #42 |
| 11 | AI stack is the `anthropic` SDK with structured outputs | PRD §4.3, TDD §4.7 | **deviated** | provider changed to Gemini; **needs contract: PR + team ping** |
| 12 | `.env` carries the model config | TDD §9 | **not met** | still `ANTHROPIC_MODEL=claude-sonnet-4-6`; no `LLM_PROVIDER` / `GEMINI_API_KEY`. Deferred to S2, which owns config |
| 13 | Four lane skills under `.claude/skills/` | TDD §3.3 | **deviated** | six now — `anchor-design` already existed undocumented, plus my two |
| 14 | Fixtures unchanged by this session | CONTRACT §4 | met | no fixture written or edited |
| 15 | Dependencies installed, pinned exactly | user instruction | met | verified green, 80 passed / 1 skipped |

### Deviations

1. **`ai-working/` not `ai/`** — *conscious.* Requested by the repo owner as "a new doc folder
   named ai working". Hyphenated rather than spaced: this checkout already sits under a path
   containing a space, and adding a second one inside the repo breaks tooling that does not
   quote paths. Placement is still top-level next to `backend/` and `frontend/` as specified.
   Trivially renameable.

2. **S0 added ahead of S1** — *conscious.* The kickoff's session list was written against
   Anthropic's token budget. With the provider changed (#39) the analysis call's output ceiling
   is an unverified number, and the analysis payload — 45–55 skills each with a prose sentence,
   plus 8 roles — is the most output-heavy thing in the product. If it does not fit, **the fix
   is architectural, not a retry setting.** S0 measures it in an hour on Day 1 rather than
   discovering it on Day 3. S1–S8 are otherwise unchanged and in the given order.

3. **`ai-working/` is not in TDD §3's tree** — *conscious.* Contains no runtime code and is
   never imported, so it cannot affect behaviour. Logged as #42.

4. **Provider is Gemini, not Anthropic** ⚠ **needs contract: PR + team ping** — *conscious,
   directed by the repo owner* (project is running on free APIs). Rationale, rejected
   alternatives, and measured free-tier numbers in **#39**.

   Mirrors that still say Anthropic and must change together in one `contract:` PR:
   **PRD §4.3** (stack table) · **TDD §4.7** (the whole `client.py` sample, including
   `from anthropic import transform_schema`) · **TDD §9** (`.env` block) ·
   `backend/.env.example`. I edited `CLAUDE.md` invariant #2 immediately rather than wait,
   because it is auto-loaded into every session and would otherwise actively mislead each one.

   **No shape changed.** `AnalysisOut` / `ProjectOut` / `ReviewOut`, the three public
   signatures, and every fixture are untouched, so no other lane's code is affected today. The
   ping is about the docs and `.env.example`, not about broken callers.

5. **Six skills, not four** — *accidental drift, now kept.* I added two; `anchor-design`
   already existed undocumented before I arrived. Rolled into the same doc PR.

### Verification I actually ran

- `pytest -q` → 80 passed, 1 skipped (baseline, before and after — nothing I did touches code)
- `pip list --format=freeze` → the exact versions now pinned in `requirements.txt`
- Gemini structured-output support checked against Google's published docs, not from memory:
  **`pattern` / `minLength` / `maxLength` are unsupported**, `minItems` / `maxItems` /
  `enum` / `required` / nested objects and arrays are supported, and *"very large or deeply
  nested schemas may be rejected"*. The unsupported set is the **same limitation the TDD
  anticipated for Anthropic**, so S1's "re-check the id pattern post-hoc" and S2's schema
  transform both survive the vendor change intact.
- Free tier confirmed at 10 RPM / 250 RPD (2.5 Flash), 250k TPM shared, 1M context.

### Files touched

```
ai-working/README.md                     new
ai-working/SESSIONS.md                   new
ai-working/BUILD_LOG.md                  new
ai-working/fixtures_notes.md             new
ai-working/prompts/analysis.md           new   ← written from scratch, see #43
ai-working/prompts/project.md            new
ai-working/prompts/review.md             new
.claude/skills/spec-check/SKILL.md       new
.claude/skills/test-first/SKILL.md       new
docs/DECISIONS.md                        +6 rows (#39–#44)
CLAUDE.md                                invariant #2 — provider line
backend/requirements.txt                 pinned to exact versions
```

Tests added/updated: **none** — no implementation code this session, by instruction. The
required test list is specified per module in `.claude/skills/test-first/SKILL.md` and is due
alongside S1.

### Open questions for the team

1. **The v3 analysis prompt is gone and nobody has it** (#43). `prompts/analysis.md` is written
   from scratch off CONTRACT §1 and the tuning priorities. **It is new work and needs a real
   read**, not a skim — it is the single highest-leverage artefact in this lane.

2. **Seed postings are at zero with a Day-2-morning deadline.** `backend/seed/postings/`
   contains only its README. PRD §8.6 admits the set *only* if it is in the prompt from the
   start of Day-2 tuning; otherwise it is out permanently. Nobody has started. **Someone has to
   decide tonight.**

3. **`parity_cases.json` has 12 cases; TDD §8 asks ~18** and names *mixed depths*, *core-only*,
   and *supporting-only* as required — all three absent, and the test asserts only `>= 12` so
   nothing fails. Separately, CONTRACT §4 describes the file as a bare list; it is
   `{_comment, cases: […]}`. Ten minutes on Day 2 morning while all three of us are together.

4. **`SkillState`'s four field names** (S6). Salman duplicated the dataclass structurally rather
   than importing my empty module (#33). Nothing enforces agreement — if I name a field
   differently his caller breaks with **no test failure**. Confirm the names before I write it.

5. **TDD §4.7 vs §4.8 disagree on `run_analysis`'s arity**, not just its name — `(student,
   courses)` in one, a pre-built prompt string in the other. #40 settles the name; the arity
   needs the same `contract:` PR.

---

## 2026-08-28 — S1 — `AnalysisOut` schema + validators V1–V6

Result: **done**
Matches spec: **DEVIATION** (two — one cosmetic, one cross-lane and additive)

First implementation code in this lane. `app/analysis/schema.py` written; nothing else in
`app/analysis/` touched — the other seven files are still empty.

Test count went **80 passed / 1 skipped → 98 passed / 0 skipped**. The skip was
`test_validation.py`, which `importorskip`s this module; it now runs its 16 assertions. Those
tests are Salman's, written against the contract before my code existed, which makes them an
honest check rather than a self-graded one.

### spec-check result

Governing sections re-read before writing: **CONTRACT §1, §1.1** · **TDD §4.5**.

| Requirement | Source | Status | Evidence |
|---|---|---|---|
| V1 · 35 ≤ skills ≤ 70 | CONTRACT §1.1 | met | rejects 34 and 71 |
| V1 · skill ids unique | CONTRACT §1.1 | met | `test_rejects_duplicate_skill_ids` |
| V1 · ids match `^[a-z0-9]+(-[a-z0-9]+)*$` | CONTRACT §1.1 | met | `test_rejects_a_non_kebab_case_skill_id` |
| V2 · exactly 8 roles | CONTRACT §1.1 | met | rejects 7 and 9 |
| V2 · 5 ≤ core roles ≤ 6 | CONTRACT §1.1 | met | rejects 4 and 7 |
| V3 · role skill_ids exist in `skills[]` | CONTRACT §1.1 | met | `test_rejects_a_role_referencing_an_unknown_skill` |
| V4 · coverage skill_ids exist in `skills[]` | CONTRACT §1.1 | met | `test_rejects_coverage_referencing_an_unknown_skill` |
| V5 · no skill repeated in one role | CONTRACT §1.1 | met | `test_rejects_a_skill_repeated_within_one_role` |
| V5 · 8 ≤ skills per role ≤ 16 | CONTRACT §1.1 | met | rejects 7 and 17 |
| V6 · adjacent roles have non-empty bridge | CONTRACT §1.1 | met | rejects `""` and `"   "` |
| Soft rules warn + skip, never raise | CONTRACT §1.1 | met | **2 tests added** — see deviation 2 |
| No `Optional`, no unions; `bridge` is plain `str` | TDD §4.5, DECISIONS #5 | met | no `\| None` in the file |
| Length bounds in validators, not `Field(min_length=…)` | TDD §4.5 | met | module-level constants |
| `pattern` on the field, re-checked post-hoc | TDD §4.5 | met | provider strips it from the sent schema |
| Module imports nothing provider-specific | DECISIONS #39 | met | imports are `typing` + `pydantic` only |

### Deviations

1. **ASCII hyphens in error messages** (`want 35-70`) where TDD §4.5 uses en-dashes
   (`want 35–70`) — *conscious, cosmetic.* Keeps the source pure ASCII so nothing depends on
   console codepage on Windows. No test asserts on the dash; messages are otherwise identical.

2. **Added two tests to `backend/tests/test_validation.py`** — *conscious.* ⚠ **cross-lane,
   needs a ping — but not a contract PR.**

   `backend/tests/` is Salman's lane (`CLAUDE.md` ownership map). The edit is **purely
   additive** — no existing test changed — and the file is explicitly scaffolded for my lane
   ("app/analysis/schema.py is Dev B's lane"). I added it rather than leave the gap because
   CONTRACT §1.1's two soft rules had **no coverage at all**: nothing asserted that an unknown
   `course_code` or a duplicate `(skill, course)` pair is *tolerated*. Hardening either into a
   hard failure is a one-line change that would turn a shrug into a 502 during a live demo, and
   the whole suite would still be green. **No contract shape changed**, so this is a chat ping,
   not a `contract:` PR.

### Lane-boundary check

`AnalysisOut` implements CONTRACT §1 exactly as already agreed — no field added, renamed, or
retyped, and no fixture touched. Salman's `persistence.py` consumes `parsed.skills`,
`parsed.roles`, `parsed.coverage` and every attribute it reads exists with the expected type.
**Nothing downstream needs to change.**

### Files touched

```
backend/app/analysis/schema.py        new (~150 lines)
backend/tests/test_validation.py      +2 tests (additive; Salman's lane — ping him)
```

Tests added/updated: **2 added** — `test_tolerates_a_coverage_row_with_an_unknown_course_code`,
`test_tolerates_a_duplicate_skill_course_coverage_pair`. The other 16 in that file were already
written and started running for the first time.

### Open question for the team

None new. The five from the scaffold entry still stand — the analysis prompt needs a real read,
seed postings are still at zero, and `parity_cases.json` is still three cases short of what
TDD §8 names.

**Next: S0** (measure the free-tier output ceiling — needs `GEMINI_API_KEY`) then **S2**.
S1 needed no key; everything after S0 does.

---

## 2026-08-29 — S0 — Provider spike: can the free tier carry the analysis call?

Result: **done**
Matches spec: **DEVIATION** (three — the docs' provider config was unusable as written)

**The headline: the risk S0 existed to test is closed.** The analysis call fits with enormous
room, and the prompt passed every validator on its first real run.

### Measured

| | |
|---|---|
| Model | `gemini-3.6-flash` |
| **Output ceiling** | **65,536 tokens** — 4× the 16k the docs budgeted |
| Output actually used | **7,497 tokens** (+1,665 thinking) — ~11% of ceiling |
| `finishReason` | `STOP` — not truncated, nowhere near it |
| Latency | **55.4 s** (prompt 2,389 tokens in) |
| Payload | 27,410 chars of JSON |

`ANALYSIS_MAX_TOKENS=16000` / `RETRY=24000` are **comfortable, not tight**. The 24k retry
rung will realistically never fire for truncation. The contingency plans in this session's
S0 notes — trim the payload, split the call in two — are **not needed**. Nothing architectural
has to change.

### Output quality — first run, no tuning

Validated clean against `AnalysisOut`: **all of V1–V6 passed**.

- **48 skills** (prompt asks 45–55) · **8 roles**, 5 core / 3 adjacent · 33 coverage rows
- Coverage codes exactly `CS201, CS301, CS401, CS402` — the demo student's four, nothing invented
- Role skill counts `[12,12,11,11,11,10,11,11]` — all inside 10–14
- **Cross-role reuse: 22 of 45 used skills appear in more than one role (49%), max 4.**
  This is the property the demo's closing beat depends on — one tick moving several cards.
- **Zero near-duplicate skills** by id-similarity and full-token-overlap. Risk-register #1,
  clean on the first attempt.
- **Zero vague `real_world` sentences** against the reject-list ("used in many jobs" etc.)
- Adjacent bridges name specific courses in second person, as the prompt demands — e.g.
  *"Your DBMS coursework in query tuning combined with your interest in UI/UX design converges
  here…"*, *"Your Machine Learning class (CS401) and Web Development skills (CS402)…"*

Minor: 3 of 48 skills are referenced by no role (`dynamic-programming`,
`microservices-architecture`, `state-machine-design`). Harmless — they still appear under
"covered by your courses" — but worth a line in S4 if it persists.

### Deviations

1. **`gemini-2.5-flash` is unusable — the model in our own config could not be called.**
   `generateContent` returns `404: "This model models/gemini-2.5-flash is no longer available
   to new users. Please update your code to use models/gemini-3.6-flash"`. It still *appears*
   in `models.list`, which makes this fail confusingly rather than obviously. Pinned
   `gemini-3.6-flash` (DECISIONS #46). Also rejected `gemini-flash-latest`: an auto-updating
   alias can change between rehearsal and the demo slot, and it 503'd during this session
   anyway. `gemini-3.7-flash` timed out under load.

2. **The `google-genai` SDK does not work with this key; using raw REST instead**
   (DECISIONS #45). The SDK returns `403 PERMISSION_DENIED` on both `models.list()` and
   `generate_content()`, while the *same key* succeeds against
   `generativelanguage.googleapis.com` with an `x-goog-api-key` header — so this is the SDK's
   auth path, not the credential. Dropped `google-genai` from `requirements.txt`; `httpx` was
   already pinned, so **the provider now costs zero extra dependencies**. This also keeps
   `finishReason` and `usageMetadata` directly accessible, which the S2 retry policy needs.

3. **Schema-transform bug found and fixed before it could reach `client.py`** (DECISIONS #47).
   Stripping JSON-Schema annotation keywords by name also deleted the **field** named `title`
   from `RoleOut`, leaving it listed in `required` — Gemini rejected it with
   `400 ... required[1]: property is not defined`. Keywords must be stripped at schema level
   only; keys inside `properties` are field names and are always preserved. S2 inherits this
   as a required test case.

### Verified working transform

Confirmed Gemini's `responseSchema` needs `$ref`/`$defs` **inlined**, and rejects `pattern`,
`minLength`, `maxLength`, `additionalProperties`. `const` must be rewritten as a
single-item `enum` (Pydantic emits `const` for single-value `Literal`s). With those handled,
the full nested `AnalysisOut` schema — 4 nested models, 2 arrays of objects — was accepted
without complaint. No sign of the *"very large or deeply nested schemas may be rejected"*
limit at our size.

### Files touched

```
backend/.env                  local only, gitignored — key + GEMINI_MODEL=gemini-3.6-flash
backend/requirements.txt      google-genai dropped; comment explains REST-over-SDK
docs/DECISIONS.md             #39 corrected, #45-#47 added, Day-1 latency filled in (55.4 s)
ai-working/SESSIONS.md        status board
```

No runtime code written — the spike ran as a throwaway script outside the repo. **S2 still
owns `client.py`**, and now has measured numbers and three concrete gotchas to build against.

Tests added/updated: none. S2's mocked retry/transform tests are where this becomes permanent —
including the `properties` case from deviation 3.

### Open question for the team

**Free-tier reliability is now a demo risk, and it is not hypothetical.** Two of the models I
tried returned 503 "high demand" *during this session*. `DEMO_MODE` with a committed
`demo_analysis.json` stops being a nicety and becomes the thing the pitch rests on — which is
why S5 was moved earlier. PRD §12.1's promise that *judges can try their own inputs live* is
the part most likely to fail on the day; someone should decide whether we still make that offer.

Also unchanged from before: the analysis prompt still needs a human read, seed postings are
still at zero, and `parity_cases.json` is still three cases short.
