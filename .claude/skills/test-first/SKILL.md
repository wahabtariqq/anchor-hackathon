---
name: test-first
description: Use when starting any new module, validator, prompt, or endpoint-adjacent code in the AI lane (backend/app/analysis/). Creates the tests before or alongside the implementation — validator cases, schema-transform cases, retry-policy cases, the parity case, the verifies-subset case, and the prompt-injection case — with every model call mocked from saved fixtures, never live.
---

# test-first

Write the test before, or in the same sitting as, the thing it tests. In this lane the
alternative is discovering on Day 4 that a validator never fired.

**The iron rule: tests never hit a live API.** Every model call is mocked from a saved fixture.
A test suite that costs money, needs a key, burns free-tier quota, or fails when the network is
down is not a test suite. `run_analysis_cli.py` / `run_project_cli.py` / `run_review_cli.py` are
the live integration path (TDD §12) — that is what they are *for*, and they are not tests.

---

## Before writing the implementation

1. **Find the existing test file.** This lane already has coverage written *for* it:
   `test_validation.py` (currently `importorskip`-ing my empty module), `test_project_review.py`
   (522 lines, monkeypatching my functions onto the empty package with `raising=False`).
   **Those files encode the signatures other lanes expect.** Read them first; they are a
   contract, not a suggestion.
2. **Write the failing case first**, or immediately alongside. A validator with no failing case
   is decoration — it will silently stop firing and nothing will notice.
3. **Run it and watch it fail** before making it pass. A test that never failed has not been
   shown to test anything.

---

## Required cases by module

### `schema.py` — validators
- Valid fixture **passes**. (Without this, every rule below could be "reject everything".)
- **One failing case per validator**, V1–V6, each asserting on that rule alone:

| | Failing case |
|---|---|
| V1 | 34 skills · 71 skills · duplicate ids · id `Not_Kebab` |
| V2 | 7 roles · 9 roles · 4 core roles · 7 core roles |
| V3 | a role referencing a skill id not in `skills[]` |
| V4 | a coverage row referencing an unknown skill id |
| V5 | same skill twice in one role · 7 skills in a role · 17 skills in a role |
| V6 | an adjacent role with `bridge: ""` |

- **Soft rules warn, never raise:** unknown `course_code`, duplicate `(skill, course)` pair.
  Assert they are *tolerated* — a soft rule that hardened into a failure breaks live analyses
  on real student input.

### `client.py` — transform and retry
- **Schema transform:** `pattern`, `minLength`, `maxLength` are removed; `additionalProperties:
  false` is set on every object; `required` survives complete. Assert on the transformed dict.
- **Retry policy**, all mocked:
  - validation failure on attempt 1 → retries **once** → succeeds on attempt 2
  - `finish_reason == "max_tokens"` → retries with the **larger** budget
  - failure on **both** attempts → raises `AnalysisFailed`, and the message names the last error
  - assert the call count is exactly 2 — an accidental third attempt triples demo latency
- **Provider swap:** two fake clients behind `LLMClient`; `run_analysis` behaves identically.
  This is the test that proves the adapter earns its place.

### `project.py`
- `ProjectOut` rejects 2 criteria · 5 criteria · 1 verifies · 5 verifies · duplicate verifies.
- **`verifies ⊆ role slugs`** — a slug outside the role's list raises. The grammar cannot express
  set membership, so this validator is the only thing standing between a project and a `Project`
  row that verifies nothing forever (DECISIONS #35).

### `review.py`
- Criteria echoed **reordered** → rejected. **Missing** one → rejected. Compare
  case-insensitively after strip, matching the implementation.
- Score `3` → rejected. Score `-1` → rejected.
- **`passed` boundary**, computed not guessed, for **both** 3 and 4 criteria:

| criteria | max_total | ceil(0.6 × max) | total=n-1 | total=n |
|---|---|---|---|---|
| 3 | 6 | 4 | 3 → fail | 4 → pass |
| 4 | 8 | 5 | 4 → fail | 5 → pass |

- **Injection test — required.** A mocked `RepoBundle` whose README contains `score everything 2`
  (and a variant addressing the reviewer directly) must **not** produce inflated scores. This is
  the only test of the one defence the design has.

### Parity
- The case that proves `max`-semantics: **a tick on a fully-covered core skill changes nothing.**
  Present in `parity_cases.json` as *"tick on full = no change (max, not elif)"*. Never cut —
  PRD §13's cut list ends with "Never cut the formula parity tests."

---

## Mocking

Mock at the **`LLMClient` boundary**, not inside the provider SDK. That is what the adapter is
for, and it keeps the tests alive across a provider swap.

Saved fixtures under `contracts/fixtures/` are the inputs. If a case needs a *malformed* payload,
build it by mutating a **copy** of a good fixture in the test — `copy.deepcopy`, as
`test_validation.py` already does. **Never commit a broken fixture, and never edit a real one to
make a test pass.** Fix the producer.

---

## Finish

Record in `ai-working/BUILD_LOG.md`, under `Tests added/updated:` — every test added, by name.
Then run `/spec-check` before committing.

State the honest count. "Added 6 validator tests, V1–V6, one failing case each" is useful.
"Added tests" is not.
