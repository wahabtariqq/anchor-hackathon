import { getStudentId } from "./identity";
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
} from "./types";

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

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const studentId = getStudentId();
  const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
    ...init,
    signal: AbortSignal.timeout(240_000),
    headers: {
      "Content-Type": "application/json",
      ...(studentId ? { "X-Student-Id": studentId } : {}),
      ...init.headers,
    },
  });
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
