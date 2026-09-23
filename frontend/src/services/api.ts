import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { AuthPayload, User } from "./auth";

/** Why the session ended without the user asking. Shown on the login page. */
export type SessionEndReason = "inactivity" | "expired";

export interface AuthHandlers {
  onRefreshed: (user: User) => void;
  onSessionEnded: (reason: SessionEndReason | null) => void;
}

// The access token lives here, in memory only. Never localStorage or sessionStorage:
// a page reload drops it and the httpOnly refresh cookie restores it.
let accessToken: string | null = null;
let handlers: AuthHandlers | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};
export const registerAuthHandlers = (h: AuthHandlers | null) => {
  handlers = h;
};

/** An error whose `detail` is always a string, however FastAPI shaped it. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  /** For 422s: message per field name, so a form can mark the right input. */
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, detail: string, fieldErrors: Record<string, string> = {}) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }
}

interface ValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

const tidy = (msg: string) => msg.replace(/^Value error,\s*/i, "");

/**
 * FastAPI's `detail` is a string for an HTTPException but a list of objects for a
 * 422. Rendering that list as a React child throws, so flatten it here, once.
 */
export function normaliseDetail(detail: unknown): { message: string; fieldErrors: Record<string, string> } {
  if (typeof detail === "string") return { message: detail, fieldErrors: {} };
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    const parts = (detail as ValidationItem[]).map((item) => {
      const msg = tidy(typeof item?.msg === "string" ? item.msg : "Invalid value");
      const field = item?.loc?.filter((p): p is string => typeof p === "string" && p !== "body").pop();
      if (field) fieldErrors[field] ??= msg;
      return field ? `${field.replace(/_/g, " ")}: ${msg}` : msg;
    });
    return { message: parts.join("; ") || "The request was not valid.", fieldErrors };
  }
  if (detail && typeof detail === "object" && "msg" in detail && typeof (detail as ValidationItem).msg === "string") {
    return { message: tidy((detail as ValidationItem).msg as string), fieldErrors: {} };
  }
  return { message: "Something went wrong. Please try again.", fieldErrors: {} };
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1",
  withCredentials: true, // sends the hn_refresh cookie
});

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.set("Authorization", `Bearer ${accessToken}`);
  return config;
});

type Retryable = InternalAxiosRequestConfig & { _retried?: boolean };

// Retrying these on a 401 would loop forever: a failed login or refresh is final.
const NEVER_RETRY = ["/auth/login", "/auth/refresh"];
const ALREADY_USED = /already used/i;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let inflightRefresh: Promise<AuthPayload> | null = null;

/**
 * One refresh at a time. React StrictMode and several tabs all ask at start-up;
 * the server rotates the token on each call, so a second concurrent call with
 * the same cookie would look like token theft.
 */
export function refreshSession(): Promise<AuthPayload> {
  inflightRefresh ??= (async () => {
    try {
      let response;
      try {
        response = await api.post<AuthPayload>("/auth/refresh");
      } catch (error) {
        // Another tab won the rotation a moment ago and has already set a fresh cookie.
        if (error instanceof ApiError && ALREADY_USED.test(error.detail)) {
          await sleep(400);
          response = await api.post<AuthPayload>("/auth/refresh");
        } else {
          throw error;
        }
      }
      accessToken = response.data.access_token;
      handlers?.onRefreshed(response.data.user);
      return response.data;
    } catch (error) {
      accessToken = null;
      if (error instanceof ApiError && error.status === 401) handlers?.onSessionEnded(endReasonOf(error.detail));
      throw error;
    }
  })().finally(() => {
    inflightRefresh = null;
  });
  return inflightRefresh;
}

/** No cookie at all is just "not signed in"; only a session that existed and died deserves a message. */
function endReasonOf(detail: string): SessionEndReason | null {
  if (/inactivity/i.test(detail)) return "inactivity";
  if (/no refresh token/i.test(detail)) return null;
  return "expired";
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: unknown }>) => {
    const config = error.config as Retryable | undefined;
    const status = error.response?.status ?? 0;

    if (status === 401 && config && !config._retried && !NEVER_RETRY.some((p) => config.url?.includes(p))) {
      config._retried = true;
      try {
        await refreshSession();
      } catch {
        return Promise.reject(toApiError(error));
      }
      return api(config); // the request interceptor attaches the new token
    }
    return Promise.reject(toApiError(error));
  },
);

function toApiError(error: AxiosError<{ detail?: unknown }>): ApiError {
  if (!error.response) {
    return new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }
  const { message, fieldErrors } = normaliseDetail(error.response.data?.detail);
  // Anything else that reads response.data.detail also gets a string.
  if (error.response.data && typeof error.response.data === "object") error.response.data.detail = message;
  return new ApiError(error.response.status, message, fieldErrors);
}

export const errorMessage = (error: unknown): string =>
  error instanceof ApiError ? error.detail : "Something went wrong. Please try again.";

/** Seconds from a 429's Retry-After header, if the server sent one. */
export const retryAfterSeconds = (error: unknown): number | null => {
  if (!(error instanceof ApiError) || error.status !== 429) return null;
  const match = error.detail.match(/(\d+)\s*seconds/);
  return match ? Number(match[1]) : null;
};
