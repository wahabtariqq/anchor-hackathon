"""Generate a project spec for one role, with no server and no database.

    python scripts/run_project_cli.py                       # the demo student's top-ranked role
    python scripts/run_project_cli.py --role data-engineer
    python scripts/run_project_cli.py --runs 3
    python scripts/run_project_cli.py --save                # writes contracts/fixtures/demo_project.json

The live integration path for S6 (TDD §12). The test suite never calls the API; this does.

Skill states are derived from `contracts/fixtures/demo_analysis.json` the same way Salman's
`skill_states_for_role` derives them from the database: best coverage depth per skill, then
`covered:full` / `covered:partial` / `missing`. A fresh student has no ticks and nothing
verified, so those two states cannot occur here -- which is honest, because that is exactly the
state the demo student is in when the pitch opens the Prove It panel.

--save writes the fixture DEMO_MODE serves. Only ever save a run you have actually read, and
regenerate it together with the repo and demo_review.json or not at all (PRD §14).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analysis import AnalysisFailed, generate_project                # noqa: E402
from app.analysis.project import ProjectOut, SkillState                  # noqa: E402

ANALYSIS_FIXTURE = ROOT / "contracts" / "fixtures" / "demo_analysis.json"
FIXTURE = ROOT / "contracts" / "fixtures" / "demo_project.json"

# A criterion the reviewer cannot check by READING is unscoreable, and the review call has no
# way to say so -- it just guesses. project.md rejects these by example; this catches the ones
# that get through. Substrings, matched case-insensitively.
UNSCOREABLE = (
    "tests pass", "test suite passes", "works correctly", "runs without", "is efficient",
    "performs well", "no bugs", "successfully runs", "executes", "compiles",
)

# Under the v4 fit formula, proof on a skill the student already has full coverage of is worth
# exactly zero percentage points -- `max(1.0, ...)` is still 1.0 (CONTRACT §2).
WORTHLESS_STATES = ("covered:full", "verified")


def load_analysis() -> dict:
    if not ANALYSIS_FIXTURE.exists():
        sys.exit(f"missing {ANALYSIS_FIXTURE} -- run run_analysis_cli.py --demo --save first")
    data = json.loads(ANALYSIS_FIXTURE.read_text(encoding="utf-8"))
    if "_todo" in data:
        sys.exit(f"{ANALYSIS_FIXTURE} is still the placeholder")
    return data


def pick_role(analysis: dict, wanted: str) -> dict:
    """`--role` by id, else the rank-1 role.

    Rank 1 is not an arbitrary default: `routers/project.py:_demo_applies` serves the demo
    project only for the student's **top-ranked** role, so any other role's spec would never be
    the one DEMO_MODE loads.
    """
    roles = sorted(analysis["roles"], key=lambda r: r["rank"])
    if not wanted:
        return roles[0]
    for role in roles:
        if role["id"] == wanted:
            return role
    sys.exit(f"unknown role {wanted!r}\navailable: {', '.join(r['id'] for r in roles)}")


def skill_states(analysis: dict, role: dict) -> list[SkillState]:
    """Mirror of Salman's `skill_states_for_role`, over the fixture instead of the DB.

    Best depth wins across courses (full > partial), matching CONTRACT §2's note that
    coverage_depth is collapsed once when the roadmap payload is built.
    """
    names = {s["id"]: s["name"] for s in analysis["skills"]}
    best: dict[str, str] = {}
    for cov in analysis["coverage"]:
        if best.get(cov["skill_id"]) != "full":
            best[cov["skill_id"]] = cov["depth"]

    states = []
    for member in role["skills"]:
        depth = best.get(member["skill_id"])
        state = f"covered:{depth}" if depth else "missing"
        states.append(
            SkillState(
                slug=member["skill_id"],
                name=names.get(member["skill_id"], member["skill_id"]),
                weight=member["weight"],
                state=state,
            )
        )
    return states


def report(project: ProjectOut, states: list[SkillState], elapsed: float, raw: str) -> list[str]:
    """Print what a human has to read before saving this. Returns warnings; empty means clean."""
    warnings: list[str] = []
    by_slug = {s.slug: s for s in states}

    print(f"  latency        {elapsed:.1f}s   ({len(raw)} chars)")
    print(f"  title          {project.title}")
    print(f"  spec           {len(project.spec.split())} words")
    for line in project.spec.splitlines():
        print(f"                 {line}")

    print(f"  criteria       {len(project.criteria)}")
    for i, criterion in enumerate(project.criteria, 1):
        print(f"    {i}. {criterion}")
        hit = [phrase for phrase in UNSCOREABLE if phrase in criterion.lower()]
        if hit:
            warnings.append(f"criterion {i} may not be checkable by reading: {hit}")

    print(f"  verifies       {len(project.verifies)}")
    for slug in project.verifies:
        state = by_slug[slug].state if slug in by_slug else "NOT IN THIS ROLE"
        print(f"    {slug}  [{state}]")

    # The thing HANDOFF §6 says to watch for: a project that moves the fit percentage by zero.
    dead = [s for s in project.verifies if by_slug.get(s) and by_slug[s].state in WORTHLESS_STATES]
    if dead:
        warnings.append(
            f"verifies {dead} are already covered:full -- proof on them moves the fit % by 0"
        )
    if len(dead) == len(project.verifies):
        warnings.append("EVERY verified skill is already covered -- this project moves nothing")

    gaps = [s.slug for s in states if s.state == "missing"]
    print(f"  role gaps      {len(gaps)}  {gaps[:6]}")
    if gaps and not (set(project.verifies) & set(gaps)):
        warnings.append(f"none of the role's {len(gaps)} missing skills are verified")
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate an ANCHOR project spec, no DB, no server.")
    ap.add_argument("--role", default="", help="role id from demo_analysis.json; default rank 1")
    ap.add_argument("--runs", type=int, default=1, help="repeat N times")
    ap.add_argument("--save", action="store_true", help="write contracts/fixtures/demo_project.json")
    args = ap.parse_args()

    analysis = load_analysis()
    role = pick_role(analysis, args.role)
    states = skill_states(analysis, role)

    print(f"role       {role['id']}  (rank {role['rank']}, {role['proximity']})")
    print(f"title      {role['title']}")
    print(f"one_liner  {role['one_liner']}")
    print(f"skills     {len(states)}  " + ", ".join(f"{s.slug}[{s.state}]" for s in states[:4]) + " ...")

    clean = 0
    last_raw = ""
    for attempt in range(1, args.runs + 1):
        print(f"\n--- run {attempt}/{args.runs} " + "-" * 40)
        started = time.time()
        try:
            project, raw = generate_project(role["title"], role["one_liner"], states)
        except AnalysisFailed as exc:
            # The lane's retry already fired twice before this point.
            print(f"  FAILED after {time.time() - started:.1f}s: {exc}")
            continue
        warnings = report(project, states, time.time() - started, raw)
        if warnings:
            print("  WARNINGS:")
            for warning in warnings:
                print(f"    - {warning}")
        else:
            print("  clean")
        clean += 1
        last_raw = raw

    print(f"\n{clean}/{args.runs} runs validated")

    if args.save:
        if not last_raw:
            print("nothing saved -- no run validated")
            return 1
        # The model's own bytes, re-indented but not re-serialised from the parsed model:
        # re-dumping would reorder keys and stop the fixture being a faithful record.
        FIXTURE.write_text(
            json.dumps(json.loads(last_raw), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"saved {FIXTURE}")
        print("  regenerate the demo repo and demo_review.json to match, or all three disagree")

    return 0 if clean == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
