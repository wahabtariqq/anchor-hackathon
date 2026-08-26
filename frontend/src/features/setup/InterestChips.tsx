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
    <div className="flex flex-wrap gap-2">
      {INTERESTS.map((interest) => {
        const on = selected.includes(interest);
        return (
          <Badge
            key={interest}
            role="checkbox"
            aria-checked={on}
            tabIndex={0}
            variant={on ? "default" : "outline"}
            onClick={() => onToggle(interest)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onToggle(interest);
              }
            }}
            className={cn(
              "cursor-pointer select-none px-3 py-1 text-xs font-medium",
              !on && "hover:border-foreground/30",
            )}
          >
            {interest}
          </Badge>
        );
      })}
    </div>
  );
}
