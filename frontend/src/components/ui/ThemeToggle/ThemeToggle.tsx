import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";
import { isDark, onThemeChange, setTheme } from "../../../lib/theme";
import { updatePreferences } from "../../../services/account";

export function ThemeToggle({
  className,
  withLabel = false,
  labelClassName = "",
}: {
  className?: string;
  withLabel?: boolean;
  labelClassName?: string;
}) {
  const { user } = useAuth();
  const [dark, setDark] = useState(isDark);
  useEffect(() => onThemeChange(setDark), []);

  const toggle = () => {
    const next = dark ? "light" : "dark";
    setTheme(next);
    if (user && user.role !== "pending_phc") void updatePreferences({ theme: next }).catch(() => undefined);
  };

  const label = dark ? "Switch to light mode" : "Switch to dark mode";
  return (
    <button type="button" onClick={toggle} aria-label={label} title={label} className={className}>
      {dark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
      {withLabel && <span className={`flex-1 text-left ${labelClassName}`}>{dark ? "Light mode" : "Dark mode"}</span>}
    </button>
  );
}
