import { AnalysisProvider, useAnalysis } from "./AnalysisContext";
import { RoleCard } from "./RoleCard";

// Day 1 harness: flat list, no two-column layout, no re-sort container yet (Day 2),
// no drawer yet (Day 3). Verifies fixtures + context + FitRing + RoleCard render correctly.
function RoadmapContent() {
  const { data, loading, error, roleFit } = useAnalysis();

  if (loading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (error) return <div className="p-8 text-anchor-critical">{error}</div>;
  if (!data) return null;

  const skillsById = new Map(data.skills.map((s) => [s.id, s]));

  return (
    <div className="mx-auto max-w-2xl space-y-3 p-8">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">
          {data.student.name} · Semester {data.student.semester}
        </h1>
        <p className="text-sm text-muted-foreground">{data.student.interests.join(" · ")}</p>
      </header>
      {data.roles.map((role) => (
        <RoleCard key={role.id} role={role} fit={roleFit.get(role.id) ?? 0} skillsById={skillsById} />
      ))}
    </div>
  );
}

// AnalysisProvider is scoped here for now; Day 5 wiring may lift it to the /roadmap
// route element in router.tsx/App.tsx instead (per anchor-frontend skill — it should
// not wrap Setup/Analyzing, which need no shared context).
export function RoadmapPage() {
  return (
    <AnalysisProvider>
      <RoadmapContent />
    </AnalysisProvider>
  );
}
