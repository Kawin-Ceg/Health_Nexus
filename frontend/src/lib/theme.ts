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

/**
 * themes.css swaps the tokens under `.dark`. Light until someone picks otherwise; "system"
 * follows the OS, live. The choice is kept on this device so signed-out pages remember it too.
 */
export function setTheme(next: ThemeChoice) {
  choice = next;
  try {
    localStorage.setItem(KEY, next);
  } catch {
    // Storage blocked: the choice lasts until the page reloads.
  }
  apply();
}

/** Calls `listener` whenever the theme changes; returns the unsubscribe function. */
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
    // Storage blocked: start light.
  }
  apply();
  darkQuery.addEventListener("change", apply);
}
