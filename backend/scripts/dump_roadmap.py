"""Print GET /api/roadmap for one student, straight from the DB.

    python scripts/dump_roadmap.py --student <id>
    python scripts/dump_roadmap.py --student <id> --out ../contracts/fixtures/roadmap_response.json

Refreshing the fixture is a Day-3 integration step and needs --out on purpose: Dev C builds
against the committed file, so this script never overwrites it by accident.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session                              # noqa: E402

from app.db import engine                                 # noqa: E402
from app.models import Student                            # noqa: E402
from app.routers.roadmap import build_roadmap             # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="dump GET /api/roadmap for a student")
    parser.add_argument("--student", required=True, help="student id (uuid)")
    parser.add_argument("--out", type=Path, default=None, help="write here instead of stdout")
    args = parser.parse_args()

    with Session(engine) as session:
        student = session.get(Student, args.student)
        if not student:
            print(f"unknown student {args.student}", file=sys.stderr)
            return 1
        payload = build_roadmap(session, student).model_dump_json(indent=2)

    if args.out:
        args.out.write_text(payload + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
