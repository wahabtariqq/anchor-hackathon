"""Retry just the repo-review step of scripts/live_smoke.py against the account it left behind.

    python scripts/live_smoke_submit.py --base http://127.0.0.1:8010

`POST /api/submit` is the one step that depends on two live services at once (GitHub, then the
model), so it is the one most likely to hit a transient upstream 503. Re-running the whole smoke
script to retry it would pay for a fresh analysis and a fresh project generation; this issues a
session for the newest account directly against the same database and submits again, so the
retry costs exactly one model call.

Local operator tool: it needs the DB file, not a password.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx                                                     # noqa: E402
from sqlmodel import Session, col, select                        # noqa: E402

from app.auth import issue_session                               # noqa: E402
from app.db import engine                                        # noqa: E402
from app.models import Project, Student, User                    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--repo", default="https://github.com/Umer-prog/cached-product-search-api")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--wait", type=float, default=20.0, help="seconds between attempts")
    args = ap.parse_args()

    with Session(engine) as db:
        user = db.exec(select(User).order_by(col(User.created_at).desc())).first()
        if not user:
            print("no account in this database — run scripts/live_smoke.py first")
            return 1
        student = db.exec(
            select(Student)
            .where(Student.user_id == user.id)
            .order_by(col(Student.created_at).desc())
        ).first()
        if not student:
            print(f"{user.email} has no student profile")
            return 1
        project = db.exec(
            select(Project)
            .where(Project.student_id == student.id)
            .order_by(col(Project.created_at).desc())
        ).first()
        if not project:
            print("no generated project to submit against")
            return 1
        # read every attribute before issue_session commits — a commit expires these instances,
        # and they are detached the moment the session closes
        email, role_id, title = user.email, project.role_id, project.title
        token = issue_session(db, user)

    print(f"account: {email}\nproject: {title}\nrepo:    {args.repo}\n", flush=True)
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(base_url=args.base, timeout=300.0) as c:
        for attempt in range(1, args.attempts + 1):
            started = time.monotonic()
            res = c.post("/api/submit", json={"role_id": role_id, "repo_url": args.repo},
                         headers=headers)
            elapsed = time.monotonic() - started
            print(f"attempt {attempt}: {res.status_code} in {elapsed:.1f}s", flush=True)

            if res.status_code == 200:
                review = res.json()["review"]
                print(f"\nscore: {review['total']}/{review['max_total']}  "
                      f"{'PASSED' if review['passed'] else 'not yet'}\n", flush=True)
                for cs in review["criteria_scores"]:
                    print(f"  [{cs['score']}/2] {cs['criterion']}", flush=True)
                    print(f"         {cs['note']}\n", flush=True)
                print(f"feedback: {review['feedback']}", flush=True)
                print(f"\nverified skill ids: {len(res.json()['verified_skill_ids'])}", flush=True)

                dash = c.get("/api/dashboard", headers=headers).json()
                print(f"\ndashboard now: top role {dash['top_role']['title']} "
                      f"{dash['top_role']['fit_percent']}% · "
                      f"{dash['skills_verified']} verified (+{dash['verified_delta']})", flush=True)
                for e in dash["recent_events"][:4]:
                    print(f"  feed: {e['text']}", flush=True)

                history = c.get("/api/projects", headers=headers).json()["projects"]
                for pwh in history:
                    for sub in pwh["submissions"]:
                        print(f"  history: {pwh['project']['title']} — {sub['total']}/"
                              f"{sub['max_total']} {'passed' if sub['passed'] else 'not yet'} "
                              f"({sub['repo_url']})", flush=True)
                return 0

            detail = json.loads(res.text).get("detail", res.text) if res.text else res.text
            print(f"  {str(detail)[:300]}", flush=True)
            transient = res.status_code == 502 and ("503" in str(detail) or "UNAVAILABLE" in str(detail))
            if not transient:
                print("\nnot a transient upstream error — stopping.", flush=True)
                return 1
            if attempt < args.attempts:
                print(f"  upstream is busy; waiting {args.wait:.0f}s\n", flush=True)
                time.sleep(args.wait)

    print("\nstill failing after every attempt — the model provider is refusing, not the code.",
          flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
