# Demo runbook

## Before the slot (15 min)

1. Backend env on the deployed host: `DEMO_MODE=true`, `DEMO_STUDENT_NAME=Ayesha`, `DEMO_REPO_URL=<the prepared repo>`, `GITHUB_TOKEN` set.
0. **Days before:** `demo_project.json`, the real public repo at `DEMO_REPO_URL`, and `demo_review.json` were generated together and committed. Do not touch any of the three after that. Copy the repo URL to the demo laptop's clipboard manager.
2. Open the deployed frontend on the **demo laptop**, not a phone.
3. Run Setup once as Ayesha (see below). Confirm the Roadmap renders, the top role's Prove It panel is instant (cached), a tick re-sorts, and pasting `DEMO_REPO_URL` returns the cached passing review in ~4 s.
4. Click **Start over** so the Setup screen is fresh. Leave the tab open.
5. Close every other tab and notification source.
6. Decide who clicks and who talks. Same people as rehearsal.

## Demo student

Name **Ayesha**, semester **4**.
Past: CS201 Data Structures & Algorithms, CS301 Database Management Systems.
Current: CS401 Machine Learning, CS402 Web Development.
Interests: Artificial Intelligence, Databases, UI/UX Design.

## Script — 75 seconds (confirm the hackathon limit first; 60 s fallback below)

| t | Do | Say |
|---|---|---|
| 0:00 | Setup screen | "A 4th-semester student. Two courses done, two in progress." |
| 0:08 | Point at the paste link | "Different syllabus? Paste your own." |
| 0:11 | Click Analyze | (analyzing screen runs, ~6s) |
| 0:18 | Roadmap | "Eight roles, ranked by how far along she already is. Not a quiz — computed from what her courses teach." |
| 0:27 | Adjacent section, read one bridge line | "She never asked for this one — the system found it." |
| 0:36 | Click the top role, drawer opens, Prove It is already there | "Covered. Missing. And a project designed for exactly her gaps." |
| 0:44 | Tick three uncovered boxes — cards shift a little | "A tick moves it a little…" |
| 0:50 | Paste the prepared repo URL, Submit (4 s) | "…a repo that passes review moves it a lot." |
| 0:57 | Review lands: ✓ badges, a role jumps, what-moved fires | "Reviewed by reading the code — and every role sharing those skills just moved too." |
| 1:12 | Stop talking | |

**60 s fallback:** drop the paste-link beat (0:08) and the adjacent beat (0:27); go Setup → Analyze → Roadmap → top role → tick three → submit repo → stop.

## If something breaks

- Analyze hangs > 20s in demo mode → `DEMO_MODE` isn't set on the host. Say "let me use the cached run" and reload; it's on the Roadmap already if step 3 above was done.
- Roadmap 404 → hit Start over, redo Setup. 25 seconds.
- Tick doesn't re-sort → it's still the fixture path or `VITE_USE_FIXTURE` is set. Fall back to describing it; do not debug on stage.
- Submit returns 422/502 → `DEMO_REPO_URL` doesn't match what you pasted (trailing slash, http vs https) or `DEMO_MODE` is off. Say "the review is cached for this repo — let me show the result" and open the drawer again: the latest review renders from `/roadmap` if step 3 above was done.

## Judge Q&A

See PRD §15. Short versions: fit % is arithmetic not model output · one shared skill vocabulary is why one tick moves four cards · paste handles syllabus differences · auth was cut deliberately · ticking everything is self-assessment, coursework coverage is the model's.
