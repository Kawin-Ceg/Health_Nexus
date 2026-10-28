import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, errorMessage } from "../services/api";

export interface Resource<T> {
  data: T | null;
  error: string | null;
  status: number | null;
  loading: boolean;
  reload: () => void;
}

export function useResource<T>(fetcher: (signal: AbortSignal) => Promise<T>, key: string): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const id = ++latest.current;
    const controller = new AbortController();
    setLoading(true);
    fetcherRef
      .current(controller.signal)
      .then((result) => {
        if (id !== latest.current) return;
        setData(result);
        setError(null);
        setStatus(null);
      })
      .catch((e: unknown) => {
        if (id !== latest.current || controller.signal.aborted) return;
        setError(errorMessage(e));
        setStatus(e instanceof ApiError ? e.status : 0);
      })
      .finally(() => {
        if (id === latest.current) setLoading(false);
      });
    return () => controller.abort();
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, status, loading, reload };
}
