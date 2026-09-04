import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { createStudent, getCourses } from "@/lib/api";
import { getUser } from "@/lib/auth";
import { setStudentId, setStudentName } from "@/lib/identity";
import type {
  CatalogCourse,
  Interest,
  SemesterTag,
  StudentCourseInput,
} from "@/lib/types";
import { CourseDetailModal } from "./CourseDetailModal";
import { CourseTile } from "./CourseTile";
import { CUSTOM_OUTLINE, DEFAULT_OUTLINE, type CourseSelection } from "./courseSelection";
import { CustomCourseModal, type CustomCourseDraft } from "./CustomCourseModal";
import { InterestChips } from "./InterestChips";

const MIN_COURSES = 3;
const MAX_COURSES = 6;
const MIN_INTERESTS = 2;
const MIN_CUSTOM_CHARS = 50; // mirrors MIN_CUSTOM_CURRICULUM_CHARS in backend/app/schemas.py

interface CustomCourse {
  key: number;
  name: string;
  /** A student-assigned course number ("CS499"), display-only — the backend's StudentCourseInput
   *  has no field for it (only custom_name/semester_tag/curriculum_text), so it never leaves the
   *  browser. It exists so a custom-course tile shows something other than a bare "Custom" badge. */
  code: string;
  semester_tag: SemesterTag;
  curriculum_text: string;
}

interface SetupPageProps {
  /** Which half of the form is showing — courses+semester, or interests. Courses and Interests
   *  are real, separate steps (OnboardingRoute owns which one); this component just renders the
   *  half asked for, over state that persists across both since it's the same component
   *  instance either way. */
  step: "courses" | "interests";
  onContinue: () => void;
  onBack: () => void;
  /** Called with the new student id once it is stored — fires from the interests step's
   *  "Analyze my path" button. */
  onComplete?: (studentId: string) => void;
}

function resolveOverride(course: CatalogCourse, selection: CourseSelection): string | undefined {
  if (selection.outline === DEFAULT_OUTLINE) return undefined;
  if (selection.outline === CUSTOM_OUTLINE) return selection.customText.trim() || undefined;
  return course.curriculum_variants?.find((v) => v.id === selection.outline)?.text;
}

export function SetupPage({ step, onContinue, onBack, onComplete }: SetupPageProps) {
  const [catalog, setCatalog] = useState<CatalogCourse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [semester, setSemester] = useState("4");
  const [selections, setSelections] = useState<Record<string, CourseSelection>>({});
  const [customCourses, setCustomCourses] = useState<CustomCourse[]>([]);
  const [interests, setInterests] = useState<Interest[]>([]);
  /** Which catalog course's detail dialog is open — null when closed. Picking, editing outline/
   *  semester, and removing a catalog course all happen in CourseDetailModal now, not inline. */
  const [openCourseId, setOpenCourseId] = useState<string | null>(null);
  /** Which custom course's dialog is open — a key edits that one, "new" creates one, null closes.
   *  Same popup style and the same tile-grid placement as catalog courses (direct feedback). */
  const [customModalTarget, setCustomModalTarget] = useState<number | "new" | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    getCourses()
      .then((res) => !cancelled && setCatalog(res.courses))
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "Could not load courses");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const selectedIds = Object.keys(selections);
  const courseCount = selectedIds.length + customCourses.length;
  const atLimit = courseCount >= MAX_COURSES;

  const semesterNumber = Number(semester);
  const semesterValid = Number.isInteger(semesterNumber) && semesterNumber >= 1 && semesterNumber <= 8;

  const customErrors = customCourses.map((course) => {
    if (!course.name.trim()) return "Give the course a name.";
    if (!course.code.trim()) return "Give the course a number.";
    if (course.curriculum_text.trim().length < MIN_CUSTOM_CHARS) {
      return `Paste at least ${MIN_CUSTOM_CHARS} characters of outline (${course.curriculum_text.trim().length} so far).`;
    }
    return null;
  });

  // A catalog course with "Write my own" picked needs the same minimum as a fully custom course
  // — a near-empty override would otherwise reach the analysis call unvalidated.
  const outlineErrors = (catalog ?? [])
    .filter((c) => selections[c.id]?.outline === CUSTOM_OUTLINE)
    .map((c) => {
      const len = selections[c.id].customText.trim().length;
      return len < MIN_CUSTOM_CHARS ? `${c.code}: paste at least ${MIN_CUSTOM_CHARS} characters (${len} so far).` : null;
    })
    .filter((m): m is string => Boolean(m));

  const problems = {
    semester: semesterValid ? null : "Semester must be a number between 1 and 8.",
    courses:
      courseCount < MIN_COURSES
        ? `Pick at least ${MIN_COURSES} courses (${courseCount} so far).`
        : null,
    custom: customErrors.some(Boolean) ? "One of your added courses is missing an outline — reopen it to finish." : null,
    outline: outlineErrors.length > 0 ? outlineErrors[0] : null,
    interests:
      interests.length < MIN_INTERESTS
        ? `Pick at least ${MIN_INTERESTS} interests (${interests.length} so far).`
        : null,
  };
  const coursesReady = !problems.semester && !problems.courses && !problems.custom && !problems.outline;
  const ready = coursesReady && !problems.interests;

  function saveCourseSelection(courseId: string, selection: CourseSelection) {
    setSelections((prev) => ({ ...prev, [courseId]: selection }));
    setOpenCourseId(null);
  }

  function removeCourseSelection(courseId: string) {
    setSelections((prev) => {
      const next = { ...prev };
      delete next[courseId];
      return next;
    });
    setOpenCourseId(null);
  }

  function summaryFor(course: CatalogCourse): string | null {
    const selection = selections[course.id];
    if (!selection) return null;
    const when = selection.semester_tag === "past" ? "Previous semester" : "Current semester";
    const outline =
      selection.outline === DEFAULT_OUTLINE
        ? "Standard outline"
        : selection.outline === CUSTOM_OUTLINE
          ? "Your own outline"
          : (course.curriculum_variants?.find((v) => v.id === selection.outline)?.label ?? "Standard outline");
    return `${when} · ${outline}`;
  }

  function toggleInterest(interest: Interest) {
    setInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest],
    );
  }

  const editingCustomCourse =
    typeof customModalTarget === "number"
      ? (customCourses.find((c) => c.key === customModalTarget) ?? null)
      : null;

  // Every course title that already exists — the *whole* catalog (picked or not: a custom course
  // must never recreate a real catalog course just because it isn't ticked yet) plus every other
  // custom course, minus whichever one is currently being edited. CustomCourseModal blocks saving
  // a name that collides with one of these, case-insensitively.
  const pickedTitles = useMemo(() => {
    const catalogNames = (catalog ?? []).map((c) => c.name.trim().toLowerCase());
    const customNames = customCourses
      .filter((c) => c.key !== customModalTarget)
      .map((c) => c.name.trim().toLowerCase());
    return new Set([...catalogNames, ...customNames]);
  }, [catalog, customCourses, customModalTarget]);

  function saveCustomCourse(draft: CustomCourseDraft) {
    if (typeof customModalTarget === "number") {
      setCustomCourses((prev) => prev.map((c) => (c.key === customModalTarget ? { ...c, ...draft } : c)));
    } else {
      setCustomCourses((prev) => [...prev, { key: Date.now() + prev.length, ...draft }]);
    }
    setCustomModalTarget(null);
  }

  function removeCustomCourse() {
    if (typeof customModalTarget === "number") {
      setCustomCourses((prev) => prev.filter((c) => c.key !== customModalTarget));
    }
    setCustomModalTarget(null);
  }

  function handleContinue() {
    setShowErrors(true);
    if (!coursesReady) return;
    setShowErrors(false);
    onContinue();
  }

  async function submit() {
    setShowErrors(true);
    if (!ready || submitting) return;

    const courses: StudentCourseInput[] = [
      ...(catalog ?? [])
        .filter((course) => selections[course.id])
        .map((course) => {
          const selection = selections[course.id];
          const override = resolveOverride(course, selection);
          return {
            course_id: course.id,
            semester_tag: selection.semester_tag,
            ...(override ? { curriculum_override: override } : {}),
          };
        }),
      ...customCourses.map((course) => ({
        custom_name: course.name.trim(),
        semester_tag: course.semester_tag,
        curriculum_text: course.curriculum_text.trim(),
      })),
    ];

    setSubmitting(true);
    setSubmitError(null);
    try {
      const { student_id } = await createStudent({
        name: getUser()?.name ?? "",
        semester: semesterNumber,
        interests,
        courses,
      });
      setStudentId(student_id);
      const accountName = getUser()?.name;
      if (accountName) setStudentName(accountName);
      onComplete?.(student_id);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Could not start the analysis");
    } finally {
      setSubmitting(false);
    }
  }

  if (step === "interests") {
    return (
      <div className="mx-auto max-w-4xl space-y-6 p-8">
        <header className="space-y-1">
          <h1 className="text-3xl font-semibold">What are you into?</h1>
          <p className="text-base text-muted-foreground">
            Pick at least two — this steers which of the eight roles float to the top.
          </p>
        </header>

        <section className="space-y-3">
          <InterestChips selected={interests} onToggle={toggleInterest} />
          {showErrors && problems.interests && (
            <p className="text-xs text-anchor-critical">{problems.interests}</p>
          )}
        </section>

        <Separator />

        <section className="flex items-center justify-between">
          <Button variant="outline" onClick={onBack}>
            ← Back to courses
          </Button>
          <div className="space-y-1 text-right">
            <Button size="lg" disabled={!ready || submitting} onClick={submit}>
              {submitting ? "Starting…" : "Analyze my path"}
            </Button>
            {submitError && <p className="text-xs text-anchor-critical">{submitError}</p>}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold">Where are you standing?</h1>
        <p className="text-base text-muted-foreground">
          Tell us what you've studied. One analysis, eight roles ranked by how far along you
          already are.
        </p>
      </header>

      <section className="max-w-[8rem] space-y-1.5">
        <Label htmlFor="semester">Semester</Label>
        <Input
          id="semester"
          inputMode="numeric"
          maxLength={1}
          value={semester}
          // Reject anything that isn't empty (mid-edit) or a single digit 1-8 — the box can
          // never hold an out-of-range value in the first place, not just fail validation later.
          onChange={(event) => {
            const next = event.target.value;
            if (next === "" || /^[1-8]$/.test(next)) setSemester(next);
          }}
        />
        {showErrors && problems.semester && (
          <p className="text-xs text-anchor-critical">{problems.semester}</p>
        )}
      </section>

      <Separator />

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Your courses
          </h2>
          <Button variant="outline" size="sm" disabled={atLimit} onClick={() => setCustomModalTarget("new")}>
            + Add a course not listed
          </Button>
        </div>

        {loadError && (
          <div className="space-y-2 rounded-md border p-4">
            <p className="text-sm text-muted-foreground">Could not load the course catalog.</p>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Try again
            </Button>
          </div>
        )}

        {!catalog && !loadError && (
          <div className="grid grid-cols-3 gap-2.5">
            {Array.from({ length: 9 }, (_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        )}

        {/* A fixed-size grid of tiles — catalog and added-by-hand courses alike. Clicking one
            opens a detail dialog (CourseDetailModal for catalog courses, CustomCourseModal for
            added ones), where picking, outline/semester, and removing all happen. Nothing in
            this grid ever grows or reflows: a tile's own size never depends on whether it's
            selected, only its border and the one-line summary shown once it's configured. */}
        {catalog && (
          <div className="grid grid-cols-3 gap-2.5">
            {catalog.map((course) => (
              <CourseTile
                key={course.id}
                title={course.name}
                code={course.code}
                blurb={course.curriculum_text}
                selected={Boolean(selections[course.id])}
                summary={summaryFor(course)}
                disabled={atLimit && !selections[course.id]}
                onOpen={() => setOpenCourseId(course.id)}
              />
            ))}
            {customCourses.map((course) => (
              <CourseTile
                key={`custom-${course.key}`}
                title={course.name.trim() || "Untitled course"}
                code={course.code.trim() || "Custom"}
                blurb={course.curriculum_text}
                selected
                summary={`${course.semester_tag === "past" ? "Previous semester" : "Current semester"} · Custom outline`}
                disabled={false}
                onOpen={() => setCustomModalTarget(course.key)}
              />
            ))}
          </div>
        )}

        <CourseDetailModal
          course={catalog?.find((c) => c.id === openCourseId) ?? null}
          existingSelection={openCourseId ? (selections[openCourseId] ?? null) : null}
          onClose={() => setOpenCourseId(null)}
          onSave={(selection) => openCourseId && saveCourseSelection(openCourseId, selection)}
          onRemove={() => openCourseId && removeCourseSelection(openCourseId)}
        />

        <CustomCourseModal
          open={customModalTarget !== null}
          existing={editingCustomCourse}
          existingTitles={pickedTitles}
          onClose={() => setCustomModalTarget(null)}
          onSave={saveCustomCourse}
          onRemove={removeCustomCourse}
        />

        {showErrors && problems.courses && (
          <p className="text-xs text-anchor-critical">{problems.courses}</p>
        )}
        {showErrors && problems.outline && (
          <p className="text-xs text-anchor-critical">{problems.outline}</p>
        )}
      </section>

      <Separator />

      <section className="space-y-2">
        <Button size="lg" onClick={handleContinue}>
          Continue
        </Button>
        {showErrors && !coursesReady && (
          <p className="text-xs text-muted-foreground">
            {[problems.semester, problems.courses, problems.custom, problems.outline]
              .filter(Boolean)
              .join(" ")}
          </p>
        )}
      </section>
    </div>
  );
}
