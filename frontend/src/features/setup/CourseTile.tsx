import { Check } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { CatalogCourse } from "@/lib/types";

interface CourseTileProps {
  course: CatalogCourse;
  selected: boolean;
  /** One line describing the saved configuration ("Previous semester · Standard outline"),
   *  shown in place of the catalog blurb once the course is picked — the tile doubles as a
   *  quick-glance summary so re-opening the dialog to check "what did I pick" isn't necessary. */
  summary: string | null;
  /** true when the 6-course maximum is reached and this course is not one of the picked ones */
  disabled: boolean;
  /** Always opens CourseDetailModal — picking, editing, and removing all happen there now, not
   *  on the tile itself, so the tile never has to grow or reflow this grid. */
  onOpen: () => void;
}

export function CourseTile({ course, selected, summary, disabled, onOpen }: CourseTileProps) {
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
      className={cn(
        "h-full cursor-pointer transition-colors",
        selected ? "border-primary/60 bg-primary/[0.07]" : "hover:border-foreground/25",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <CardContent className="flex h-full flex-col gap-1.5 p-3.5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold leading-tight">{course.name}</h3>
          <div
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors",
              selected ? "border-primary bg-primary text-primary-foreground" : "border-foreground/25",
            )}
          >
            {selected && <Check className="h-3 w-3" />}
          </div>
        </div>
        <span className="text-xs text-muted-foreground">{course.code}</span>
        <p
          className={cn(
            "line-clamp-2 text-xs leading-relaxed",
            summary ? "font-medium text-primary" : "text-muted-foreground",
          )}
        >
          {summary ?? course.curriculum_text}
        </p>
      </CardContent>
    </Card>
  );
}
