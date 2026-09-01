"""Verify a deployed ANCHOR API from outside. Day-1 CORS check and Day-3 go/no-go.

    python scripts/smoke_deploy.py --url https://anchor-api.onrender.com
    python scripts/smoke_deploy.py --url https://... --origin https://anchor.vercel.app
    python scripts/smoke_deploy.py --url https://... --analyze     # answers TDD Appendix B

Read-only except with --analyze, which creates one throwaway student and runs a real
analysis. Exits non-zero if any check fails, so CI or a pre-demo script can gate on it.
"""

import argparse
import json
import sys
import time
from typing import Any

import httpx

DEMO_STUDENT: dict[str, Any] = {
    "name": "Smoke Test",                       # deliberately NOT the demo name — see --analyze
    "semester": 4,
    "interests": ["Artificial Intelligence", "Databases"],
    "courses": [
        {"course_id": "cs201", "semester_tag": "past"},
        {"course_id": "cs301", "semester_tag": "past"},
        {"course_id": "cs401", "semester_tag": "current"},
    ],
}

# TDD §5.1: some host proxies cut long requests at ~100 s. Measured live analysis is 53-102 s,
# which straddles it — the whole point of the --analyze check.
PROXY_WARNING_SECONDS = 100
ANALYZE_TIMEOUT_SECONDS = 240                   # matches the client timeout in lib/api.ts

results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    """detail is remediation advice — only shown when the check actually fails."""
    results.append((ok, name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="smoke-test a deployed ANCHOR API")
    parser.add_argument("--url", required=True, help="base URL, e.g. https://anchor-api.onrender.com")
    parser.add_argument("--origin", default="http://localhost:5173", help="frontend origin to test CORS from")
    parser.add_argument("--analyze", action="store_true", help="run a real analysis and time it")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        print(f"\n=== {base} ===")

        # 1. reachable, and honest about its own configuration
        try:
            health = client.get(f"{base}/health")
        except httpx.HTTPError as e:
            check(False, "reachable", str(e))
            return report()
        if not check(health.status_code == 200, f"GET /health -> {health.status_code}"):
            return report()

        body = health.json()
        print(f"        {json.dumps(body)}")
        check(body.get("database") is True, "database reachable", "check DATABASE_URL (session pooler, :5432)")

        # 2. THE deploy trap: contracts/ ships outside backend/
        check(
            body.get("demo_fixtures_present") is True,
            "contracts/fixtures/ shipped",
            f"missing {body.get('missing_demo_fixtures')} — deploy from the repo ROOT, not backend/",
        )
        if body.get("demo_mode"):
            check(body.get("demo_repo_url_set") is True, "DEMO_REPO_URL set",
                  "unset means the demo submit falls through to a LIVE review: 4 s becomes up to 124 s")
        else:
            print("  note  DEMO_MODE is off — turn it on for the slot (PRD §12.1)")
        check(body.get("llm_key_set") is True, "model provider key set", "/analyze will 502 without it")
        check(body.get("github_token_set") is True, "GITHUB_TOKEN set",
              "unauthenticated GitHub is 60 req/h; judge trials exhaust it (DECISIONS #24)")

        # 3. the catalog, and CORS from the real frontend origin
        courses = client.get(f"{base}/api/courses")
        n = len(courses.json().get("courses", [])) if courses.status_code == 200 else 0
        check(courses.status_code == 200 and n == 10, f"GET /api/courses -> {courses.status_code}, {n} courses")

        preflight = client.request(
            "OPTIONS", f"{base}/api/students",
            headers={"Origin": args.origin, "Access-Control-Request-Method": "POST",
                     "Access-Control-Request-Headers": "x-student-id,content-type"},
        )
        allowed = preflight.headers.get("access-control-allow-origin")
        check(allowed == args.origin, f"CORS allows {args.origin}",
              f"got {allowed!r} — add it to CORS_ORIGINS (comma-separated)")

        # 4. identity still behaves
        check(client.get(f"{base}/api/roadmap").status_code == 404, "GET /api/roadmap without a header is 404")

        if args.analyze:
            print("\n  --analyze: creating a throwaway student and running a real analysis")
            print("  (name is 'Smoke Test', so DEMO_MODE's cached path is bypassed on purpose)")
            created = client.post(f"{base}/api/students", json=DEMO_STUDENT)
            if not check(created.status_code == 201, "POST /api/students", f"HTTP {created.status_code}"):
                return report()
            sid = created.json()["student_id"]

            started = time.monotonic()
            try:
                analyzed = client.post(f"{base}/api/analyze", headers={"X-Student-Id": sid},
                                       timeout=ANALYZE_TIMEOUT_SECONDS)
                elapsed = time.monotonic() - started
                ok = analyzed.status_code == 200
                check(ok, "POST /api/analyze completed", f"HTTP {analyzed.status_code} in {elapsed:.1f}s")
                if ok:
                    print(f"\n  TDD Appendix B: the host did NOT cut a {elapsed:.1f}s request.")
                    if elapsed > PROXY_WARNING_SECONDS:
                        print(f"  It is over the ~{PROXY_WARNING_SECONDS}s warning though — little headroom.")
                    else:
                        print("  Async analyze is NOT needed. Record the decision in DECISIONS.md.")
                roadmap = client.get(f"{base}/api/roadmap", headers={"X-Student-Id": sid})
                check(roadmap.status_code == 200, "GET /api/roadmap after analysis", f"HTTP {roadmap.status_code}")
            except httpx.HTTPError as e:
                elapsed = time.monotonic() - started
                check(False, "POST /api/analyze completed", f"cut after {elapsed:.1f}s: {e}")
                print(f"\n  TDD Appendix B: the host CUT the request at ~{elapsed:.0f}s.")
                print("  Implement Appendix B (~40 backend lines in routers/analyze.py), or")
                print("  confirm the pitch runs entirely in DEMO_MODE (6 s) and record that choice.")

    return report()


def report() -> int:
    failed = [name for ok, name, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
