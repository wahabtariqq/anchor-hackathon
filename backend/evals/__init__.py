"""Prompt evals for the AI lane.

Tests answer "does the code do what it says". Evals answer "is the model's output any good",
which is a different question with a different failure mode: nothing throws, everything
validates, and the roadmap is quietly useless.

Two halves, deliberately separated:

* `graders.py` is pure. Given an output it returns pass/fail checks with the measured number.
  No network, no model, no I/O -- so `tests/test_evals.py` runs the graders against the
  committed fixtures on every `pytest` run, and a grader that silently stopped firing fails
  the suite like anything else.
* `scripts/run_evals.py` is the live half. It calls the real model N times and grades each
  run. It is not a test and never runs under pytest, for the same reason the three
  `run_*_cli.py` scripts are not tests: no test in this repo may make a live call.

The thresholds encode the tuning priorities in the `anchor-analysis` skill, in its order:
skill dedup first, then cross-role reuse, then bridge specificity, then `real_world`.
"""
