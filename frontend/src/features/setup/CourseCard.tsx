import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { CatalogCourse, SemesterTag } from "@/lib/types";

export const DEFAULT_OUTLINE = "default";
export const CUSTOM_OUTLINE = "custom";

export interface CourseSelection {
  semester_tag: SemesterTag;
  /** DEFAULT_OUTLINE | CUSTOM_OUTLINE | one of course.curriculum_variants[].id */
  outline: string;
  /** only meaningful when outline === CUSTOM_OUTLINE */
  customText: string;
}

interface CourseCardProps {
  course: CatalogCourse;
  selection: CourseSelection | null;
  /** true when the 6-course maximum is reached and this card is not one of them */
  disabled: boolean;
  onToggle: () => void;
  onTagChange: (tag: SemesterTag) => void;
  onOutlineChange: (outline: string) => void;
  onCustomTextChange: (text: string) => void;
}

const TAGS: { value: SemesterTag; label: string }[] = [
  { value: "past", label: "Previous" },
  { value: "current", label: "Current" },
];

function OutlineOption({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={cn(
        "rounded-md border px-2 py-1 text-xs font-medium transition-colors",
        active
          ? "border-primary/50 bg-primary/10 text-foreground"
          : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

export function CourseCard({
  course,
  selection,
  disabled,
  onToggle,
  onTagChange,
  onOutlineChange,
  onCustomTextChange,
}: CourseCardProps) {
  const selected = selection !== null;
  const [previewOpen, setPreviewOpen] = useState(false);
  const customId = `custom-${course.id}`;
  const variants = course.curriculum_variants ?? [];

  const resolvedText =
    !selection || selection.outline === DEFAULT_OUTLINE
      ? course.curriculum_text
      : selection.outline === CUSTOM_OUTLINE
        ? null
        : (variants.find((v) => v.id === selection.outline)?.text ?? course.curriculum_text);

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
        selected ? "border-primary/50 bg-primary/[0.06]" : "hover:border-foreground/20",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <CardContent className="space-y-2 p-4">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="text-base font-semibold">{course.name}</h3>
          <span className="shrink-0 text-xs text-muted-foreground">{course.code}</span>
        </div>
        <p className="line-clamp-2 text-base text-muted-foreground">{course.curriculum_text}</p>

        {/* The full default outline, viewable on demand whether or not the course is picked
            yet — not just a two-line preview. */}
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setPreviewOpen((v) => !v);
          }}
          className="flex items-center gap-1 text-xs font-medium text-primary underline-offset-2 hover:underline"
        >
          {previewOpen ? "Hide full outline" : "Read full outline"}
          <ChevronDown className={cn("h-3 w-3 transition-transform", previewOpen && "rotate-180")} />
        </button>
        {previewOpen && (
          <p
            onClick={(event) => event.stopPropagation()}
            className="max-h-40 overflow-y-auto rounded-md border bg-background/60 p-2.5 text-xs leading-relaxed text-muted-foreground"
          >
            {course.curriculum_text}
          </p>
        )}

        {selection && (
          // Stop propagation everywhere below: the card itself is the select/deselect target.
          <div className="space-y-3 pt-1" onClick={(event) => event.stopPropagation()}>
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

            {variants.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Which outline matches what you took?
                </p>
                <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`Outline for ${course.code}`}>
                  <OutlineOption
                    label="Standard"
                    active={selection.outline === DEFAULT_OUTLINE}
                    onClick={() => onOutlineChange(DEFAULT_OUTLINE)}
                  />
                  {variants.map((v) => (
                    <OutlineOption
                      key={v.id}
                      label={v.label}
                      active={selection.outline === v.id}
                      onClick={() => onOutlineChange(v.id)}
                    />
                  ))}
                  <OutlineOption
                    label="Write my own"
                    active={selection.outline === CUSTOM_OUTLINE}
                    onClick={() => onOutlineChange(CUSTOM_OUTLINE)}
                  />
                </div>
              </div>
            )}

            {selection.outline === CUSTOM_OUTLINE ? (
              <div className="space-y-1">
                <Label htmlFor={customId} className="text-xs text-muted-foreground">
                  Your outline for {course.code}
                </Label>
                <Textarea
                  id={customId}
                  autoFocus
                  rows={4}
                  value={selection.customText}
                  placeholder="Paste the topics your course actually covers…"
                  onChange={(event) => onCustomTextChange(event.target.value)}
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                {variants.length === 0 && (
                  <button
                    type="button"
                    onClick={() => onOutlineChange(CUSTOM_OUTLINE)}
                    className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
                  >
                    My syllabus is different — write my own
                  </button>
                )}
                <p className="max-h-32 overflow-y-auto rounded-md border bg-background/60 p-2.5 text-xs leading-relaxed text-muted-foreground">
                  {resolvedText}
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
