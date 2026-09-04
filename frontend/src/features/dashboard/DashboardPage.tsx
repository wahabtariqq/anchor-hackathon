import { useEffect, useMemo, useState } from "react";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { Skeleton } from "@/components/ui/skeleton";
import { getDashboard } from "@/lib/api";
import { getUser } from "@/lib/auth";
import type { DashboardResponse } from "@/lib/types";
import { ActivityFeed } from "./ActivityFeed";
import { FitChart } from "./FitChart";
import { NextActions } from "./NextActions";
import { StatCards } from "./StatCards";

// "Where am I and what's next" in five seconds (PRD-V2 §4.3).
//
// Two sources, deliberately: current numbers (top-role fit, verified/checked counts) read live
// off the shared AnalysisContext — the same context /roadmap and /skills use — so a tick made a
// second ago is already reflected without a refetch. History (the chart, the deltas, the
// activity feed, the next actions) comes from GET /api/dashboard, because none of it is
// derivable from the roadmap payload: it lives in the `event` and `fit_snapshot` tables
// (docs/TDD-V2.md §4.6).
const EMPTY: DashboardResponse = {
  top_role: null,
  skills_verified: 0,
  skills_checked: 0,
  verified_delta: 0,
  checked_delta: 0,
  snapshots: {},
  next_actions: [],
  recent_events: [],
};

export function DashboardPage() {
  const { data, loading, roleFit, checkedIds, verifiedIds } = useAnalysis();
  const [dash, setDash] = useState<DashboardResponse | null>(null);
  const user = getUser();

  useEffect(() => {
    let cancelled = false;
    getDashboard()
      .then((res) => {
        if (!cancelled) setDash(res);
      })
      // History failing must not blank the page — the live numbers above still stand on their
      // own, so fall back to an empty history rather than an error screen.
      .catch(() => {
        if (!cancelled) setDash(EMPTY);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const roleById = useMemo(() => new Map((data?.roles ?? []).map((r) => [r.id, r])), [data]);

  // next_actions and snapshots are both built server-side from the same top-3 list, in the same
  // order, so walking next_actions keeps FitChart's COLORS[i] and NextActions' COLORS[i] on the
  // same role — which is exactly what DECISIONS #90 ties together.
  const charted = (dash ?? EMPTY).next_actions.filter((a) => roleById.has(a.role_id));

  const series = charted.map((a) => ({
    roleId: a.role_id,
    title: roleById.get(a.role_id)!.title,
    points: (dash ?? EMPTY).snapshots[a.role_id] ?? [],
  }));

  const nextActions = charted.map((a) => ({
    roleId: a.role_id,
    slug: roleById.get(a.role_id)!.slug,
    roleTitle: roleById.get(a.role_id)!.title,
    label: a.label,
  }));

  if (loading || !data || !dash) {
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

  // Live ordering, not the payload's: if a tick just changed which role leads, the greeting's
  // headline number has to agree with what /roadmap would show right now.
  const best = [...data.roles]
    .filter((r) => r.proximity === "core")
    .sort((a, b) => (roleFit.get(b.id) ?? 0) - (roleFit.get(a.id) ?? 0))[0];
  const topRole = best ? { title: best.title, fit: roleFit.get(best.id) ?? 0 } : null;

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8">
      <header>
        <h1 className="font-display text-heading">Welcome back, {user?.name ?? data.student.name}</h1>
        <p className="text-base text-muted-foreground">Here's where you stand.</p>
      </header>

      <StatCards
        topRole={topRole}
        skillsVerified={verifiedIds.size}
        verifiedDelta={dash.verified_delta}
        skillsChecked={checkedIds.size}
        checkedDelta={dash.checked_delta}
      />

      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Progress</h2>
        <FitChart series={series} />
      </section>

      <NextActions actions={nextActions} />

      <ActivityFeed events={dash.recent_events} />
    </div>
  );
}
