"""End-to-end live smoke: every endpoint, real model calls, a real GitHub repo.

    uvicorn app.main:app --port 8010          # with a scratch DATABASE_URL
    python scripts/live_smoke.py --base http://127.0.0.1:8010

Walks the whole product in the order a student does — signup, login, onboarding, gap analysis,
roadmap, tick, project generation, repo submission, dashboard — and prints what each call
returned. Unlike `pytest`, this makes **real** calls: three to the model provider and up to
twelve to GitHub. That is the point; it is the only check that the pipeline works outside the
stubs, so it is a script you run, never a test the suite collects.

Exit code is 0 only if every step passed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from typing import Any

import httpx

TIMEOUT = 300.0
DEMO_REPO = "https://github.com/Umer-prog/cached-product-search-api"

STUDENT = {
    "name": "Ayesha",
    "semester": 4,
    "interests": ["Artificial Intelligence", "Databases", "UI/UX Design"],
    "courses": [
        {"course_id": "cs201", "semester_tag": "past"},
        {"course_id": "cs301", "semester_tag": "past"},
        {"course_id": "cs401", "semester_tag": "current"},
        {"course_id": "cs402", "semester_tag": "current"},
    ],
}

results: list[tuple[str, str, float, str]] = []
failures = 0


def step(name: str, res: httpx.Response, expect: int, note: str = "", elapsed: float = 0.0) -> Any:
    """Record one call. Returns the parsed body when it matched, else None."""
    global failures
    ok = res.status_code == expect
    if not ok:
        failures += 1
        note = f"expected {expect}, got {res.status_code}: {res.text[:300]}"
    results.append((name, "PASS" if ok else "FAIL", elapsed, note))
    marker = "ok " if ok else "FAIL"
    print(f"  [{marker}] {name}  ({res.status_code}, {elapsed:.1f}s) {note}", flush=True)
    if not ok:
        return None
    try:
        return res.json()
    except ValueError:
        return None


def call(client: httpx.Client, method: str, path: str, **kw: Any) -> tuple[httpx.Response, float]:
    started = time.monotonic()
    res = client.request(method, path, **kw)
    return res, time.monotonic() - started


def check(name: str, condition: bool, detail: str = "") -> None:
    global failures
    if not condition:
        failures += 1
    results.append((name, "PASS" if condition else "FAIL", 0.0, detail))
    print(f"  [{'ok ' if condition else 'FAIL'}] {name} {detail}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--repo", default=DEMO_REPO)
    args = ap.parse_args()

    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    password = "hunter2-strong"

    with httpx.Client(base_url=args.base, timeout=TIMEOUT) as c:
        print("\n== 1. health and the public catalog ==", flush=True)
        res, t = call(c, "GET", "/health")
        health = step("GET /health", res, 200, elapsed=t)
        if health:
            print(f"        readiness: {json.dumps(health)[:220]}", flush=True)

        res, t = call(c, "GET", "/api/courses")
        courses = step("GET /api/courses (public, no token)", res, 200, elapsed=t)
        if courses:
            check("  catalog has 10 courses", len(courses["courses"]) == 10,
                  f"{len(courses['courses'])} returned")

        print("\n== 2. accounts and sessions ==", flush=True)
        res, t = call(c, "POST", "/api/auth/signup",
                      json={"email": email, "password": password, "name": "Ayesha"})
        signup = step("POST /api/auth/signup", res, 200, elapsed=t)
        if signup:
            check("  signup issues no token", "token" not in signup)

        res, t = call(c, "POST", "/api/auth/signup",
                      json={"email": email, "password": password, "name": "Ayesha"})
        step("POST /api/auth/signup (duplicate email -> 409)", res, 409, elapsed=t)

        res, t = call(c, "POST", "/api/auth/login", json={"email": email, "password": "wrong-one"})
        bad_pw = step("POST /api/auth/login (wrong password -> 401)", res, 401, elapsed=t)
        res, t = call(c, "POST", "/api/auth/login",
                      json={"email": f"nobody-{uuid.uuid4().hex[:6]}@example.com", "password": password})
        unknown = step("POST /api/auth/login (unknown email -> 401)", res, 401, elapsed=t)
        if bad_pw and unknown:
            check("  both 401s are byte-identical (no enumeration oracle)", bad_pw == unknown,
                  f"{bad_pw} vs {unknown}")

        res, t = call(c, "POST", "/api/auth/login", json={"email": email, "password": password})
        auth = step("POST /api/auth/login", res, 200, elapsed=t)
        if not auth:
            return report()
        headers = {"Authorization": f"Bearer {auth['token']}"}

        res, t = call(c, "GET", "/api/roadmap", headers={"Authorization": "Bearer not-a-token"})
        step("GET /api/roadmap (bad token -> 401)", res, 401, elapsed=t)

        print("\n== 3. authenticated but not onboarded ==", flush=True)
        for path in ("/api/roadmap", "/api/dashboard", "/api/skills", "/api/projects"):
            res, t = call(c, "GET", path, headers=headers)
            body = step(f"GET {path} (no student yet -> 404)", res, 404, elapsed=t)
            if body and path == "/api/dashboard":
                check("  404 says 'complete onboarding', not 'unauthorized'",
                      body["detail"].startswith("No student profile yet"), body["detail"])

        print("\n== 4. onboarding ==", flush=True)
        res, t = call(c, "POST", "/api/students", json=STUDENT, headers=headers)
        created = step("POST /api/students", res, 201, elapsed=t)
        if not created:
            return report()
        print(f"        student_id: {created['student_id']}", flush=True)

        print("\n== 5. gap analysis — LIVE model call ==", flush=True)
        res, t = call(c, "POST", "/api/analyze", headers=headers)
        analyzed = step("POST /api/analyze  [LIVE]", res, 200, elapsed=t)
        if not analyzed:
            print("\n  !! The analysis call failed. If this is a quota/rate-limit answer, swap "
                  "GEMINI_API_KEY in backend/.env and re-run.\n", flush=True)
            return report()

        res, t = call(c, "GET", "/api/roadmap", headers=headers)
        roadmap = step("GET /api/roadmap", res, 200, elapsed=t)
        if not roadmap:
            return report()
        core = [r for r in roadmap["roles"] if r["proximity"] == "core"]
        adjacent = [r for r in roadmap["roles"] if r["proximity"] == "adjacent"]
        check("  8 roles ranked", len(roadmap["roles"]) == 8, f"{len(roadmap['roles'])} roles")
        check("  roles are sorted by fit",
              [r["fit_percent"] for r in roadmap["roles"]]
              == sorted((r["fit_percent"] for r in roadmap["roles"]), reverse=True))
        print(f"        {len(roadmap['skills'])} skills · {len(core)} core / {len(adjacent)} adjacent roles", flush=True)
        for r in roadmap["roles"][:3]:
            print(f"          {r['fit_percent']:3}%  {r['title']} — {r['one_liner'][:70]}", flush=True)

        print("\n== 6. the three V2 read endpoints ==", flush=True)
        res, t = call(c, "GET", "/api/skills", headers=headers)
        skills = step("GET /api/skills", res, 200, elapsed=t)
        if skills:
            check("  every roadmap skill is listed",
                  [s["id"] for s in skills["skills"]] == [s["id"] for s in roadmap["skills"]])
            shared = [s for s in skills["skills"] if len(s["roles"]) > 1]
            check("  skills carry their roles (one row, many roles)", bool(shared),
                  f"{len(shared)} skills wanted by more than one role")

        res, t = call(c, "GET", "/api/dashboard", headers=headers)
        dash0 = step("GET /api/dashboard (day one)", res, 200, elapsed=t)
        if dash0:
            check("  top role matches the roadmap", dash0["top_role"]["id"] == core[0]["id"])
            check("  chart is empty — no backfill",
                  all(p == [] for p in dash0["snapshots"].values()))
            check("  three next actions, one per charted role", len(dash0["next_actions"]) == 3)
            for a in dash0["next_actions"]:
                print(f"          [{a['kind']}] {a['label']}", flush=True)

        res, t = call(c, "GET", "/api/projects", headers=headers)
        projects0 = step("GET /api/projects (before Prove It)", res, 200, elapsed=t)
        if projects0 is not None:
            check("  no projects yet", projects0 == {"projects": []})

        print("\n== 7. ticking a skill writes an event and a snapshot ==", flush=True)
        by_id = {s["id"]: s for s in roadmap["skills"]}

        def unresolved(sid: str) -> bool:
            s = by_id[sid]
            return not (s["checked"] or s["verified"] or s["coverage_depth"])

        charted = [a["role_id"] for a in (dash0 or {"next_actions": []})["next_actions"]]
        target = next(
            (
                (r, rs["skill_id"])
                for r in roadmap["roles"]
                if r["id"] in charted
                for rs in r["skills"]
                if unresolved(rs["skill_id"])
            ),
            None,
        )
        if not target:
            check("  a charted role has an unresolved skill to tick", False,
                  "every charted role is fully covered — the chart cannot move via a tick")
        else:
            role, skill_id = target
            print(f"        ticking '{by_id[skill_id]['name']}' for {role['title']}", flush=True)
            res, t = call(c, "POST", "/api/progress",
                          json={"skill_id": skill_id, "checked": True}, headers=headers)
            step("POST /api/progress (tick)", res, 200, elapsed=t)

            res, t = call(c, "GET", "/api/dashboard", headers=headers)
            dash1 = step("GET /api/dashboard (after the tick)", res, 200, elapsed=t)
            if dash1:
                check("  checked_delta is 1", dash1["checked_delta"] == 1, str(dash1["checked_delta"]))
                points = dash1["snapshots"].get(role["id"], [])
                check("  the chart gained a point for that role", len(points) == 1,
                      f"{len(points)} points: {points}")
                check("  the feed says what happened",
                      any(e["text"] == f"Marked {by_id[skill_id]['name']} as learned"
                          for e in dash1["recent_events"]),
                      str([e["text"] for e in dash1["recent_events"]][:3]))

            res, t = call(c, "POST", "/api/progress",
                          json={"skill_id": skill_id, "checked": False}, headers=headers)
            step("POST /api/progress (untick)", res, 200, elapsed=t)
            res, t = call(c, "GET", "/api/dashboard", headers=headers)
            dash2 = step("GET /api/dashboard (after the untick)", res, 200, elapsed=t)
            if dash2:
                check("  the untick cancels the delta", dash2["checked_delta"] == 0,
                      str(dash2["checked_delta"]))
            # leave it ticked for the rest of the run
            call(c, "POST", "/api/progress",
                 json={"skill_id": skill_id, "checked": True}, headers=headers)

        res, t = call(c, "POST", "/api/progress",
                      json={"skill_id": "not-a-real-skill", "checked": True}, headers=headers)
        step("POST /api/progress (unknown skill -> 404)", res, 404, elapsed=t)

        print("\n== 8. project generation — LIVE model call ==", flush=True)
        role = core[0]
        res, t = call(c, "GET", f"/api/project?role_id={role['id']}", headers=headers)
        project = step(f"GET /api/project ({role['title']})  [LIVE]", res, 200, elapsed=t)
        if not project:
            print("\n  !! Project generation failed. If this is a quota answer, swap "
                  "GEMINI_API_KEY in backend/.env and re-run.\n", flush=True)
            return report()
        print(f"        title:    {project['title']}", flush=True)
        print(f"        spec:     {project['spec'][:160]}...", flush=True)
        for crit in project["criteria"]:
            print(f"        criterion: {crit}", flush=True)
        check("  the project verifies skills this role actually wants",
              set(project["verifies"]) <= {rs["skill_id"] for rs in role["skills"]},
              f"verifies {len(project['verifies'])} skills")

        res, t = call(c, "GET", f"/api/project?role_id={role['id']}", headers=headers)
        cached = step("GET /api/project (again -> cached, no second model call)", res, 200, elapsed=t)
        if cached:
            check("  the cached project is identical", cached == project)

        res, t = call(c, "GET", "/api/projects", headers=headers)
        projects1 = step("GET /api/projects (after generation)", res, 200, elapsed=t)
        if projects1:
            check("  the project appears in the plural view", len(projects1["projects"]) == 1)
            check("  the plural view does not reshape it",
                  projects1["projects"][0]["project"] == project)
            check("  no submissions yet", projects1["projects"][0]["submissions"] == [])

        print("\n== 9. repo review — LIVE GitHub fetch + LIVE model call ==", flush=True)
        print(f"        repo: {args.repo}", flush=True)
        res, t = call(c, "POST", "/api/submit",
                      json={"role_id": role["id"], "repo_url": args.repo}, headers=headers)
        submitted = step("POST /api/submit  [LIVE]", res, 200, elapsed=t)
        if submitted:
            review = submitted["review"]
            print(f"\n        score: {review['total']}/{review['max_total']}  "
                  f"{'PASSED' if review['passed'] else 'not yet'}", flush=True)
            for cs in review["criteria_scores"]:
                print(f"          [{cs['score']}/2] {cs['criterion']}", flush=True)
                print(f"                 {cs['note']}", flush=True)
            print(f"\n        feedback: {review['feedback']}\n", flush=True)
            check("  total is the sum of the criterion scores",
                  review["total"] == sum(cs["score"] for cs in review["criteria_scores"]))
            check("  max_total is 2 per criterion",
                  review["max_total"] == 2 * len(review["criteria_scores"]))
            check("  verified set is returned whole",
                  isinstance(submitted["verified_skill_ids"], list))

            res, t = call(c, "GET", "/api/projects", headers=headers)
            projects2 = step("GET /api/projects (with history)", res, 200, elapsed=t)
            if projects2:
                history = projects2["projects"][0]["submissions"]
                check("  the submission is in the history", len(history) == 1)
                if history:
                    check("  history carries the repo, score and feedback",
                          history[0]["repo_url"] == args.repo
                          and history[0]["total"] == review["total"]
                          and history[0]["feedback"] == review["feedback"])

            res, t = call(c, "GET", "/api/dashboard", headers=headers)
            dash3 = step("GET /api/dashboard (after the submission)", res, 200, elapsed=t)
            if dash3:
                texts = [e["text"] for e in dash3["recent_events"]]
                check("  the feed records the submission",
                      f"Submitted a repo for {role['title']}" in texts, str(texts[:3]))
                if review["passed"]:
                    check("  a pass is its own feed line",
                          f"Verified skills for {role['title']} via repo review" in texts)
                    check("  verified_delta counts it", dash3["verified_delta"] >= 1,
                          str(dash3["verified_delta"]))
                    check("  skills_verified is no longer zero", dash3["skills_verified"] > 0)
                print(f"        top role now: {dash3['top_role']['title']} "
                      f"{dash3['top_role']['fit_percent']}%", flush=True)
                for rid, pts in dash3["snapshots"].items():
                    if pts:
                        title = next(r["title"] for r in roadmap["roles"] if r["id"] == rid)
                        print(f"          {title}: {[p['fit'] for p in pts]}", flush=True)

        res, t = call(c, "POST", "/api/submit",
                      json={"role_id": role["id"], "repo_url": "https://gitlab.com/o/r"},
                      headers=headers)
        step("POST /api/submit (not a GitHub URL -> 422)", res, 422, elapsed=t)

        print("\n== 10. logout ends the session ==", flush=True)
        res, t = call(c, "POST", "/api/auth/logout", headers=headers)
        step("POST /api/auth/logout", res, 200, elapsed=t)
        res, t = call(c, "GET", "/api/dashboard", headers=headers)
        step("GET /api/dashboard (after logout -> 401)", res, 401, elapsed=t)

        res, t = call(c, "POST", "/api/auth/login", json={"email": email, "password": password})
        again = step("POST /api/auth/login (log back in)", res, 200, elapsed=t)
        if again:
            h2 = {"Authorization": f"Bearer {again['token']}"}
            res, t = call(c, "GET", "/api/dashboard", headers=h2)
            dash4 = step("GET /api/dashboard (data survived the logout)", res, 200, elapsed=t)
            if dash4:
                check("  the work is still there", dash4["skills_checked"] >= 1)
                check("  deltas reset on the new visit", dash4["checked_delta"] == 0,
                      str(dash4["checked_delta"]))
            res, t = call(c, "POST", "/api/auth/logout_all", headers=h2)
            step("POST /api/auth/logout_all", res, 200, elapsed=t)
            res, t = call(c, "GET", "/api/dashboard", headers=h2)
            step("GET /api/dashboard (after logout_all -> 401)", res, 401, elapsed=t)

    return report()


def report() -> int:
    print("\n" + "=" * 78, flush=True)
    print(f"{'STEP':<58} {'RESULT':<6} {'TIME':>6}", flush=True)
    print("-" * 78, flush=True)
    for name, verdict, elapsed, note in results:
        secs = f"{elapsed:.1f}s" if elapsed else ""
        print(f"{name[:57]:<58} {verdict:<6} {secs:>6}", flush=True)
        if verdict == "FAIL" and note:
            print(f"    -> {note[:200]}", flush=True)
    passed = sum(1 for _, v, _, _ in results if v == "PASS")
    print("-" * 78, flush=True)
    print(f"{passed}/{len(results)} passed, {failures} failed", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
