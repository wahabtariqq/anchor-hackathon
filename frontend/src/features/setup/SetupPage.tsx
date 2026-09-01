import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { createStudent, getCourses } from "@/lib/api";
import { setStudentId, setStudentName } from "@/lib/identity";
import type {
  CatalogCourse,
  Interest,
  SemesterTag,
  StudentCourseInput,
} from "@/lib/types";
import { CourseCard, type CourseSelection } from "./CourseCard";
import { InterestChips } from "./InterestChips";

const MIN_COURSES = 3;
const MAX_COURSES = 6;
const MIN_INTERESTS = 2;
const MIN_CUSTOM_CHARS = 50;      // mirrors MIN_CUSTOM_CURRICULUM_CHARS in backend/app/schemas.py

interface CustomCourse {
  key: number;
  name: string;
  semester_tag: SemesterTag;
  curriculum_text: string;
}

interface SetupPageProps {
  /** Called with the new student id once it is stored. The router owns the redirect to
   *  /analyzing, which is where POST /api/analyze is fired from (TDD §5.1). */
  onComplete?: (studentId: string) => void;
}

export function SetupPage({ onComplete }: SetupPageProps) {
  const [catalog, setCatalog] = useState<CatalogCourse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [name, setName] = useState("");
  const [semester, setSemester] = useState("4");
  const [selections, setSelections] = useState<Record<string, CourseSelection>>({});
  const [customCourses, setCustomCourses] = useState<CustomCourse[]>([]);
  const [interests, setInterests] = useState<Interest[]>([]);

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
  const semesterValid = Number.isInteger(semesterNumber) && semesterNumber >= 1 && semesterNumber <= 12;

  // PRD §10.1 mandates a disabled submit button, so a validation error must never be gated
  // behind a click nobody can make. Course rows report live as soon as they have any content;
  // the header fields wait for a submit attempt, and the summary under the button always says
  // what is still missing.
  const customErrors = customCourses.map((course) => {
    if (!course.name.trim()) return "Give the course a name.";
    if (course.curriculum_text.trim().length < MIN_CUSTOM_CHARS) {
      return `Paste at least ${MIN_CUSTOM_CHARS} characters of outline (${course.curriculum_text.trim().length} so far).`;
    }
    return null;
  });

  const problems = {
    name: name.trim() ? null : "Enter your name.",
    semester: semesterValid ? null : "Semester must be a number between 1 and 12.",
    courses:
      courseCount < MIN_COURSES
        ? `Pick at least ${MIN_COURSES} courses (${courseCount} so far).`
        : null,
    interests:
      interests.length < MIN_INTERESTS
        ? `Pick at least ${MIN_INTERESTS} interests (${interests.length} so far).`
        : null,
    custom: customErrors.some(Boolean) ? "Finish the courses you added below." : null,
  };
  const ready = !Object.values(problems).some(Boolean);

  const grouped = useMemo(() => {
    const label = (tag: SemesterTag) => {
      const catalogCodes = (catalog ?? [])
        .filter((c) => selections[c.id]?.semester_tag === tag)
        .map((c) => c.code);
      const customNames = customCourses
        .filter((c) => c.semester_tag === tag)
        .map((c) => c.name.trim() || "Untitled");
      return [...catalogCodes, ...customNames];
    };
    return { past: label("past"), current: label("current") };
  }, [catalog, selections, customCourses]);

  function toggleCourse(courseId: string) {
    setSelections((prev) => {
      const next = { ...prev };
      if (next[courseId]) delete next[courseId];
      else next[courseId] = { semester_tag: "past", override: null };
      return next;
    });
  }

  function patchSelection(courseId: string, patch: Partial<CourseSelection>) {
    setSelections((prev) =>
      prev[courseId] ? { ...prev, [courseId]: { ...prev[courseId], ...patch } } : prev,
    );
  }

  function toggleInterest(interest: Interest) {
    setInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest],
    );
  }

  function patchCustom(key: number, patch: Partial<CustomCourse>) {
    setCustomCourses((prev) => prev.map((c) => (c.key === key ? { ...c, ...patch } : c)));
  }

  async function submit() {
    setShowErrors(true);
    if (!ready || submitting) return;

    const courses: StudentCourseInput[] = [
      ...(catalog ?? [])
        .filter((course) => selections[course.id])
        .map((course) => {
          const selection = selections[course.id];
          const override = selection.override?.trim();
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
        name: name.trim(),
        semester: semesterNumber,
        interests,
        courses,
      });
      setStudentId(student_id);
      setStudentName(name.trim());
      onComplete?.(student_id);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Could not start the analysis");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Where are you standing?</h1>
        <p className="text-sm text-muted-foreground">
          Tell us what you've studied and what interests you. One analysis, eight roles ranked by
          how far along you already are.
        </p>
      </header>

      <section className="grid grid-cols-[1fr_8rem] gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="name">Your name</Label>
          <Input
            id="name"
            value={name}
            placeholder="Ayesha"
            onChange={(event) => setName(event.target.value)}
          />
          {showErrors && problems.name && (
            <p className="text-xs text-anchor-critical">{problems.name}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="semester">Semester</Label>
          <Input
            id="semester"
            inputMode="numeric"
            value={semester}
            onChange={(event) => setSemester(event.target.value)}
          />
          {showErrors && problems.semester && (
            <p className="text-xs text-anchor-critical">{problems.semester}</p>
          )}
        </div>
      </section>

      <Separator />

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Your courses
          </h2>
          <span className="text-xs text-muted-foreground">
            {courseCount} of {MAX_COURSES} · pick {MIN_COURSES}–{MAX_COURSES}
          </span>
        </div>

        {(grouped.past.length > 0 || grouped.current.length > 0) && (
          <p className="text-xs text-muted-foreground">
            {grouped.past.length > 0 && <>Previous semesters: {grouped.past.join(", ")}</>}
            {grouped.past.length > 0 && grouped.current.length > 0 && " · "}
            {grouped.current.length > 0 && <>Current semester: {grouped.current.join(", ")}</>}
          </p>
        )}

        {loadError && (
          <div className="space-y-2 rounded-md border p-4">
            <p className="text-sm text-muted-foreground">Could not load the course catalog.</p>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Try again
            </Button>
          </div>
        )}

        {!catalog && !loadError && (
          <div className="grid grid-cols-2 items-start gap-3">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
        )}

        {catalog && (
          <div className="grid grid-cols-2 items-start gap-3">
            {catalog.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                selection={selections[course.id] ?? null}
                disabled={atLimit && !selections[course.id]}
                onToggle={() => toggleCourse(course.id)}
                onTagChange={(semester_tag) => patchSelection(course.id, { semester_tag })}
                onOverrideChange={(override) => patchSelection(course.id, { override })}
              />
            ))}
          </div>
        )}

        {customCourses.map((course, index) => (
          <Card key={course.key}>
            <CardContent className="space-y-2 p-4">
              <div className="flex items-center gap-2">
                <Input
                  value={course.name}
                  placeholder="Course name, e.g. Human-Computer Interaction"
                  onChange={(event) => patchCustom(course.key, { name: event.target.value })}
                />
                <div className="flex shrink-0 gap-1">
                  {(["past", "current"] as const).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => patchCustom(course.key, { semester_tag: tag })}
                      className={
                        course.semester_tag === tag
                          ? "rounded-md border border-foreground/40 px-2 py-1 text-xs font-medium"
                          : "rounded-md border border-transparent px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                      }
                    >
                      {tag === "past" ? "Previous" : "Current"}
                    </button>
                  ))}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    setCustomCourses((prev) => prev.filter((c) => c.key !== course.key))
                  }
                >
                  Remove
                </Button>
              </div>
              <Textarea
                rows={4}
                value={course.curriculum_text}
                placeholder="Paste the course outline — topics, projects, anything the syllabus lists…"
                onChange={(event) => patchCustom(course.key, { curriculum_text: event.target.value })}
              />
              {customErrors[index] &&
                (showErrors || Boolean(course.name.trim() || course.curriculum_text.trim())) && (
                  <p className="text-xs text-anchor-critical">{customErrors[index]}</p>
                )}
            </CardContent>
          </Card>
        ))}

        <Button
          variant="outline"
          size="sm"
          disabled={atLimit}
          onClick={() =>
            setCustomCourses((prev) => [
              ...prev,
              { key: Date.now() + prev.length, name: "", semester_tag: "current", curriculum_text: "" },
            ])
          }
        >
          + Add a course not listed
        </Button>

        {showErrors && problems.courses && (
          <p className="text-xs text-anchor-critical">{problems.courses}</p>
        )}
      </section>

      <Separator />

      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          What interests you
        </h2>
        <InterestChips selected={interests} onToggle={toggleInterest} />
        {showErrors && problems.interests && (
          <p className="text-xs text-anchor-critical">{problems.interests}</p>
        )}
      </section>

      <Separator />

      <section className="space-y-2">
        <Button size="lg" disabled={!ready || submitting} onClick={submit}>
          {submitting ? "Starting…" : "Analyze my path"}
        </Button>
        {submitError && <p className="text-xs text-anchor-critical">{submitError}</p>}
        {!ready && (
          <p className="text-xs text-muted-foreground">
            {[problems.name, problems.semester, problems.courses, problems.interests, problems.custom]
              .filter(Boolean)
              .join(" ")}
          </p>
        )}
      </section>
    </div>
  );
}
