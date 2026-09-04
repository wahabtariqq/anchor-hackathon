import { useEffect, useMemo, useState } from "react";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { Skeleton } from "@/components/ui/skeleton";
import { getDashboard } from "@/lib/api";
import { getUser } from "@/lib/auth";
import {
  getDashboardBaseline,
  getEventsSince,
  getRecentEvents,
  getSnapshotsForRoles,
  humanize,
  seedIfEmpty,
} from "@/lib/eventLog";
import { ActivityFeed } from "./ActivityFeed";
import { FitChart } from "./FitChart";
import { NextActions } from "./NextActions";
import { StatCards } from "./StatCards";

// "Where am I and what's next" in five seconds (PRD-V2 §4.3). Current numbers (fit, verified,
// checked counts) read live off the shared AnalysisContext — the same context /roadmap and
// /skills use — so they're never stale. History (the chart, deltas, activity feed) reads off
// lib/eventLog.ts, seeded once from the fixture and grown by real ticks/submissions since.
export function DashboardPage() {
  const { data, loading, roleFit, checkedIds, verifiedIds } = useAnalysis();
  const [seeded, setSeeded] = useState(false);
  const user = getUser();

  useEffect(() => {
    let cancelled = false;
    getDashboard().then((res) => {
      if (!cancelled) {
        seedIfEmpty(res);
        setSeeded(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const coreRoles = useMemo(() => (data ? data.roles.filter((r) => r.proximity === "core") : []), [data]);
  const top3 = useMemo(
    () => [...coreRoles].sort((a, b) => (roleFit.get(b.id) ?? 0) - (roleFit.get(a.id) ?? 0)).slice(0, 3),
    [coreRoles, roleFit],
  );
  const skillsById = useMemo(() => new Map((data?.skills ?? []).map((s) => [s.id, s])), [data]);

  const baseline = getDashboardBaseline();
  const recentSimEvents = seeded ? getEventsSince(baseline) : [];
  const verifiedDelta = recentSimEvents.filter((e) => e.type === "pass").length;
  const checkedDelta =
    recentSimEvents.filter((e) => e.type === "tick").length -
    recentSimEvents.filter((e) => e.type === "untick").length;

  const snapshots = seeded ? getSnapshotsForRoles(top3.map((r) => r.id)) : {};
  const series = top3.map((r) => ({ roleId: r.id, title: r.title, points: snapshots[r.id] ?? [] }));

  const activity = seeded ? getRecentEvents(10).map((e) => ({ text: humanize(e), at: e.at })) : [];

  const nextActions = top3.map((role) => {
    const unresolved = [...role.skills]
      .sort((a, b) => (a.weight === b.weight ? 0 : a.weight === "core" ? -1 : 1))
      .find((rs) => {
        const skill = skillsById.get(rs.skill_id);
        if (!skill) return false;
        const covered =
          checkedIds.has(rs.skill_id) || verifiedIds.has(rs.skill_id) || skill.coverage_depth != null;
        return !covered;
      });
    const skillName = unresolved ? skillsById.get(unresolved.skill_id)?.name : null;
    return {
      roleId: role.id,
      slug: role.slug,
      roleTitle: role.title,
      label: skillName ? `Learn ${skillName}` : `Review ${role.title}`,
    };
  });

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 p-8">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const topRole = top3[0] ? { title: top3[0].title, fit: roleFit.get(top3[0].id) ?? 0 } : null;

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8">
      <header>
        <h1 className="font-display text-heading">Welcome back, {user?.name ?? data.student.name}</h1>
        <p className="text-base text-muted-foreground">Here's where you stand.</p>
      </header>

      <StatCards
        topRole={topRole}
        skillsVerified={verifiedIds.size}
        verifiedDelta={verifiedDelta}
        skillsChecked={checkedIds.size}
        checkedDelta={checkedDelta}
      />

      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Progress</h2>
        <FitChart series={series} />
      </section>

      <NextActions actions={nextActions} />

      <ActivityFeed events={activity} />
    </div>
  );
}
