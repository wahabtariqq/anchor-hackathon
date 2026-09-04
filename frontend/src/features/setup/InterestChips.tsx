import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { INTERESTS, type Interest } from "@/lib/types";

interface InterestChipsProps {
  selected: Interest[];
  onToggle: (interest: Interest) => void;
}

/** The fixed list of 8 (PRD §6.3), multi-select, minimum 2. */
export function InterestChips({ selected, onToggle }: InterestChipsProps) {
  return (
    <div className="flex flex-wrap gap-3">
      {INTERESTS.map((interest) => {
        const on = selected.includes(interest);
        return (
          <Badge
            key={interest}
            role="checkbox"
            aria-checked={on}
            tabIndex={0}
            variant="outline"
            onClick={() => onToggle(interest)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onToggle(interest);
              }
            }}
            className={cn(
              // Badge's base classes put a focus ring on plain :focus, which fires on a mouse
              // click (not just keyboard nav) and reads as a stray white outline. Restrict it to
              // :focus-visible so a mouse click stays clean and Tab navigation still shows one.
              "cursor-pointer select-none px-4 py-2 text-sm font-medium transition-colors",
              "focus:outline-none focus:ring-0 focus:ring-offset-0",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              // Same treatment as a selected CourseTile: a primary-tinted border and wash over
              // the dark surface, not a solid fill — one selected look across the whole flow.
              on ? "border-primary/60 bg-primary/[0.07] text-primary" : "hover:border-foreground/30",
            )}
          >
            {interest}
          </Badge>
        );
      })}
    </div>
  );
}
