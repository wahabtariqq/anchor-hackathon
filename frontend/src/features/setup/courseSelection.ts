import type { SemesterTag } from "@/lib/types";

export const DEFAULT_OUTLINE = "default";
export const CUSTOM_OUTLINE = "custom";

export interface CourseSelection {
  semester_tag: SemesterTag;
  /** DEFAULT_OUTLINE | CUSTOM_OUTLINE | one of course.curriculum_variants[].id */
  outline: string;
  /** only meaningful when outline === CUSTOM_OUTLINE */
  customText: string;
}
