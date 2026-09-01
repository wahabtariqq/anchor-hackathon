const KEY = "anchor:student_id";
const NAME_KEY = "anchor:student_name";

export function getStudentId(): string | null {
  return localStorage.getItem(KEY);
}

export function setStudentId(id: string): void {
  localStorage.setItem(KEY, id);
}

// Display-only personalization for the app shell (AppShell.tsx) — never sent to the
// API, never used for identity/auth. The id is what X-Student-Id carries.
export function getStudentName(): string | null {
  return localStorage.getItem(NAME_KEY);
}

export function setStudentName(name: string): void {
  localStorage.setItem(NAME_KEY, name);
}

export function clearStudentId(): void {
  localStorage.removeItem(KEY);
  localStorage.removeItem(NAME_KEY);
}
