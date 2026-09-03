import { clearStudentId, getStudentId } from "./identity";
import { rotateLastSeen } from "./eventLog";
import type { AuthResponse, LoginRequest, SignupRequest, UserOut } from "./types";

// Parallels identity.ts's single-responsibility pattern (docs/TDD-V2.md §7.1) — this is the
// only place the session token/user/onboarded flag are read or written. identity.ts still
// exists for the pre-signup anonymous student_id used by claim-on-signup below.

const TOKEN_KEY = "anchor:token";
const USER_KEY = "anchor:user";
const ONBOARDED_KEY = "anchor:onboarded";
const ACCOUNTS_KEY = "anchor:mock_accounts";

export class AuthError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function getUser(): UserOut | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as UserOut) : null;
}

function setUser(user: UserOut): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Whether this account has a completed analysis — drives RequireAuth's /onboarding redirect
 *  (TDD-V2 §5.5's "current_student finds no student → 404 → /onboarding" rule, simulated). */
export function isOnboarded(): boolean {
  return localStorage.getItem(ONBOARDED_KEY) === "1";
}

export function setOnboarded(value: boolean): void {
  if (value) localStorage.setItem(ONBOARDED_KEY, "1");
  else localStorage.removeItem(ONBOARDED_KEY);
}

// ---- fixture-only mock account store ----
// /api/auth/* doesn't exist yet (docs/PRD-V2.md §0's audit found the backend empty) — there is
// no real endpoint to fall back to, so signup/login are fully local until it lands. The seam is
// this file only: swap the two function bodies below for real POSTs, keep the same signatures,
// and every caller (LoginPage/SignupPage/RequireAuth) needs zero changes.

const DEMO_ACCOUNT: UserOut = {
  id: "usr_demo",
  email: "ayesha@example.com",
  name: "Ayesha",
  semester: 4,
  created_at: new Date().toISOString(),
};

function getAccounts(): UserOut[] {
  try {
    const raw = localStorage.getItem(ACCOUNTS_KEY);
    return raw ? (JSON.parse(raw) as UserOut[]) : [DEMO_ACCOUNT];
  } catch {
    return [DEMO_ACCOUNT];
  }
}

function saveAccounts(accounts: UserOut[]): void {
  localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
}

function randomId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function issueSession(user: UserOut): AuthResponse {
  const token = randomId("tok");
  setToken(token);
  setUser(user);
  rotateLastSeen();
  return { token, user };
}

export async function signup(body: Omit<SignupRequest, "claim_student_id">): Promise<AuthResponse> {
  const email = body.email.trim().toLowerCase();
  const accounts = getAccounts();
  if (accounts.some((a) => a.email === email)) {
    throw new AuthError(409, "Email already registered");
  }

  const user: UserOut = {
    id: randomId("usr"),
    email,
    name: body.name.trim(),
    semester: body.semester,
    created_at: new Date().toISOString(),
  };
  saveAccounts([...accounts, user]);

  // Claim-on-signup (TDD-V2 §5.1): a V1 anonymous student id, if present, is spent here either
  // way — claiming it means this account already has an analysis, so onboarding is skipped.
  const claimId = getStudentId();
  clearStudentId();
  setOnboarded(Boolean(claimId));

  return issueSession(user);
}

export async function login(body: LoginRequest): Promise<AuthResponse> {
  const email = body.email.trim().toLowerCase();
  const account = getAccounts().find((a) => a.email === email);
  // Never say which was wrong (PRD-V2 §4.1) — there is no separate password check to fail here
  // since the mock store holds no credentials, but the copy stays honest about what a real
  // backend would say either way.
  if (!account) throw new AuthError(401, "Wrong email or password");
  setOnboarded(true); // a returning account has necessarily finished onboarding already
  return issueSession(account);
}

export async function logout(): Promise<void> {
  clearToken();
  localStorage.removeItem(USER_KEY);
}

export async function logoutAll(): Promise<void> {
  await logout();
}
