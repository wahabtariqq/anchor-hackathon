import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";

interface NextActionItem {
  roleId: string;
  slug: string;
  roleTitle: string;
  label: string;
}

// Same categorical palette FitChart.tsx uses for these same three roles (dataviz skill,
// slots 1-3: blue/orange/aqua) — reusing it by index here, rather than a second invented
// scheme, links each task card back to its line in the chart directly above it.
const COLORS = ["#3987e5", "#d95926", "#199e70"];

// "What now" — PRD-V2 §4.3.3. Deep-links into the roadmap drawer for the role, reusing the
// existing ?role= convenience (RoadmapPage's own read/write effect) rather than any new state.
export function NextActions({ actions }: { actions: NextActionItem[] }) {
  if (actions.length === 0) return null;
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">What now</h2>
      <div className="grid grid-cols-3 gap-3">
        {actions.map((a, i) => {
          const color = COLORS[i % COLORS.length];
          return (
            <Link key={a.roleId} to={`/roadmap?role=${a.slug}`} className="group block h-full">
              <Card className="relative h-full overflow-hidden transition-colors hover:border-foreground/30 motion-reduce:transition-none">
                <div className="absolute inset-y-0 left-0 w-1" style={{ background: color }} aria-hidden />
                <CardContent className="flex items-start justify-between gap-2 py-4 pl-5 pr-4">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold uppercase tracking-wide" style={{ color }}>
                      {a.roleTitle}
                    </p>
                    <p className="mt-1 text-sm font-medium leading-snug">{a.label}</p>
                  </div>
                  <ArrowUpRight
                    className="h-4 w-4 shrink-0 text-muted-foreground transition-transform motion-reduce:transition-none group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
                    aria-hidden
                  />
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
