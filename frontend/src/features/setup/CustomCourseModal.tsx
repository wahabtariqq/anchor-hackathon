import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { SemesterTag } from "@/lib/types";

const MIN_CUSTOM_CHARS = 50; // mirrors MIN_CUSTOM_CURRICULUM_CHARS in backend/app/schemas.py

export interface CustomCourseDraft {
  name: string;
  /** Student-assigned course number, e.g. "CS499" — display-only, mirrors a catalog course's
   *  code so a custom tile shows something other than a bare "Custom" badge. */
  code: string;
  semester_tag: SemesterTag;
  curriculum_text: string;
}

interface CustomCourseModalProps {
  open: boolean;
  /** null when adding a new course; the course being edited otherwise. */
  existing: CustomCourseDraft | null;
  /** Every already-picked course title, lowercased and trimmed (catalog + other custom courses,
   *  never including the one being edited) — saving a name in this set is blocked so the same
   *  course can't end up picked twice under two different tiles. */
  existingTitles: Set<string>;
  onClose: () => void;
  onSave: (draft: CustomCourseDraft) => void;
  onRemove: () => void;
}

const TAGS: { value: SemesterTag; label: string }[] = [
  { value: "past", label: "Previous semester" },
  { value: "current", label: "Current semester" },
];

const EMPTY: CustomCourseDraft = { name: "", code: "", semester_tag: "current", curriculum_text: "" };

/**
 * The same popup style as CourseDetailModal, for a course that isn't in the catalog at all — a
 * name field stands in for the fixed catalog title, and there's no outline-variant picker since
 * a custom course is, definitionally, "write your own." Opened by the "+ Add a course not
 * listed" button (new) or by clicking the resulting tile again (edit/remove).
 */
export function CustomCourseModal({
  open,
  existing,
  existingTitles,
  onClose,
  onSave,
  onRemove,
}: CustomCourseModalProps) {
  const [draft, setDraft] = useState<CustomCourseDraft>(existing ?? EMPTY);

  useEffect(() => {
    if (open) setDraft(existing ?? EMPTY);
  }, [open, existing]);

  const trimmedName = draft.name.trim();
  const nameValid = trimmedName.length > 0;
  const nameConflict = nameValid && existingTitles.has(trimmedName.toLowerCase());
  const codeValid = draft.code.trim().length > 0;
  const textLen = draft.curriculum_text.trim().length;
  const textValid = textLen >= MIN_CUSTOM_CHARS;
  const canSave = nameValid && !nameConflict && codeValid && textValid;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{existing ? "Edit course" : "Add a course not listed"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="custom-course-name">Course name</Label>
              <Input
                id="custom-course-name"
                autoFocus
                value={draft.name}
                placeholder="e.g. Human-Computer Interaction"
                onChange={(event) => setDraft((d) => ({ ...d, name: event.target.value }))}
              />
              {nameConflict && (
                <p className="text-xs text-anchor-critical">"{trimmedName}" already exists in the options.</p>
              )}
            </div>
            <div className="w-28 shrink-0 space-y-1.5">
              <Label htmlFor="custom-course-code">Course no.</Label>
              <Input
                id="custom-course-code"
                value={draft.code}
                placeholder="e.g. CS499"
                onChange={(event) => setDraft((d) => ({ ...d, code: event.target.value }))}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">When did you take this?</p>
            <div className="flex gap-1.5" role="radiogroup" aria-label="When did you take this course?">
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

          <div className="space-y-1">
            <Label htmlFor="custom-course-outline" className="text-xs text-muted-foreground">
              Outline
            </Label>
            <Textarea
              id="custom-course-outline"
              rows={6}
              value={draft.curriculum_text}
              placeholder="Paste the topics your course actually covers…"
              onChange={(event) => setDraft((d) => ({ ...d, curriculum_text: event.target.value }))}
            />
            {!textValid && (
              <p className="text-xs text-anchor-critical">
                Paste at least {MIN_CUSTOM_CHARS} characters ({textLen} so far).
              </p>
            )}
          </div>
        </div>

        <DialogFooter className="sm:justify-between">
          {existing ? (
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
            <Button disabled={!canSave} onClick={() => onSave(draft)}>
              {existing ? "Save" : "Add course"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
