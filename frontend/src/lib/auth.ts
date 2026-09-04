import { clearStudentId, getStudentId } from "./identity";
import { rotateLastSeen } from "./eventLog";
import type { AuthResponse, LoginRequest, SignupRequest, UserOut } from "./types";

// Parallels identity.ts's single-responsibility pattern (docs/TDD-V2.md §7.1) — this is the
// only place the session token/user/onboarded flag are read or written. identity.ts still
// exists for the pre-signup anonymous student_id used by claim-on-signup below.
//
// Wired to the real backend (POST /api/auth/signup|login|logout, landed in the V2 auth PR).
// The mock account store below is kept but now only runs under VITE_USE_FIXTURE, so the
// frontend still boots and demos with no backend at all. Every exported signature is
// unchanged, which is what TDD-V2 §7.5 promised: no screen needed a change.

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

const API = import.meta.env.VITE_API_URL ?? "";
const USE_FIXTURE = import.meta.env.VITE_USE_FIXTURE === "true";

/** FastAPI sends `{detail: string}`, or `{detail: [{msg, loc}, ...]}` for a 422. Turn either
 *  into one sentence a person can read; never surface the raw JSON. */
function readDetail(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    if (first && typeof first.msg === "string") return first.msg.replace(/^Value error, /, "");
  }
  return fallback;
}

async function postAuth<T>(path: string, body: unknown, token?: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new AuthError(0, "Can't reach the server — is the API running?");
  }
  const payload: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new AuthError(res.status, readDetail(payload, "Something went wrong — try again."));
  return payload as T;
}

/** Has this account finished onboarding? The server is the authority: GET /api/roadmap answers
 *  200 when an analysis exists and 404 ("No student profile yet") when it does not. Probed once
 *  at login and cached, so RequireAuth can stay a synchronous render-time guard rather than
 *  every screen growing a loading state. api.ts self-corrects the flag if it ever goes stale. */
async function probeOnboarded(token: string, userId: string): Promise<void> {
  try {
    const res = await fetch(`${API}/api/roadmap`, { headers: { Authorization: `Bearer ${token}` } });
    setOnboarded(res.ok, userId);
  } catch {
    setOnboarded(false, userId);
  }
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

  if (!USE_FIXTURE) {
    // Claim-on-signup (TDD-V2 §5.1): hand the server any V1 anonymous student id we still
    // hold. It adopts it only if unclaimed, and ignores an unknown one. Spent either way.
    const claim = getStudentId();
    const { user } = await postAuth<{ user: UserOut }>("/api/auth/signup", {
      email,
      password: body.password,
      name: body.name.trim(),
      ...(claim ? { claim_student_id: claim } : {}),
    });
    clearStudentId();
    // No token here by design — signup creates the account, the login that follows starts the
    // session (DECISIONS #78). Onboarded status is settled by login's probe.
    return user;
  }

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

  if (!USE_FIXTURE) {
    const auth = await postAuth<AuthResponse>("/api/auth/login", { email, password: body.password });
    setToken(auth.token);
    setUser(auth.user);
    rotateLastSeen();
    await probeOnboarded(auth.token, auth.user.id);
    return auth;
  }

  const account = getAccounts().find((a) => a.email === email);
  // Never say which was wrong (PRD-V2 §4.1) — there is no separate password check to fail here
  // since the mock store holds no credentials, but the copy stays honest about what a real
  // backend would say either way.
  if (!account) throw new AuthError(401, "Wrong email or password");
  return issueSession(account);
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (!USE_FIXTURE && token) {
    // Best effort: the server call ends the session, but a network failure must not strand
    // the user in a logged-in-looking app. Local state is cleared either way.
    await postAuth("/api/auth/logout", {}, token).catch(() => undefined);
  }
  clearToken();
  localStorage.removeItem(USER_KEY);
}

/** Ends every session for this account. The backend route exists; no screen calls it yet
 *  (PRD-V2 §4.7 cut the profile screen that would have). */
export async function logoutAll(): Promise<void> {
  const token = getToken();
  if (!USE_FIXTURE && token) {
    await postAuth("/api/auth/logout_all", {}, token).catch(() => undefined);
  }
  clearToken();
  localStorage.removeItem(USER_KEY);
}
