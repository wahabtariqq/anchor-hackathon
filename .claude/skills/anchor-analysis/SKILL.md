---
name: anchor-analysis
description: How to build, run, and tune the ANCHOR AI pipeline in backend/app/analysis/ — the single Claude call that turns courses + interests into a skills / coverage / roles JSON via Anthropic structured outputs, the Pydantic validators, the retry and truncation logic, the demo cache, and the prompt. Use this for any task under backend/app/analysis/, for prompt tuning, for skill-deduplication or adjacent-role quality, for anything mentioning Anthropic, Claude, structured outputs, max_tokens, the analysis fixture, or DEMO_MODE.
---

# ANCHOR analysis pipeline

Design reference: `docs/TDD.md` §4.5, §4.7, §4.8. Output shape and validation rules:
`docs/CONTRACT.md` §1. This lane owns `backend/app/analysis/` and nothing else.

## Public surface — the only thing other lanes import

```python
from app.analysis import run_analysis
parsed, raw = run_analysis(student, courses)   # -> (AnalysisOut, str); raises AnalysisFailed
```

Keep this signature stable. Dev A's router depends on it. Everything else in the package is private.

## Module map

| File | Contains |
|---|---|
| `__init__.py` | re-exports `run_analysis`, `AnalysisFailed`, `load_demo` |
| `schema.py` | `AnalysisOut` + validators V1–V6 from the contract |
| `prompt.py` | `build_prompt(student, courses) -> str` — the PRD §8.3 text |
| `client.py` | the Anthropic call: structured outputs, retry, truncation handling |
| `demo.py` | `load_demo() -> (AnalysisOut, str)` from `contracts/fixtures/demo_analysis.json` |
| `export_schema.py` | writes `contracts/analysis.schema.json` |

## How the call must be made

- `client.messages.create(...)` with
  `output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}}` where
  `OUTPUT_SCHEMA = transform_schema(AnalysisOut.model_json_schema())`.
- Parse with `AnalysisOut.model_validate_json(text)` — this runs the custom validators and
  re-checks the `pattern` the SDK stripped from the sent schema.
- Check `resp.stop_reason == "max_tokens"` before parsing. If truncated, retry with
  `ANALYSIS_RETRY_MAX_TOKENS`.
- Retry once total on validation failure. Then raise `AnalysisFailed`.
- **No prefill** (unsupported on Claude 4.6+, incompatible with structured outputs).
  **No fence-stripping regex.** Both are dead code from v2 — do not reintroduce them.
- All fields required, no `Optional`, no `| None` in `schema.py`. Union types blow up the
  grammar. `bridge` is `str` and `""` for core roles.

## Iterate without the server or the DB

```bash
python scripts/run_analysis_cli.py --demo                 # demo student, prints validation result + latency
python scripts/run_analysis_cli.py --demo --save          # also writes contracts/fixtures/demo_analysis.json
python scripts/run_analysis_cli.py --courses cs201,cs301 --interests "Databases,Security"
```

The CLI builds a fake `Student` and `StudentCourse` list from `seed/courses.py`, calls
`run_analysis`, prints wall-clock seconds and `stop_reason`, and dumps validation errors.
Write the measured latency into `docs/DECISIONS.md` on Day 1 — the timeout strategy depends on it.

## Prompt tuning priorities (in order)

1. **Skill dedup.** Open the fixture, sort skill names, look for near-duplicates
   (`sql`, `sql-querying`, `relational-databases`). If any, strengthen the CRITICAL
   paragraph with the exact pair you saw. This is the #1 risk in the risk register.
2. **Cross-role reuse.** Count how many roles share each skill. If most skills appear in
   one role only, the demo tick won't move multiple cards. Ask for more shared foundations.
3. **Adjacent-role interestingness.** Bridge lines must name the specific course or
   interest, second person ("Your UI/UX interest and DBMS coursework converge here…").
4. **`real_world` specificity.** Concrete number, situation, or consequence. Reject "used in many jobs".

Change one thing per run. Save the fixture after every good run; the previous one is in git.

## Demo mode

`load_demo()` reads the committed fixture and sleeps 6 s so the Analyzing screen reads as
real work. `analyze.py` selects it when `DEMO_MODE=true` **and** `student.name` matches
`DEMO_STUDENT_NAME` (case-insensitive). Everyone else gets a live call. The fixture's
coverage codes must be CS201/CS301/CS401/CS402 — the demo student's courses.

## Definition of done for this lane

- `run_analysis_cli.py --demo` passes validation on 3 consecutive runs.
- Fixture committed; `python -m app.analysis.export_schema` run.
- Latency recorded in `docs/DECISIONS.md`.
- `pytest tests/test_validation.py` green: it must reject unknown skill_id, duplicate ids,
  a repeated skill in one role, adjacent without bridge, 7 or 9 roles, 4 or 7 core roles.
