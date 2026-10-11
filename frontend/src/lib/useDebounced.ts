import { useEffect, useState } from "react";

/** `value`, but only after it has stopped changing for `ms`: search boxes query once typing pauses. */
export function useDebounced<T>(value: T, ms = 300): T {
  const [out, setOut] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setOut(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return out;
}
