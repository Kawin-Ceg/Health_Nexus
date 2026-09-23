import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Anything read from the URL is untrusted: `?days=abc` must never reach the API.
 * These parse, validate and clamp, falling back to a default.
 */
export function intParam(raw: string | null, fallback: number, min: number, max: number): number {
  if (raw === null || !/^\d{1,6}$/.test(raw)) return fallback;
  return Math.min(max, Math.max(min, Number(raw)));
}

export function oneOf<T extends string>(raw: string | null, allowed: readonly T[], fallback: T): T;
export function oneOf<T extends string>(raw: string | null, allowed: readonly T[], fallback: null): T | null;
export function oneOf<T extends string>(raw: string | null, allowed: readonly T[], fallback: T | null): T | null {
  return raw !== null && (allowed as readonly string[]).includes(raw) ? (raw as T) : fallback;
}

export function textParam(raw: string | null, maxLength: number): string {
  return (raw ?? "").slice(0, maxLength);
}

/** Read and write query parameters; writing an empty value removes the key. Replaces history, so filters do not flood Back. */
export function useQueryState() {
  const [params, setParams] = useSearchParams();
  const set = useCallback(
    (updates: Record<string, string | number | null | undefined>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(updates)) {
            if (value === null || value === undefined || value === "") next.delete(key);
            else next.set(key, String(value));
          }
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  return useMemo(() => ({ params, set }), [params, set]);
}
