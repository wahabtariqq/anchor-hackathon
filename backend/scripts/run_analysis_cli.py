"""Run the analysis pipeline with no server and no database.

    python scripts/run_analysis_cli.py --demo
    python scripts/run_analysis_cli.py --demo --runs 3          # the S3 done-check
    python scripts/run_analysis_cli.py --demo --save            # writes the demo fixture
    python scripts/run_analysis_cli.py --courses cs201,cs301 --interests "Databases,Security"

This is the live integration path for the AI lane (TDD 12). The test suite never calls the API;
this does. It prints wall-clock latency and the quality signals S4 tunes against, so a tuning
run is one command rather than a command plus a notebook.

--save writes contracts/fixtures/demo_analysis.json, which feeds DEMO_MODE and Salman's
persistence tests. Only ever save a run you have actually read.
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analysis import AnalysisFailed, run_analysis            # noqa: E402
from app.analysis.schema import AnalysisOut                      # noqa: E402
from app.models import Student, StudentCourse                    # noqa: E402
from seed.courses import CATALOG                                 # noqa: E402

FIXTURE = ROOT / "contracts" / "fixtures" / "demo_analysis.json"

# PRD 12.2. The fixture's coverage codes must match these exactly or persistence silently drops
# coverage rows and every fit percentage comes out low with nothing on screen to explain it.
DEMO_COURSES = {"cs201": "past", "cs301": "past", "cs401": "current", "cs402": "current"}
DEMO_INTERESTS = ["Artificial Intelligence", "Databases", "UI/UX Design"]
DEMO_NAME = "Ayesha"
DEMO_SEMESTER = 4

VAGUE = ("many jobs", "important for", "key skill", "widely used", "essential for", "used in many")


def build_inputs(course_ids: dict[str, str], interests: list[str], name: str, semester: int):
    """Real Student / StudentCourse objects, never persisted. No session, no engine, no DB."""
    by_id = {c["id"]: c for c in CATALOG}
    unknown = set(course_ids) - set(by_id)
    if unknown:
        sys.exit(f"unknown course ids: {sorted(unknown)}\navailable: {sorted(by_id)}")

    student = Student(name=name, semester=semester, interests=interests)
    courses = [
        StudentCourse(
            student_id=student.id,
            course_id=cid,
            code=by_id[cid]["code"],
            name=by_id[cid]["name"],
            curriculum_text=by_id[cid]["curriculum_text"],
            semester_tag=tag,
        )
        for cid, tag in course_ids.items()
    ]
    return student, courses


def near_duplicates(parsed: AnalysisOut) -> list[tuple[str, str]]:
    """Risk-register #1. Two entries a practitioner would call the same skill.

    Flags an id pair that is textually close, or a name pair where one name's words are a
    subset of the other's -- which is how `sql` / `sql-querying` / `relational-databases`
    actually shows up in practice.
    """
    def words(text: str) -> set[str]:
        return set(text.replace("-", " ").lower().split())

    hits = []
    for a, b in itertools.combinations(parsed.skills, 2):
        ratio = difflib.SequenceMatcher(None, a.id, b.id).ratio()
        overlap = words(a.name) & words(b.name)
        subset = overlap and len(overlap) >= min(len(words(a.name)), len(words(b.name)))
        if ratio > 0.72 or subset:
            hits.append((a.id, b.id))
    return hits


def report(parsed: AnalysisOut, elapsed: float, raw: str) -> list[str]:
    """Print the signals S4 tunes against. Returns a list of warnings (empty means clean)."""
    warnings: list[str] = []
    core = sum(r.proximity == "core" for r in parsed.roles)

    print(f"  latency        {elapsed:.1f}s   ({len(raw)} chars)")
    print(f"  skills         {len(parsed.skills)}")
    print(f"  roles          {len(parsed.roles)}  ({core} core / {len(parsed.roles) - core} adjacent)")
    print(f"  coverage rows  {len(parsed.coverage)}")

    appear = Counter(rs.skill_id for r in parsed.roles for rs in r.skills)
    shared = sum(1 for n in appear.values() if n > 1)
    pct = shared / len(appear) * 100 if appear else 0
    print(f"  cross-role reuse   {shared}/{len(appear)} skills in >1 role ({pct:.0f}%), max {max(appear.values(), default=0)}")
    if pct < 30:
        warnings.append(f"reuse only {pct:.0f}% -- one tick will barely move the ranking")

    dupes = near_duplicates(parsed)
    print(f"  near-duplicates    {len(dupes)}")
    for a, b in dupes[:8]:
        print(f"      {a}  <->  {b}")
    if dupes:
        warnings.append(f"{len(dupes)} near-duplicate skill pairs -- tune the CRITICAL block first")

    vague = [s.id for s in parsed.skills if any(v in s.real_world.lower() for v in VAGUE)]
    print(f"  vague real_world   {len(vague)}  {vague[:5]}")
    if vague:
        warnings.append(f"{len(vague)} vague real_world sentences")

    unused = [s.id for s in parsed.skills if s.id not in appear]
    if unused:
        print(f"  unused by any role {len(unused)}  {unused[:5]}")

    codes = sorted({c.course_code for c in parsed.coverage})
    print(f"  coverage codes     {codes}")

    # Not a validator (DECISIONS #57): a bad rank is cosmetic in the roadmap's tie-break and
    # not worth failing a 53-102 s call over. It is worth blocking --save, though -- the demo
    # student's cached analysis is what _demo_applies reads when it picks the top role, and a
    # fixture whose top role is ambiguous can hand the cached demo project to the wrong one.
    ranks = sorted(r.rank for r in parsed.roles)
    if ranks != list(range(1, len(parsed.roles) + 1)):
        warnings.append(f"ranks are {ranks}, want 1-{len(parsed.roles)} each once -- do not --save this")

    thin = [r.title for r in parsed.roles if not r.bridge.strip() and r.proximity == "adjacent"]
    if thin:
        warnings.append(f"adjacent roles with no bridge: {thin}")
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the ANCHOR analysis pipeline, no DB, no server.")
    ap.add_argument("--demo", action="store_true", help="the canonical demo student (PRD 12.2)")
    ap.add_argument("--courses", help="comma-separated catalog ids, e.g. cs201,cs301")
    ap.add_argument("--interests", help="comma-separated interest tags")
    ap.add_argument("--name", default=DEMO_NAME)
    ap.add_argument("--semester", type=int, default=DEMO_SEMESTER)
    ap.add_argument("--runs", type=int, default=1, help="repeat N times; S3 wants 3 clean in a row")
    ap.add_argument("--save", action="store_true", help="write contracts/fixtures/demo_analysis.json")
    args = ap.parse_args()

    if args.demo:
        course_ids = dict(DEMO_COURSES)
        interests = DEMO_INTERESTS
    elif args.courses:
        course_ids = {cid.strip(): "past" for cid in args.courses.split(",") if cid.strip()}
        interests = [i.strip() for i in (args.interests or "").split(",") if i.strip()]
        if len(interests) < 2:
            return ap.error("--interests needs at least two (CONTRACT 3)")
    else:
        return ap.error("pass --demo or --courses")

    if args.save and not args.demo:
        return ap.error("--save only makes sense with --demo; the fixture is the demo student's")

    student, courses = build_inputs(course_ids, interests, args.name, args.semester)
    print(f"{student.name}, semester {student.semester}")
    print(f"courses:   {', '.join(f'{c.code}({c.semester_tag})' for c in courses)}")
    print(f"interests: {', '.join(student.interests)}")

    clean = 0
    last_raw = ""
    for attempt in range(1, args.runs + 1):
        print(f"\n--- run {attempt}/{args.runs} " + "-" * 40)
        started = time.time()
        try:
            parsed, raw = run_analysis(student, courses)
        except AnalysisFailed as exc:
            # The lane's retry already fired twice before this point.
            print(f"  FAILED after {time.time() - started:.1f}s: {exc}")
            continue
        warnings = report(parsed, time.time() - started, raw)
        if warnings:
            print("  WARNINGS:")
            for w in warnings:
                print(f"    - {w}")
        else:
            print("  clean")
        clean += 1
        last_raw = raw

    print(f"\n{clean}/{args.runs} runs validated")

    if args.save:
        if not last_raw:
            print("nothing saved -- no run validated")
            return 1
        # The raw bytes, not a re-serialised model: re-dumping would reorder keys and stop the
        # fixture being a faithful record of what the model actually produced.
        FIXTURE.write_text(json.dumps(json.loads(last_raw), indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        print(f"saved {FIXTURE}")

    return 0 if clean == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
