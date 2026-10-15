import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { BellRing, CircleCheck, Info, X } from "lucide-react";
import { play } from "../../lib/sound";
import { cx } from "./ui";

export type ToastTone = "alert" | "success" | "info";

interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  body?: string;
}

interface ToastApi {
  /** Shows a message and plays its sound: alert → alert chime, success → clear, info → message. */
  notify: (toast: Omit<Toast, "id">) => void;
}

const ToastContext = createContext<ToastApi>({ notify: () => undefined });

const SOUND = { alert: "alert", success: "clear", info: "message" } as const;
const ICON = { alert: BellRing, success: CircleCheck, info: Info };
const TONE = {
  alert: "bg-danger-soft text-danger",
  success: "bg-success-soft text-success",
  info: "bg-lime text-olive",
};
const LIFETIME_MS = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(0);

  const dismiss = useCallback((id: number) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const notify = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = ++next.current;
      setToasts((list) => [...list.slice(-2), { ...toast, id }]);
      play(SOUND[toast.tone]);
      window.setTimeout(() => dismiss(id), LIFETIME_MS);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-[300] flex flex-col items-end gap-2 sm:left-auto sm:right-6 sm:bottom-6"
      >
        {toasts.map((t) => {
          const Icon = ICON[t.tone];
          return (
            <div
              key={t.id}
              className="hn-toast pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-3xl border border-line bg-surface p-4 shadow-[0_24px_60px_-30px_rgb(17_17_17/0.45)]"
            >
              <span className={cx("grid h-9 w-9 shrink-0 place-items-center rounded-full", TONE[t.tone])}>
                <Icon size={18} aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1 pt-1">
                <p className="font-display text-lg leading-tight text-ink">{t.title}</p>
                {t.body && <p className="mt-1 text-sm text-ink-soft">{t.body}</p>}
              </div>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink-soft hover:bg-paper-raised hover:text-ink"
                aria-label="Dismiss"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
