export type ThemeChoice = "system" | "light" | "dark";

const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
let choice: ThemeChoice = "system";

function apply() {
  const dark = choice === "dark" || (choice === "system" && darkQuery.matches);
  document.documentElement.classList.toggle("dark", dark);
}

/** themes.css swaps the tokens under `.dark`. "system" follows the OS, live. */
export function setTheme(next: ThemeChoice) {
  choice = next;
  apply();
}

export function initTheme() {
  apply();
  darkQuery.addEventListener("change", apply);
}
