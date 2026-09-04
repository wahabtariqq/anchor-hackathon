import { Check } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface CourseTileProps {
  title: string;
  /** Catalog code ("CS301") or "Custom" for a course the student added themselves — both render
   *  the same way, so custom courses sit in this grid exactly like catalog ones. */
  code: string;
  /** Full catalog description. Not shown on the tile by default (that's "Click to add") — only
   *  surfaced as a hover tooltip, so an unpicked tile stays a scannable name + code. */
  blurb: string;
  selected: boolean;
  /** One line describing the saved configuration ("Previous semester · Standard outline"),
   *  shown once the course is picked, replacing "Click to add" — the tile doubles as a
   *  quick-glance summary so re-opening the dialog to check "what did I pick" isn't necessary. */
  summary: string | null;
  /** true when the 6-course maximum is reached and this course is not one of the picked ones */
  disabled: boolean;
  /** Always opens a detail dialog (CourseDetailModal for catalog courses, CustomCourseModal for
   *  added ones) — picking, editing, and removing all happen there, not on the tile itself, so
   *  the tile never has to grow or reflow this grid. */
  onOpen: () => void;
}

export function CourseTile({ title, code, blurb, selected, summary, disabled, onOpen }: CourseTileProps) {
  return (
    <Card
      role="button"
      aria-pressed={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onOpen()}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
      // The full description is still available on hover (native title tooltip) — it's just
      // not shown by default, so an unselected tile stays scannable instead of turning the grid
      // into a page of catalog copy.
      title={!selected ? blurb : undefined}
      className={cn(
        "h-full cursor-pointer transition-colors",
        selected ? "border-primary/60 bg-primary/[0.07]" : "hover:border-foreground/25",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <CardContent className="flex h-full flex-col gap-1.5 p-3.5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold leading-tight">{title}</h3>
          <div
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors",
              selected ? "border-primary bg-primary text-primary-foreground" : "border-foreground/25",
            )}
          >
            {selected && <Check className="h-3 w-3" />}
          </div>
        </div>
        <span className="text-xs text-muted-foreground">{code}</span>
        <p
          className={cn(
            "line-clamp-2 text-xs leading-relaxed",
            summary ? "font-medium text-primary" : "text-muted-foreground",
          )}
        >
          {summary ?? "Click to add"}
        </p>
      </CardContent>
    </Card>
  );
}
