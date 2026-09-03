import { useEffect, useMemo, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { clearStudentId } from "@/lib/identity";
import type { RoadmapRole, RoadmapSkill } from "@/lib/types";
import { AnalysisProvider, useAnalysis } from "./AnalysisContext";
import { RoleCard } from "./RoleCard";
import { RoleDrawer } from "./RoleDrawer";
import { WhatMoved } from "./WhatMoved";

// Fixed role-card height, gap included (anchor-design §4). Card content must never
// grow past this — RoleCard truncates its own text; we clip the rest defensively.
const CARD_H = 132;
const CARD_GAP = 12;

function RoadmapContent() {
  const { data, loading, error, checkedIds, verifiedIds, roleFit, openRoleSlug, setOpenRole, toggle } =
    useAnalysis();
  const lastTrigger = useRef<HTMLElement | null>(null);
  // Guards the write-effect below from clearing ?role= before the read-effect has had
  // a chance to hydrate openRoleSlug from it — both effects fire on mount, and without
  // this, the write-effect's first pass (openRoleSlug still null pre-hydration) wipes
  // the query string out from under the read-effect's later, async-gated pass.
  const hydratedFromUrl = useRef(false);

  // data.skills' own checked/verified fields are a load-time snapshot (they only seed
  // checkedIds/verifiedIds in AnalysisContext — see its useEffect). Every row and card
  // that displays a skill's state must read the live sets, not that snapshot, or a tick
  // updates the fit % and re-sort but never flips its own checkbox.
  const skillsById = useMemo(() => {
    const m = new Map<string, RoadmapSkill>();
    if (!data) return m;
    for (const s of data.skills) {
      m.set(s.id, { ...s, checked: checkedIds.has(s.id), verified: verifiedIds.has(s.id) });
    }
    return m;
  }, [data, checkedIds, verifiedIds]);

  // ?role=slug is a reload convenience only (TDD §7.2) — never a navigation, so this
  // reads/writes the URL directly rather than going through a router.
  useEffect(() => {
    if (!data) return;
    const slug = new URLSearchParams(window.location.search).get("role");
    if (slug && data.roles.some((r) => r.slug === slug)) setOpenRole(slug);
    hydratedFromUrl.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  useEffect(() => {
    if (!hydratedFromUrl.current) return;
    const params = new URLSearchParams(window.location.search);
    if (openRoleSlug) params.set("role", openRoleSlug);
    else params.delete("role");
    const search = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${search ? `?${search}` : ""}`);
    if (!openRoleSlug) lastTrigger.current?.focus();
  }, [openRoleSlug]);

  // Stable order: data.roles only changes on initial load, so this iteration order
  // never changes across ticks — required for the translateY re-sort to slide, not snap.
  const coreRoles = useMemo(() => (data ? data.roles.filter((r) => r.proximity === "core") : []), [data]);
  const adjacentRoles = useMemo(
    () => (data ? data.roles.filter((r) => r.proximity === "adjacent") : []),
    [data],
  );

  const ordered = [...coreRoles].sort(
    (a, b) => (roleFit.get(b.id) ?? 0) - (roleFit.get(a.id) ?? 0) || a.rank - b.rank,
  );
  const pos = new Map(ordered.map((r, i) => [r.id, i]));

  function openRole(role: RoadmapRole) {
    // A clicked/keyboard-activated Card is focused by the time its onClick fires, so
    // this captures the actual trigger without RoleCard needing to expose the event.
    lastTrigger.current = document.activeElement as HTMLElement;
    setOpenRole(role.slug);
  }

  if (loading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (error) return <div className="p-8 text-anchor-critical">{error}</div>;
  if (!data) return null;

  const openRole_ = data.roles.find((r) => r.slug === openRoleSlug) ?? null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">
            {data.student.name} · Semester {data.student.semester}
          </h1>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {data.student.interests.map((interest) => (
              <Badge key={interest} variant="outline" className="text-xs font-normal">
                {interest}
              </Badge>
            ))}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            clearStudentId();
            window.location.href = "/setup";
          }}
        >
          Start over
        </Button>
      </header>

      <div className="grid grid-cols-[1fr_28rem] items-start gap-6">
        <div className="space-y-6">
          <section className="space-y-3">
            <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
              Your closest paths
            </h2>
            <div className="relative" style={{ height: coreRoles.length * CARD_H }}>
              {coreRoles.map((role) => (
                <div
                  key={role.id}
                  className="absolute inset-x-0 transition-transform duration-500 ease-out motion-reduce:transition-none"
                  style={{ height: CARD_H - CARD_GAP, transform: `translateY(${(pos.get(role.id) ?? 0) * CARD_H}px)` }}
                >
                  <RoleCard
                    role={role}
                    fit={roleFit.get(role.id) ?? 0}
                    skillsById={skillsById}
                    className="h-full overflow-hidden"
                    onClick={() => openRole(role)}
                  />
                </div>
              ))}
            </div>
            <WhatMoved roles={coreRoles} roleFit={roleFit} pos={pos} />
          </section>

          {adjacentRoles.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
                Worth considering
              </h2>
              <div className="space-y-3">
                {adjacentRoles.map((role) => (
                  <RoleCard
                    key={role.id}
                    role={role}
                    fit={roleFit.get(role.id) ?? 0}
                    skillsById={skillsById}
                    onClick={() => openRole(role)}
                  />
                ))}
              </div>
            </section>
          )}
        </div>

        <div className="sticky top-8" style={{ minHeight: coreRoles.length * CARD_H }}>
          {openRole_ ? (
            <RoleDrawer
              role={openRole_}
              fit={roleFit.get(openRole_.id) ?? 0}
              skillsById={skillsById}
              onToggleSkill={toggle}
              onClose={() => setOpenRole(null)}
            />
          ) : (
            <div className="flex h-full min-h-[200px] items-center justify-center rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              Click a role to see covered and missing skills.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// AnalysisProvider is scoped here for now; per anchor-frontend skill it should not wrap
// Setup/Analyzing, which need no shared context.
export function RoadmapPage() {
  return (
    <AnalysisProvider>
      <RoadmapContent />
    </AnalysisProvider>
  );
}
