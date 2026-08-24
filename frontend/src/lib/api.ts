import { getStudentId } from "./identity";
import type {
  CoursesResponse,
  StudentCreateRequest,
  StudentCreateResponse,
  AnalyzeResponse,
  RoadmapResponse,
  ProgressRequest,
  ProgressResponse,
} from "./types";

import fixtureCourses from "@fixtures/courses.json";
import fixtureRoadmap from "@fixtures/roadmap_response.json";

export class ApiError extends Error {
  status: number;
  constructor(status: number, body: string) {
    super(`API error ${status}: ${body}`);
    this.status = status;
  }
}

const USE_FIXTURE = import.meta.env.VITE_USE_FIXTURE === "true";
const FIXTURE_DELAY_MS = 300;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fixtureResponse<T>(path: string, method: string): Promise<T> {
  await delay(FIXTURE_DELAY_MS);

  if (method === "GET" && path === "/api/courses") {
    return fixtureCourses as unknown as T;
  }
  if (method === "GET" && path === "/api/roadmap") {
    return fixtureRoadmap as unknown as T;
  }
  if (method === "POST" && path === "/api/students") {
    return { student_id: "fixture-student" } as unknown as T;
  }
  if (method === "POST" && path === "/api/analyze") {
    return { ok: true } as unknown as T;
  }
  if (method === "POST" && path === "/api/progress") {
    return { ok: true } as unknown as T;
  }

  throw new ApiError(404, `No fixture handler for ${method} ${path}`);
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";

  if (USE_FIXTURE) {
    return fixtureResponse<T>(path, method);
  }

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
