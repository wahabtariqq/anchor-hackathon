"""Grade the three prompts against the live model.

    python scripts/run_evals.py                      # all three suites, 1 run each
    python scripts/run_evals.py --suite analysis --runs 3
    python scripts/run_evals.py --suite review       # calibration + injection
    python scripts/run_evals.py --offline            # grade the committed fixtures, no API

This is not a test and never runs under pytest -- no test in this repo may make a live call.
`tests/test_evals.py` covers the graders themselves, offline, against the committed fixtures.

**Why evals and not more tests.** The tests answer "does the code do what it says"; they pass
whether the model's output is excellent or useless, because everything validates either way.
These answer "is the output any good", and every check reports the number it measured, so a
prompt change can be argued about with evidence rather than taste.

Thresholds follow the tuning order in the `anchor-analysis` skill: dedup, cross-role reuse,
bridge specificity, then `real_world`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analysis import AnalysisFailed, generate_project, review_repo, run_analysis  # noqa: E402
from app.analysis.project import ProjectOut                                           # noqa: E402
from app.analysis.review import ReviewOut, score_review                               # noqa: E402
from app.analysis.schema import AnalysisOut                                           # noqa: E402
from app.models import Student, StudentCourse                                         # noqa: E402
from evals import bundles, graders                                                    # noqa: E402
from seed.courses import CATALOG                                                      # noqa: E402

FIXTURES = ROOT / "contracts" / "fixtures"

DEMO_COURSES = {"cs201": "past", "cs301": "past", "cs401": "current", "cs402": "current"}
DEMO_INTERESTS = ["Artificial Intelligence", "Databases", "UI/UX Design"]


def demo_inputs():
    by_id = {c["id"]: c for c in CATALOG}
    student = Student(name="EvalStudent", semester=4, interests=DEMO_INTERESTS)
    courses = [
        StudentCourse(
            student_id=student.id, course_id=cid, code=by_id[cid]["code"],
            name=by_id[cid]["name"], curriculum_text=by_id[cid]["curriculum_text"],
            semester_tag=tag,
        )
        for cid, tag in DEMO_COURSES.items()
    ]
    return student, courses


def report(title: str, checks: list[graders.Check]) -> tuple[int, int]:
    passed, total = graders.summarise(checks)
    print(f"\n{title}  ({passed}/{total})")
    for check in checks:
        print(check.line())
    return passed, total


def skill_states_for(analysis: AnalysisOut, role):
    """Same derivation as run_project_cli.py: best depth wins, then a state label."""
    from app.analysis.project import SkillState

    names = {s.id: s.name for s in analysis.skills}
    best: dict[str, str] = {}
    for cov in analysis.coverage:
        if best.get(cov.skill_id) != "full":
            best[cov.skill_id] = cov.depth
    return [
        SkillState(
            slug=rs.skill_id, name=names.get(rs.skill_id, rs.skill_id), weight=rs.weight,
            state=f"covered:{best[rs.skill_id]}" if rs.skill_id in best else "missing",
        )
        for rs in role.skills
    ]


def eval_analysis(runs: int, offline: bool) -> tuple[int, int]:
    codes = [c["code"] for c in CATALOG if c["id"] in DEMO_COURSES]
    passed = total = 0

    for i in range(1, runs + 1):
        if offline:
            parsed = AnalysisOut.model_validate_json(
                (FIXTURES / "demo_analysis.json").read_text(encoding="utf-8")
            )
            label = "analysis (committed fixture)"
        else:
            student, courses = demo_inputs()
            started = time.time()
            parsed, _ = run_analysis(student, courses)
            label = f"analysis run {i}/{runs}  ({time.time() - started:.1f}s)"

        checks = graders.grade_analysis(parsed, course_codes=codes, interests=DEMO_INTERESTS)
        checks += graders.grade_analysis_structure(parsed, course_codes=codes)
        p, t = report(label, checks)
        passed, total = passed + p, total + t
    return passed, total


def eval_project(runs: int, offline: bool) -> tuple[int, int]:
    analysis = AnalysisOut.model_validate_json(
        (FIXTURES / "demo_analysis.json").read_text(encoding="utf-8")
    )
    role = min(analysis.roles, key=lambda r: r.rank)
    states = skill_states_for(analysis, role)
    passed = total = 0

    for i in range(1, runs + 1):
        if offline:
            project = ProjectOut.model_validate_json(
                (FIXTURES / "demo_project.json").read_text(encoding="utf-8")
            )
            label = "project (committed fixture)"
        else:
            started = time.time()
            project, _ = generate_project(role.title, role.one_liner, states)
            label = f"project run {i}/{runs}  ({time.time() - started:.1f}s)"

        p, t = report(label, graders.grade_project(project, states))
        passed, total = passed + p, total + t
    return passed, total


def eval_review(offline: bool) -> tuple[int, int]:
    """Calibration and injection resistance -- both need two runs to mean anything."""
    project = ProjectOut.model_validate_json(
        (FIXTURES / "demo_project.json").read_text(encoding="utf-8")
    )
    passed = total = 0

    if offline:
        stored = json.loads((FIXTURES / "demo_review.json").read_text(encoding="utf-8"))
        review = ReviewOut.model_validate(
            {"criteria_scores": stored["criteria_scores"], "feedback": stored["feedback"]}
        )
        t, m, _ = score_review(review)
        checks = graders.grade_review(review, t, m, criteria=project.criteria)
        p, n = report("review (committed fixture)", checks)
        print("\n  calibration and injection need live runs; use --suite review without --offline")
        return p, n

    strong = bundles.load("strong_repo")
    weak = bundles.load("weak_repo")

    started = time.time()
    s_review, s_total, s_max, _ = review_repo(project, strong)
    p, n = report(f"review: strong repo  ({time.time() - started:.1f}s)",
                  graders.grade_review(s_review, s_total, s_max, criteria=project.criteria,
                                       bundle=strong))
    passed, total = passed + p, total + n

    started = time.time()
    w_review, w_total, w_max, _ = review_repo(project, weak)
    p, n = report(f"review: weak repo  ({time.time() - started:.1f}s)",
                  graders.grade_review(w_review, w_total, w_max, criteria=project.criteria,
                                       bundle=weak))
    passed, total = passed + p, total + n

    p, n = report("review: calibration",
                  graders.grade_calibration((s_total, s_max), (w_total, w_max)))
    passed, total = passed + p, total + n

    # Injected into the WEAK repo on purpose: the strong one already scores maximum, so an
    # unchanged score there would be arithmetic rather than evidence.
    started = time.time()
    _, i_total, i_max, _ = review_repo(project, bundles.injected(weak))
    p, n = report(f"review: injection  ({time.time() - started:.1f}s)",
                  graders.grade_injection((w_total, w_max), (i_total, i_max)))
    return passed + p, total + n


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade the ANCHOR prompts against the live model.")
    ap.add_argument("--suite", choices=["analysis", "project", "review", "all"], default="all")
    ap.add_argument("--runs", type=int, default=1, help="repeat the analysis/project suites N times")
    ap.add_argument("--offline", action="store_true",
                    help="grade the committed fixtures instead of calling the model")
    args = ap.parse_args()

    if args.offline:
        print("ANCHOR prompt evals  --  committed fixtures, no API")
    else:
        # Evals spend the same free-tier budget the demo runs on: 10 requests/minute and
        # 250/day. A full --runs 3 sweep is 9 calls, and repeated sweeps really do exhaust it
        # -- this harness hit 503s and then 429 RESOURCE_EXHAUSTED the day it was written.
        # Run --offline while iterating on graders; spend live calls deliberately.
        calls = (args.runs if args.suite in ("analysis", "all") else 0)             + (args.runs if args.suite in ("project", "all") else 0)             + (3 if args.suite in ("review", "all") else 0)
        print(f"ANCHOR prompt evals  --  LIVE: about {calls} model call(s)")
        print("  free tier is 10/min and 250/day, shared with the demo. --offline costs nothing.")

    passed = total = 0
    try:
        if args.suite in ("analysis", "all"):
            p, t = eval_analysis(args.runs, args.offline); passed, total = passed + p, total + t
        if args.suite in ("project", "all"):
            p, t = eval_project(args.runs, args.offline); passed, total = passed + p, total + t
        if args.suite in ("review", "all"):
            p, t = eval_review(args.offline); passed, total = passed + p, total + t
    except AnalysisFailed as exc:
        print(f"\nFAILED: {exc}")
        return 1

    print(f"\n{'=' * 60}\nTOTAL  {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
