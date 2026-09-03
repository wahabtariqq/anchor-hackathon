import { Card, CardContent } from "@/components/ui/card";

interface StatCardsProps {
  topRole: { title: string; fit: number } | null;
  skillsVerified: number;
  verifiedDelta: number;
  skillsChecked: number;
  checkedDelta: number;
}

function Delta({ value }: { value: number }) {
  if (value === 0) return <span className="text-sm text-muted-foreground">No change since last visit</span>;
  const positive = value > 0;
  return (
    <span className={`text-sm ${positive ? "text-anchor-good" : "text-muted-foreground"}`}>
      {positive ? "+" : ""}
      {value} since last visit
    </span>
  );
}

// "Where am I" — PRD-V2 §4.3.1. Numbers get the display face and the size; labels recede
// (anchor-design §3: "Numbers are the heroes").
export function StatCards({ topRole, skillsVerified, verifiedDelta, skillsChecked, checkedDelta }: StatCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Top role fit</p>
          <p className="font-display text-display">{topRole ? `${topRole.fit}%` : "—"}</p>
          <p className="mt-1 truncate text-sm text-muted-foreground">
            {topRole?.title ?? "Complete your analysis"}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Skills verified</p>
          <p className="font-display text-display">{skillsVerified}</p>
          <div className="mt-1">
            <Delta value={verifiedDelta} />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Skills self-reported</p>
          <p className="font-display text-display">{skillsChecked}</p>
          <div className="mt-1">
            <Delta value={checkedDelta} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
