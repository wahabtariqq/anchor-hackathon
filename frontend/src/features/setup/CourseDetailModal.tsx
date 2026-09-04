import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { CatalogCourse, SemesterTag } from "@/lib/types";
import { CUSTOM_OUTLINE, DEFAULT_OUTLINE, type CourseSelection } from "./courseSelection";

const MIN_CUSTOM_CHARS = 50; // mirrors MIN_CUSTOM_CURRICULUM_CHARS in backend/app/schemas.py

interface CourseDetailModalProps {
  /** null closes the dialog. */
  course: CatalogCourse | null;
  /** null means this course isn't picked yet — the dialog offers "Add course" instead of
   *  "Save" / "Remove". */
  existingSelection: CourseSelection | null;
  onClose: () => void;
  onSave: (selection: CourseSelection) => void;
  onRemove: () => void;
}

const TAGS: { value: SemesterTag; label: string }[] = [
  { value: "past", label: "Previous semester" },
  { value: "current", label: "Current semester" },
];

function PillOption({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={cn(
        "rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors",
        active
          ? "border-primary/50 bg-primary/10 text-foreground"
          : "border-transparent bg-background/60 text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

const EMPTY: CourseSelection = { semester_tag: "past", outline: DEFAULT_OUTLINE, customText: "" };

/**
 * Everything about one course — the full outline, when you took it, which variant (or your own
 * write-up) — lives in one floating dialog instead of a grid cell or a list row. A dialog can be
 * as tall as it needs to be without ever fighting a sibling tile for space, which is the whole
 * reason this replaced inline expansion (direct feedback: clicking a tile should open a popup).
 *
 * Draft state is local and only committed via onSave — closing without saving discards it, so a
 * student can explore "Write my own" and back out without losing whatever was there before.
 */
export function CourseDetailModal({ course, existingSelection, onClose, onSave, onRemove }: CourseDetailModalProps) {
  const [draft, setDraft] = useState<CourseSelection>(existingSelection ?? EMPTY);

  // Re-seed the draft whenever a different course opens (or the same one reopens with a fresh
  // saved selection) — never carry stale edits from the last course into this one.
  useEffect(() => {
    setDraft(existingSelection ?? EMPTY);
  }, [course?.id, existingSelection]);

  const variants = course?.curriculum_variants ?? [];
  const resolvedText =
    draft.outline === DEFAULT_OUTLINE
      ? course?.curriculum_text
      : draft.outline === CUSTOM_OUTLINE
        ? null
        : (variants.find((v) => v.id === draft.outline)?.text ?? course?.curriculum_text);

  const customTooShort = draft.outline === CUSTOM_OUTLINE && draft.customText.trim().length < MIN_CUSTOM_CHARS;

  return (
    <Dialog open={course !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-xl">
        {course && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-baseline gap-2">
                {course.name}
                <span className="text-sm font-normal text-muted-foreground">{course.code}</span>
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">When did you take this?</p>
                <div className="flex gap-1.5" role="radiogroup" aria-label={`When did you take ${course.code}?`}>
                  {TAGS.map((tag) => (
                    <button
                      key={tag.value}
                      type="button"
                      role="radio"
                      aria-checked={draft.semester_tag === tag.value}
                      onClick={() => setDraft((d) => ({ ...d, semester_tag: tag.value }))}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                        draft.semester_tag === tag.value
                          ? "border-primary/50 bg-primary/10 text-foreground"
                          : "border-transparent bg-background/60 text-muted-foreground hover:bg-accent hover:text-foreground",
                      )}
                    >
                      {tag.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">Outline</p>
                <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`Outline for ${course.code}`}>
                  <PillOption
                    label="Standard"
                    active={draft.outline === DEFAULT_OUTLINE}
                    onClick={() => setDraft((d) => ({ ...d, outline: DEFAULT_OUTLINE }))}
                  />
                  {variants.map((v) => (
                    <PillOption
                      key={v.id}
                      label={v.label}
                      active={draft.outline === v.id}
                      onClick={() => setDraft((d) => ({ ...d, outline: v.id }))}
                    />
                  ))}
                  <PillOption
                    label="Write my own"
                    active={draft.outline === CUSTOM_OUTLINE}
                    onClick={() => setDraft((d) => ({ ...d, outline: CUSTOM_OUTLINE }))}
                  />
                </div>

                {draft.outline === CUSTOM_OUTLINE ? (
                  <div className="space-y-1 pt-1.5">
                    <Label htmlFor="custom-outline" className="text-xs text-muted-foreground">
                      Your outline for {course.code}
                    </Label>
                    <Textarea
                      id="custom-outline"
                      autoFocus
                      rows={6}
                      value={draft.customText}
                      placeholder="Paste the topics your course actually covers…"
                      onChange={(event) => setDraft((d) => ({ ...d, customText: event.target.value }))}
                    />
                    {customTooShort && (
                      <p className="text-xs text-anchor-critical">
                        Paste at least {MIN_CUSTOM_CHARS} characters ({draft.customText.trim().length} so far).
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="mt-1.5 max-h-56 overflow-y-auto rounded-md border bg-background/60 p-3 text-sm leading-relaxed text-muted-foreground">
                    {resolvedText}
                  </p>
                )}
              </div>
            </div>

            <DialogFooter className="sm:justify-between">
              {existingSelection ? (
                <Button variant="destructive" onClick={onRemove}>
                  Remove course
                </Button>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button disabled={customTooShort} onClick={() => onSave(draft)}>
                  {existingSelection ? "Save" : "Add course"}
                </Button>
              </div>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
