const KEY = "anchor:student_id";

export function getStudentId(): string | null {
  return localStorage.getItem(KEY);
}

export function setStudentId(id: string): void {
  localStorage.setItem(KEY, id);
}

export function clearStudentId(): void {
  localStorage.removeItem(KEY);
}
