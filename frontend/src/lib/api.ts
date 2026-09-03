import { getToken, clearToken } from "./auth";
import { getLiveSubmissionsForRole } from "./eventLog";
import type {
  CoursesResponse,
  StudentCreateRequest,
  StudentCreateResponse,
  AnalyzeResponse,
  RoadmapResponse,
  ProgressRequest,
  ProgressResponse,
  ProjectResponse,
  SubmitRequest,
  SubmitResponse,
  DashboardResponse,
  SkillsResponse,
  ProjectsResponse,
  SubmissionOut,
} from "./types";

import fixtureCourses from "@fixtures/courses.json";
import fixtureRoadmap from "@fixtures/roadmap_response.json";
import fixtureDashboard from "@fixtures/dashboard_response.json";
import fixtureSkills from "@fixtures/skills_response.json";
import fixtureProjects from "@fixtures/projects_response.json";

export class ApiError extends Error {
  status: number;
  /** The server's `{detail: "..."}` body, when it sent one (e.g. 422 repo messages). */
  detail: string | null;
  constructor(status: number, body: string) {
    let detail: string | null = null;
    try {
      const parsed: unknown = JSON.parse(body);
      if (parsed && typeof parsed === "object" && typeof (parsed as { detail?: unknown }).detail === "string") {
        detail = (parsed as { detail: string }).detail;
      }
    } catch {
      // body wasn't JSON — detail stays null, message below falls back to the raw text.
    }
    super(detail ?? `API error ${status}: ${body}`);
    this.status = status;
    this.detail = detail;
  }
}

// VITE_USE_FIXTURE serves contracts/fixtures/*.json instead of hitting a real API — the same
// dev mode V1 used to build the Roadmap screen (anchor-frontend skill), now also covering V2's
// dashboard/skills/projects endpoints, none of which exist on a real backend yet (docs/PRD-V2.md
// §0's audit). Delete this branch and the three V2 fixture imports above once the real
// endpoints land — every function below keeps the same signature either way.
const USE_FIXTURE = import.meta.env.VITE_USE_FIXTURE === "true";
const FIXTURE_DELAY_MS = 250;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Fixture-only simulation of DECISIONS #21's "verified = union over ALL passing submissions" —
// there's no server accumulating this across calls, so a tiny localStorage set stands in.
const SIM_VERIFIED_KEY = "anchor:sim_verified_skill_ids";

function getSimVerified(): string[] {
  try {
    const raw = localStorage.getItem(SIM_VERIFIED_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function addSimVerified(ids: string[]): string[] {
  const merged = Array.from(new Set([...getSimVerified(), ...ids]));
  localStorage.setItem(SIM_VERIFIED_KEY, JSON.stringify(merged));
  return merged;
}

async function fixtureResponse<T>(path: string, method: string, body: string | null): Promise<T> {
  await delay(FIXTURE_DELAY_MS);

  if (method === "GET" && path === "/api/courses") return fixtureCourses as unknown as T;
  if (method === "GET" && path === "/api/roadmap") return fixtureRoadmap as unknown as T;
  if (method === "GET" && path === "/api/dashboard") return fixtureDashboard as unknown as T;
  if (method === "GET" && path === "/api/skills") return fixtureSkills as unknown as T;
  if (method === "GET" && path === "/api/projects") {
    // Merge in any submissions made live this session (recorded by AnalysisContext.submitRepo
    // via eventLog.recordSubmission) so a resubmit shows up here on refetch, not just on the
    // Dashboard — same "make it actually react" reasoning as the Dashboard's seed+live design.
    const base = fixtureProjects as unknown as ProjectsResponse;
    const roadmap = fixtureRoadmap as unknown as RoadmapResponse;
    const merged: ProjectsResponse = {
      projects: base.projects.map((pwh) => {
        const roleTitle = roadmap.roles.find((r) => r.id === pwh.project.role_id)?.title ?? "";
        const seed = pwh.submissions[0];
        const live: SubmissionOut[] = getLiveSubmissionsForRole(roleTitle).map((e, i) => ({
          id: `live_${pwh.project.id}_${i}`,
          repo_url: e.repoUrl ?? "",
          total: e.total ?? seed.total,
          max_total: e.maxTotal ?? seed.max_total,
          passed: seed.passed,
          created_at: e.at,
          criteria_scores: seed.criteria_scores,
          feedback: seed.feedback,
        }));
        return { project: pwh.project, submissions: [...live, ...pwh.submissions] };
      }),
    };
    return merged as unknown as T;
  }
  if (method === "POST" && path === "/api/students") return { student_id: "fixture-student" } as unknown as T;
  if (method === "POST" && path === "/api/analyze") return { ok: true } as unknown as T;
  if (method === "POST" && path === "/api/progress") return { ok: true } as unknown as T;

  if (method === "GET" && path.startsWith("/api/project?")) {
    // Only the two roles authored in projects_response.json have a fixture project (matching
    // TDD-V2 §4.6's "lazy, cached per student×role" — nothing generates one on the fly here,
    // there's no model call in fixture mode). Every other role 404s, which is the honest answer
    // and exercises ProveIt.tsx's real load-error state, not a fabricated one.
    const roleId = new URL(path, "http://fixture").searchParams.get("role_id");
    const match = (fixtureProjects as unknown as ProjectsResponse).projects.find(
      (p) => p.project.role_id === roleId,
    );
    if (match) return match.project as unknown as T;
    throw new ApiError(404, "No project generated for this role yet");
  }

  if (method === "POST" && path === "/api/submit") {
    const parsed = body ? (JSON.parse(body) as SubmitRequest) : null;
    const match = (fixtureProjects as unknown as ProjectsResponse).projects.find(
      (p) => p.project.role_id === parsed?.role_id,
    );
    if (!match) {
      throw new ApiError(
        422,
        "This role doesn't have a fixture project yet — try Full-Stack Engineer or Machine Learning Engineer.",
      );
    }
    // Fixture mode has no live model call to re-grade a different URL, so it deterministically
    // replays that project's one authored submission — honest given ProveIt's own "reviewed by
    // reading the repo" copy, not pretended to be freshly scored.
    const seed = match.submissions[0];
    const verified = seed.passed ? addSimVerified(match.project.verifies) : getSimVerified();
    return {
      review: {
        criteria_scores: seed.criteria_scores,
        feedback: seed.feedback,
        total: seed.total,
        max_total: seed.max_total,
        passed: seed.passed,
      },
      verified_skill_ids: verified,
    } as unknown as T;
  }

  throw new ApiError(404, `No fixture handler for ${method} ${path}`);
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";

  if (USE_FIXTURE) {
    return fixtureResponse<T>(path, method, typeof init.body === "string" ? init.body : null);
  }

  const token = getToken();
  const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
    ...init,
    signal: AbortSignal.timeout(240_000),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (res.status === 401) {
    clearToken();
    window.location.assign("/login");
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}

export function getCourses(): Promise<CoursesResponse> {
  return api<CoursesResponse>("/api/courses");
}

export function createStudent(body: StudentCreateRequest): Promise<StudentCreateResponse> {
  return api<StudentCreateResponse>("/api/students", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function analyze(): Promise<AnalyzeResponse> {
  return api<AnalyzeResponse>("/api/analyze", { method: "POST" });
}

export function getRoadmap(): Promise<RoadmapResponse> {
  return api<RoadmapResponse>("/api/roadmap");
}

export function setProgress(body: ProgressRequest): Promise<ProgressResponse> {
  return api<ProgressResponse>("/api/progress", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getProject(roleId: string): Promise<ProjectResponse> {
  return api<ProjectResponse>(`/api/project?role_id=${encodeURIComponent(roleId)}`);
}

export function submitRepo(body: SubmitRequest): Promise<SubmitResponse> {
  return api<SubmitResponse>("/api/submit", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---- V2 (docs/TDD-V2.md §6) — real endpoints don't exist yet; see USE_FIXTURE above ----

export function getDashboard(): Promise<DashboardResponse> {
  return api<DashboardResponse>("/api/dashboard");
}

export function getSkills(): Promise<SkillsResponse> {
  return api<SkillsResponse>("/api/skills");
}

export function getProjects(): Promise<ProjectsResponse> {
  return api<ProjectsResponse>("/api/projects");
}
