export type ThemeChoice = "system" | "light" | "dark";

const KEY = "hn.theme";
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const listeners = new Set<(dark: boolean) => void>();
let choice: ThemeChoice = "light";

export const isDark = () => choice === "dark" || (choice === "system" && darkQuery.matches);

function apply() {
  const dark = isDark();
  document.documentElement.classList.toggle("dark", dark);
  listeners.forEach((listener) => listener(dark));
}

export function setTheme(next: ThemeChoice) {
  choice = next;
  try {
    localStorage.setItem(KEY, next);
  } catch {
  }
  apply();
}

export function onThemeChange(listener: (dark: boolean) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function initTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark" || saved === "system") choice = saved;
  } catch {
  }
  apply();
  darkQuery.addEventListener("change", apply);
}
