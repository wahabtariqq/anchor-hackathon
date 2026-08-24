# Fixtures

| File | Written by | When | Read by |
|---|---|---|---|
| `demo_analysis.json` | Dev B, `scripts/run_analysis_cli.py --demo --save` | Day 1 (first valid run), refreshed Day 2 | `DEMO_MODE`, persistence tests |
| `roadmap_response.json` | Dev C by hand on Day 1 (shape from `docs/CONTRACT.md` §3); Dev A via `scripts/dump_roadmap.py` on Day 2 | | frontend with `VITE_USE_FIXTURE=true` |
| `courses.json` | Dev A, copy of `GET /courses` | Day 1 | frontend fixture mode |
| `parity_cases.json` | all three | Day 2 morning | `test_parity.py`, `scoring.test.ts` |

Never edit a fixture to make a test pass. Fix the producer.
