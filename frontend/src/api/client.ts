/**
 * Thin fetch wrapper around the DevFlow API.
 *
 * Responsibilities kept here on purpose, so components never deal with them:
 *   - attaching the bearer token;
 *   - refreshing an expired access token once, transparently, and replaying the
 *     request (concurrent 401s share a single refresh);
 *   - turning the API error envelope into a typed ApiError.
 */

import type { AuthResponse, TokenPair } from "./types";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "/api/v1").replace(/\/$/, "");
const ACCESS_KEY = "devflow.access_token";
const REFRESH_KEY = "devflow.refresh_token";

export interface ApiErrorDetail {
  field: string;
  message: string;
  type: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: ApiErrorDetail[];

  constructor(status: number, code: string, message: string, details?: ApiErrorDetail[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Message for a specific form field, when the API reported one. */
  fieldError(field: string): string | undefined {
    return this.details?.find((detail) => detail.field === field)?.message;
  }
}

export const tokenStore = {
  access: (): string | null => localStorage.getItem(ACCESS_KEY),
  refresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  save(tokens: { access_token: string; refresh_token: string }): void {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

type SessionExpiredHandler = () => void;
let onSessionExpired: SessionExpiredHandler = () => {};

/** Registered by the auth provider so a dead session can bounce the user to /login. */
export function setSessionExpiredHandler(handler: SessionExpiredHandler): void {
  onSessionExpired = handler;
}

async function parseError(response: Response): Promise<ApiError> {
  let code = "http_error";
  let message = response.statusText || "Request failed.";
  let details: ApiErrorDetail[] | undefined;

  try {
    const body = await response.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      if (Array.isArray(body.error.details)) {
        details = body.error.details as ApiErrorDetail[];
      }
    }
  } catch {
    // Not JSON (a proxy error page, an empty body): keep the status text.
  }
  return new ApiError(response.status, code, message, details);
}

// A single in-flight refresh shared by every request that hits a 401 at once.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = tokenStore.refresh();
  if (!refreshToken) return false;

  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const tokens = (await response.json()) as TokenPair;
      tokenStore.save(tokens);
      return true;
    } catch {
      return false;
    } finally {
      // Cleared on the next tick so parallel callers observe the same result.
      setTimeout(() => {
        refreshInFlight = null;
      }, 0);
    }
  })();

  return refreshInFlight;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  /** Skips the bearer header and the refresh dance (used by login/register). */
  anonymous?: boolean;
}

export function buildQuery(
  params: Record<string, string | number | boolean | undefined | null> = {},
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.append(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function send<T>(path: string, options: RequestOptions, retry = true): Promise<T> {
  const { method = "GET", body, params, anonymous } = options;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const token = tokenStore.access();
  if (!anonymous && token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}${path}${buildQuery(params)}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && !anonymous && retry) {
    if (await refreshSession()) {
      return send<T>(path, options, false);
    }
    tokenStore.clear();
    onSessionExpired();
    throw await parseError(response);
  }

  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"]) => send<T>(path, { params }),
  post: <T>(path: string, body?: unknown, anonymous = false) =>
    send<T>(path, { method: "POST", body, anonymous }),
  patch: <T>(path: string, body: unknown) => send<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => send<T>(path, { method: "DELETE" }),
};

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>("/auth/login", { email, password }, true),
  register: (fullName: string, email: string, password: string) =>
    api.post<AuthResponse>("/auth/register", { full_name: fullName, email, password }, true),
  logout: () => api.post<{ message: string }>("/auth/logout"),
  me: () => api.get<AuthResponse["user"]>("/auth/me"),
};
