import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";

interface NextActionItem {
  roleId: string;
  slug: string;
  label: string;
}

// "What now" — PRD-V2 §4.3.3. Deep-links into the roadmap drawer for the role, reusing the
// existing ?role= convenience (RoadmapPage's own read/write effect) rather than any new state.
export function NextActions({ actions }: { actions: NextActionItem[] }) {
  if (actions.length === 0) return null;
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">What now</h2>
      <div className="grid grid-cols-3 gap-3">
        {actions.map((a) => (
          <Link key={a.roleId} to={`/roadmap?role=${a.slug}`}>
            <Card className="h-full transition-colors hover:border-foreground/20 motion-reduce:transition-none">
              <CardContent className="p-4 text-sm font-medium">{a.label}</CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
