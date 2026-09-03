import { clearStudentId, getStudentId } from "./identity";
import { rotateLastSeen } from "./eventLog";
import type { AuthResponse, LoginRequest, SignupRequest, UserOut } from "./types";

// Parallels identity.ts's single-responsibility pattern (docs/TDD-V2.md §7.1) — this is the
// only place the session token/user/onboarded flag are read or written. identity.ts still
// exists for the pre-signup anonymous student_id used by claim-on-signup below.

const TOKEN_KEY = "anchor:token";
const USER_KEY = "anchor:user";
const ONBOARDED_IDS_KEY = "anchor:onboarded_ids";
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

// Onboarded status is tracked per account id (not a single global flag) — a login must be able
// to tell a brand-new account (no analysis yet → /onboarding) apart from a returning one
// (→ Dashboard). The demo account is seeded as already-onboarded so logging in with it lands
// straight on the Dashboard, matching what it's there to demo.
function getOnboardedIds(): string[] {
  try {
    const raw = localStorage.getItem(ONBOARDED_IDS_KEY);
    return raw ? (JSON.parse(raw) as string[]) : ["usr_demo"];
  } catch {
    return ["usr_demo"];
  }
}

/** Whether the given (or, if omitted, currently logged-in) account has a completed analysis —
 *  drives RequireAuth's /onboarding redirect (TDD-V2 §5.5's "current_student finds no student →
 *  404 → /onboarding" rule, simulated). */
export function isOnboarded(userId?: string): boolean {
  const id = userId ?? getUser()?.id;
  if (!id) return false;
  return getOnboardedIds().includes(id);
}

export function setOnboarded(value: boolean, userId?: string): void {
  const id = userId ?? getUser()?.id;
  if (!id) return;
  const ids = getOnboardedIds();
  const next = value ? Array.from(new Set([...ids, id])) : ids.filter((x) => x !== id);
  localStorage.setItem(ONBOARDED_IDS_KEY, JSON.stringify(next));
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

/** Creates the account only — does NOT establish a session. Signup intentionally always sends
 *  the student to /login to sign in for real, rather than auto-logging them in (product
 *  decision, not a contract change: a real POST /signup would still return a usable token). */
export async function signup(body: Omit<SignupRequest, "claim_student_id">): Promise<UserOut> {
  const email = body.email.trim().toLowerCase();
  const accounts = getAccounts();
  if (accounts.some((a) => a.email === email)) {
    throw new AuthError(409, "Email already registered");
  }

  const user: UserOut = {
    id: randomId("usr"),
    email,
    name: body.name.trim(),
    created_at: new Date().toISOString(),
  };
  saveAccounts([...accounts, user]);

  // Claim-on-signup (TDD-V2 §5.1): a V1 anonymous student id, if present, is spent here either
  // way — claiming it means this account already has an analysis, so onboarding will be skipped
  // once they actually log in.
  const claimId = getStudentId();
  clearStudentId();
  if (claimId) setOnboarded(true, user.id);

  return user;
}

export async function login(body: LoginRequest): Promise<AuthResponse> {
  const email = body.email.trim().toLowerCase();
  const account = getAccounts().find((a) => a.email === email);
  // Never say which was wrong (PRD-V2 §4.1) — there is no separate password check to fail here
  // since the mock store holds no credentials, but the copy stays honest about what a real
  // backend would say either way.
  if (!account) throw new AuthError(401, "Wrong email or password");
  return issueSession(account);
}

export async function logout(): Promise<void> {
  clearToken();
  localStorage.removeItem(USER_KEY);
}
