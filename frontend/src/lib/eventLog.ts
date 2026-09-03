import type { DashboardResponse, SnapshotPoint } from "./types";

// Frontend-only simulation of TDD-V2 §4.2's `Event`/`FitSnapshot` tables, localStorage-backed
// instead of DB-backed, because /api/dashboard doesn't exist yet (docs/PRD-V2.md §0). Seeded
// once from contracts/fixtures/dashboard_response.json so a fresh browser still shows a history
// on day one; every tick/submission made during real use of the app appends to it for real, so
// the Dashboard's chart and activity feed actually move instead of staying frozen on the seed.
// Survives a refresh (localStorage) but not a second browser — that's an honest limitation, not
// a faked one. Delete this file and swap DashboardPage's reads for a real `getDashboard()` call
// once the backend lands; nothing else about the UI needs to change.

const EVENTS_KEY = "anchor:sim_events";
const SNAPSHOTS_KEY = "anchor:sim_snapshots";
const SEEDED_KEY = "anchor:sim_seeded";
const LAST_SEEN_KEY = "anchor:last_seen_at";
const BASELINE_KEY = "anchor:dashboard_baseline_at";

export type SimEventType = "tick" | "untick" | "submission" | "pass";

export interface SimEvent {
  type: SimEventType;
  at: string; // ISO timestamp
  skillName?: string;
  roleTitle?: string;
  repoUrl?: string;
  total?: number;
  maxTotal?: number;
  /** Seed events arrive pre-humanized from the fixture; live events are formatted from the
   *  fields above at read time — see humanize(). */
  text?: string;
}

export interface SimSnapshot {
  roleId: string;
  fitPercent: number;
  at: string;
}

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function getEvents(): SimEvent[] {
  return read<SimEvent[]>(EVENTS_KEY, []);
}

function getSnapshots(): SimSnapshot[] {
  return read<SimSnapshot[]>(SNAPSHOTS_KEY, []);
}

/** Seeds the log once from the dashboard fixture. After this, only the record* calls below grow
 *  it — the fixture is never re-read, so it can't overwrite anything you did this session. */
export function seedIfEmpty(seed: DashboardResponse): void {
  if (localStorage.getItem(SEEDED_KEY)) return;

  const events: SimEvent[] = seed.recent_events.map((e) => ({
    type: "tick" as const,
    at: e.at,
    text: e.text,
  }));
  const snapshots: SimSnapshot[] = Object.entries(seed.snapshots).flatMap(([roleId, points]) =>
    points.map((p) => ({ roleId, fitPercent: p.fit, at: p.at })),
  );

  write(EVENTS_KEY, events);
  write(SNAPSHOTS_KEY, snapshots);
  localStorage.setItem(SEEDED_KEY, "1");
}

/** Mirrors app/events.py's record_tick. */
export function recordTick(skillName: string, checked: boolean): void {
  const events = getEvents();
  events.push({ type: checked ? "tick" : "untick", skillName, at: new Date().toISOString() });
  write(EVENTS_KEY, events);
}

/** Mirrors app/events.py's record_submission — a "submission" event, plus a "pass" event too
 *  when it passed. repo_url/total/max_total ride along so ProjectsPage can render a live
 *  submission row without a second store. */
export function recordSubmission(
  roleTitle: string,
  repoUrl: string,
  total: number,
  maxTotal: number,
  passed: boolean,
): void {
  const events = getEvents();
  const at = new Date().toISOString();
  events.push({ type: "submission", roleTitle, repoUrl, total, maxTotal, at });
  if (passed) events.push({ type: "pass", roleTitle, repoUrl, total, maxTotal, at });
  write(EVENTS_KEY, events);
}

/** Mirrors app/events.py's snapshot_changed_roles: one row per role whose fit actually moved.
 *  `before` is undefined on the very first computation (nothing to compare yet) — no snapshot. */
export function recordSnapshotIfChanged(roleId: string, before: number | undefined, after: number): void {
  if (before === undefined || before === after) return;
  const snapshots = getSnapshots();
  snapshots.push({ roleId, fitPercent: after, at: new Date().toISOString() });
  write(SNAPSHOTS_KEY, snapshots);
}

export function getEventsSince(sinceIso: string | null): SimEvent[] {
  const events = getEvents();
  return sinceIso ? events.filter((e) => e.at >= sinceIso) : events;
}

export function getRecentEvents(n: number): SimEvent[] {
  return [...getEvents()].sort((a, b) => (a.at < b.at ? 1 : -1)).slice(0, n);
}

export function getSnapshotsForRoles(roleIds: string[]): Record<string, SnapshotPoint[]> {
  const ids = new Set(roleIds);
  const out: Record<string, SnapshotPoint[]> = {};
  for (const id of ids) out[id] = [];
  for (const s of getSnapshots()) {
    if (!ids.has(s.roleId)) continue;
    out[s.roleId].push({ fit: s.fitPercent, at: s.at });
  }
  for (const id of ids) out[id].sort((a, b) => (a.at < b.at ? -1 : 1));
  return out;
}

export function getLiveSubmissionsForRole(roleTitle: string): SimEvent[] {
  return getEvents().filter((e) => e.type === "submission" && e.roleTitle === roleTitle);
}

export function humanize(event: SimEvent): string {
  if (event.text) return event.text;
  switch (event.type) {
    case "tick":
      return `Marked ${event.skillName} as learned`;
    case "untick":
      return `Unmarked ${event.skillName}`;
    case "submission":
      return `Submitted a repo for ${event.roleTitle} — ${event.total}/${event.maxTotal}`;
    case "pass":
      return `Verified skills via repo review for ${event.roleTitle}`;
    default:
      return "";
  }
}

/** Called once per login/signup — never per-request (TDD-V2 §4.4: last_seen_at is a session
 *  baseline, not a freshness timestamp). Returns the *previous* value, frozen as this session's
 *  Dashboard delta baseline, before overwriting it with now for next time. */
export function rotateLastSeen(): string {
  const prev = localStorage.getItem(LAST_SEEN_KEY);
  const now = new Date().toISOString();
  localStorage.setItem(LAST_SEEN_KEY, now);
  const baseline = prev ?? now;
  localStorage.setItem(BASELINE_KEY, baseline);
  return baseline;
}

export function getDashboardBaseline(): string | null {
  return localStorage.getItem(BASELINE_KEY);
}
