import { useCallback } from "react";
import { en, type MessageKey } from "./en";

export type Lang = "en";
export type { MessageKey };

export function useLanguage(): Lang {
  return "en";
}

type Vars = Record<string, string | number>;

export function translate(key: MessageKey, vars: Vars = {}): string {
  return en[key]
    .replace(/\{(\w+):([^|}]*)\|([^}]*)\}/g, (_, name: string, one: string, other: string) => (Number(vars[name]) === 1 ? one : other))
    .replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}

export function useT() {
  return useCallback((key: MessageKey, vars?: Vars) => translate(key, vars), []);
}

export function useLabel() {
  return useCallback((_kind: "vital" | "symptom", key: string, fallback?: string) => fallback ?? key, []);
}
