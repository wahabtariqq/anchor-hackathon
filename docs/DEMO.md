# Demo runbook

## Before the slot (15 min)

1. Backend env on the deployed host: `DEMO_MODE=true`, `DEMO_STUDENT_NAME=Ayesha`.
2. Open the deployed frontend on the **demo laptop**, not a phone.
3. Run Setup once as Ayesha (see below). Confirm the Roadmap renders and a tick re-sorts.
4. Click **Start over** so the Setup screen is fresh. Leave the tab open.
5. Close every other tab and notification source.
6. Decide who clicks and who talks. Same people as rehearsal.

## Demo student

Name **Ayesha**, semester **4**.
Past: CS201 Data Structures & Algorithms, CS301 Database Management Systems.
Current: CS401 Machine Learning, CS402 Web Development.
Interests: Artificial Intelligence, Databases, UI/UX Design.

## Script — 60 seconds

| t | Do | Say |
|---|---|---|
| 0:00 | Setup screen | "A 4th-semester student. Two courses done, two in progress." |
| 0:08 | Point at the paste link | "Different syllabus? Paste your own." |
| 0:11 | Click Analyze | (analyzing screen runs, ~6s) |
| 0:18 | Roadmap | "Eight roles, ranked by how far along she already is. Not a quiz — computed from what her courses teach." |
| 0:28 | Adjacent section, read one bridge line | "She never asked for this one — the system found it." |
| 0:38 | Click a role, drawer opens | "Covered by her coursework. Missing. Each with where it actually matters." |
| 0:46 | Tick three boxes | "Every role recomputes at once — they all share one skill vocabulary." Point at the "what moved" line. |
| 0:57 | Stop talking | |

## If something breaks

- Analyze hangs > 20s in demo mode → `DEMO_MODE` isn't set on the host. Say "let me use the cached run" and reload; it's on the Roadmap already if step 3 above was done.
- Roadmap 404 → hit Start over, redo Setup. 25 seconds.
- Tick doesn't re-sort → it's still the fixture path or `VITE_USE_FIXTURE` is set. Fall back to describing it; do not debug on stage.

## Judge Q&A

See PRD §15. Short versions: fit % is arithmetic not model output · one shared skill vocabulary is why one tick moves four cards · paste handles syllabus differences · auth was cut deliberately · ticking everything is self-assessment, coursework coverage is the model's.
