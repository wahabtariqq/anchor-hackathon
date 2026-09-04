import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { SubmissionOut } from "@/lib/types";

function formatDate(at: string): string {
  return new Date(at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function SubmissionRow({ submission }: { submission: SubmissionOut }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-token-md border p-3">
      <CollapsibleTrigger asChild>
        <button type="button" className="flex w-full items-center justify-between gap-3 text-left text-sm">
          <span className="min-w-0 truncate text-muted-foreground">{submission.repo_url}</span>
          <span className="flex shrink-0 items-center gap-2">
            <span className="font-medium">
              {submission.total}/{submission.max_total}
            </span>
            <Badge
              variant="outline"
              className={
                submission.passed
                  ? "border-anchor-good/40 bg-anchor-good/10 text-anchor-good"
                  : "text-muted-foreground"
              }
            >
              {submission.passed ? "Passed" : "Not yet"}
            </Badge>
            <span className="text-xs text-muted-foreground">{formatDate(submission.created_at)}</span>
            <ChevronDown className={cn("h-4 w-4 transition-transform motion-reduce:transition-none", open && "rotate-180")} />
          </span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-3 space-y-2">
        {submission.criteria_scores.map((c) => (
          <div key={c.criterion} className="text-sm">
            <div className="flex items-baseline gap-2">
              <Badge variant="outline" className="shrink-0 text-xs font-normal">
                {c.score}/2
              </Badge>
              <span className="font-medium">{c.criterion}</span>
            </div>
            <p className="pl-1 text-muted-foreground">{c.note}</p>
          </div>
        ))}
        <p className="text-base text-muted-foreground">{submission.feedback}</p>
        <p className="text-xs italic text-muted-foreground">Reviewed by reading the repo — nothing was run.</p>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function SubmissionHistory({ submissions }: { submissions: SubmissionOut[] }) {
  if (submissions.length === 0) {
    return <p className="text-sm text-muted-foreground">No submissions yet.</p>;
  }
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Submissions ({submissions.length})
      </h3>
      <div className="space-y-2">
        {submissions.map((s) => (
          <SubmissionRow key={s.id} submission={s} />
        ))}
      </div>
    </div>
  );
}
