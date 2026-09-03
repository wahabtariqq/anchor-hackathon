// Mirrors docs/CONTRACT.md. Change one, change the other in the same PR (per anchor-contract skill).

export type Depth = "full" | "partial";
export type Weight = "core" | "supporting";
export type Proximity = "core" | "adjacent";
export type SemesterTag = "past" | "current";

export const INTERESTS = [
  "Artificial Intelligence",
  "Databases",
  "UI/UX Design",
  "Web Development",
  "Systems & Infrastructure",
  "Data Analysis",
  "Security",
  "Mobile",
] as const;
export type Interest = (typeof INTERESTS)[number];

// ---- GET /api/courses ----

export interface CatalogCourse {
  id: string;
  code: string;
  name: string;
  curriculum_text: string;
}

export interface CoursesResponse {
  courses: CatalogCourse[];
}

// ---- POST /api/students ----

export type StudentCourseInput =
  | { course_id: string; semester_tag: SemesterTag; curriculum_override?: string }
  | { custom_name: string; semester_tag: SemesterTag; curriculum_text: string };

export interface StudentCreateRequest {
  name: string;
  semester: number;
  interests: Interest[];
  courses: StudentCourseInput[];
}

export interface StudentCreateResponse {
  student_id: string;
}

// ---- POST /api/analyze ----

export interface AnalyzeResponse {
  ok: true;
}

// ---- GET /api/roadmap ----

export interface RoadmapStudent {
  name: string;
  semester: number;
  interests: Interest[];
}

export interface RoadmapSkill {
  id: string;
  slug: string;
  name: string;
  real_world: string;
  coverage_depth: Depth | null;
  covered_by: string[];
  checked: boolean;
  verified: boolean;
}

export interface RoadmapRoleSkill {
  skill_id: string;
  weight: Weight;
}

export interface RoadmapRole {
  id: string;
  slug: string;
  title: string;
  one_liner: string;
  proximity: Proximity;
  bridge: string;
  rank: number;
  fit_percent: number;
  skills: RoadmapRoleSkill[];
  project: ProjectResponse | null;
  latest_review: ReviewResponse | null;
}

export interface RoadmapCourse {
  id: string;
  code: string;
  name: string;
  semester_tag: SemesterTag;
  skill_ids: string[];
}

export interface RoadmapResponse {
  student: RoadmapStudent;
  skills: RoadmapSkill[];
  roles: RoadmapRole[];
  courses: RoadmapCourse[];
}

// ---- GET /api/project?role_id= ----

export interface ProjectResponse {
  id: string;
  role_id: string;
  title: string;
  spec: string;
  criteria: string[];
  verifies: string[]; // skill ids (this role's skills)
}

// ---- POST /api/submit ----

export interface SubmitRequest {
  role_id: string;
  repo_url: string;
}

export interface CriterionScore {
  criterion: string;
  score: 0 | 1 | 2;
  note: string;
}

export interface ReviewResponse {
  criteria_scores: CriterionScore[];
  feedback: string;
  total: number;
  max_total: number;
  passed: boolean;
}

export interface SubmitResponse {
  review: ReviewResponse;
  verified_skill_ids: string[]; // full verified set for the student, across all passing submissions
}

// ---- POST /api/progress ----

export interface ProgressRequest {
  skill_id: string;
  checked: boolean;
}

export interface ProgressResponse {
  ok: true;
}

// ---- V2 (docs/TDD-V2.md §6) — frontend-only fixture today, no real backend yet.
// Copied verbatim from the TDD; not yet mirrored in backend/app/schemas.py or docs/CONTRACT.md.
// A real integration PR must be titled `contract: …` and update both, per CLAUDE.md. ----

// -- POST /api/auth/signup, /login --

export interface SignupRequest {
  email: string;
  password: string;
  name: string;
  semester: number;
  claim_student_id?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserOut {
  id: string;
  email: string;
  name: string;
  semester: number;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: UserOut;
}

// -- GET /api/dashboard --

export interface SnapshotPoint {
  fit: number;
  at: string;
}

export type NextActionKind = "tick" | "project";

export interface NextAction {
  role_id: string;
  label: string;
  kind: NextActionKind;
}

export interface ActivityEvent {
  text: string;
  at: string;
}

export interface DashboardTopRole {
  id: string;
  title: string;
  fit_percent: number;
}

export interface DashboardResponse {
  top_role: DashboardTopRole | null;
  skills_verified: number;
  skills_checked: number;
  verified_delta: number;
  checked_delta: number;
  snapshots: Record<string, SnapshotPoint[]>;
  next_actions: NextAction[];
  recent_events: ActivityEvent[];
}

// -- GET /api/skills --

export interface SkillRoleRef {
  id: string;
  title: string;
}

export interface SkillInventoryRow {
  id: string;
  slug: string;
  name: string;
  real_world: string;
  coverage_depth: Depth | null;
  checked: boolean;
  verified: boolean;
  roles: SkillRoleRef[];
}

export interface SkillsResponse {
  skills: SkillInventoryRow[];
}

// -- GET /api/projects --

export interface SubmissionOut {
  id: string;
  repo_url: string;
  total: number;
  max_total: number;
  passed: boolean;
  created_at: string;
  criteria_scores: CriterionScore[];
  feedback: string;
}

export interface ProjectWithHistory {
  project: ProjectResponse;
  submissions: SubmissionOut[];
}

export interface ProjectsResponse {
  projects: ProjectWithHistory[];
}

// ---- shared scoring input shape ----

export interface ScoredSkillInput {
  weight: Weight;
  coverageDepth: Depth | null;
  checked: boolean;
  verified: boolean;
}
