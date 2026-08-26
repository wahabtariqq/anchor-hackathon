import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { CatalogCourse, SemesterTag } from "@/lib/types";

/** null override = not pasting. "" = the textarea is open but empty, which resolves to the catalog text. */
export interface CourseSelection {
  semester_tag: SemesterTag;
  override: string | null;
}

interface CourseCardProps {
  course: CatalogCourse;
  selection: CourseSelection | null;
  /** true when the 6-course maximum is reached and this card is not one of them */
  disabled: boolean;
  onToggle: () => void;
  onTagChange: (tag: SemesterTag) => void;
  onOverrideChange: (override: string | null) => void;
}

const TAGS: { value: SemesterTag; label: string }[] = [
  { value: "past", label: "Previous" },
  { value: "current", label: "Current" },
];

export function CourseCard({
  course,
  selection,
  disabled,
  onToggle,
  onTagChange,
  onOverrideChange,
}: CourseCardProps) {
  const selected = selection !== null;
  const overrideId = `override-${course.id}`;

  return (
    <Card
      role="checkbox"
      aria-checked={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onToggle()}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onToggle();
        }
      }}
      className={cn(
        "cursor-pointer transition-colors",
        selected ? "border-foreground/40 bg-accent/40" : "hover:border-foreground/20",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <CardContent className="space-y-2 p-4">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="text-base font-semibold">{course.name}</h3>
          <span className="shrink-0 text-xs text-muted-foreground">{course.code}</span>
        </div>
        <p className="line-clamp-2 text-sm text-muted-foreground">{course.curriculum_text}</p>

        {selection && (
          // Stop propagation everywhere below: the card itself is the select/deselect target.
          <div className="space-y-2 pt-1" onClick={(event) => event.stopPropagation()}>
            <div className="flex gap-1" role="radiogroup" aria-label={`When did you take ${course.code}?`}>
              {TAGS.map((tag) => (
                <button
                  key={tag.value}
                  type="button"
                  role="radio"
                  aria-checked={selection.semester_tag === tag.value}
                  onClick={() => onTagChange(tag.value)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-xs font-medium transition-colors",
                    selection.semester_tag === tag.value
                      ? "border-foreground/40 bg-background"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  {tag.label}
                </button>
              ))}
            </div>

            {selection.override === null ? (
              <button
                type="button"
                onClick={() => onOverrideChange("")}
                className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
              >
                My syllabus is different — paste it
              </button>
            ) : (
              <div className="space-y-1">
                <Label htmlFor={overrideId} className="text-xs text-muted-foreground">
                  Your outline for {course.code}
                </Label>
                <Textarea
                  id={overrideId}
                  autoFocus
                  rows={4}
                  value={selection.override}
                  placeholder="Paste the topics your course actually covers…"
                  onChange={(event) => onOverrideChange(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => onOverrideChange(null)}
                  className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
                >
                  Use the standard outline instead
                </button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
