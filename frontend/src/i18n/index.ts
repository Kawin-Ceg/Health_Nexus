import { useCallback, useSyncExternalStore } from "react";
import { en, type MessageKey } from "./en";
import { hi } from "./hi";
import { ta } from "./ta";

export type Lang = "en" | "ta" | "hi";
export type { MessageKey };

export const LANGUAGES: { value: Lang; label: string }[] = [
  { value: "en", label: "English" },
  { value: "ta", label: "தமிழ்" },
  { value: "hi", label: "हिन्दी" },
];

const DICTS: Record<Lang, Partial<Record<MessageKey, string>>> = { en, ta, hi };
const KEY = "hn.lang";
const listeners = new Set<() => void>();

function stored(): Lang {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "ta" || v === "hi" || v === "en") return v;
  } catch {
    // storage blocked
  }
  return "en";
}

let current: Lang = stored();
document.documentElement.lang = current;

export function getLanguage(): Lang {
  return current;
}

export function setLanguage(next: Lang) {
  if (next === current) return;
  current = next;
  document.documentElement.lang = next;
  try {
    localStorage.setItem(KEY, next);
  } catch {
    // storage blocked
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

type Vars = Record<string, string | number>;

export function translate(lang: Lang, key: MessageKey, vars: Vars = {}): string {
  const template = DICTS[lang][key] ?? en[key];
  return template
    .replace(/\{(\w+):([^|}]*)\|([^}]*)\}/g, (_, name: string, one: string, other: string) => (Number(vars[name]) === 1 ? one : other))
    .replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}

export function useLanguage(): Lang {
  return useSyncExternalStore(subscribe, getLanguage);
}

export function useT() {
  const lang = useLanguage();
  return useCallback((key: MessageKey, vars?: Vars) => translate(lang, key, vars), [lang]);
}

/** A server-side English label (vital, symptom) in the chosen language, when there is a translation. */
export function useLabel() {
  const lang = useLanguage();
  return useCallback(
    (kind: "vital" | "symptom", key: string, fallback?: string) => {
      const found = lang === "en" ? undefined : DICTS[lang][`${kind}.${key}` as MessageKey];
      return found ?? fallback ?? key;
    },
    [lang],
  );
}
