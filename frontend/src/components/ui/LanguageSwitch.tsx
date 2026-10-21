import { Languages } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { LANGUAGES, setLanguage, useLanguage, useT, type Lang } from "../../i18n";
import { updatePreferences } from "../../services/account";

/** Language picker for any page. Signed in, the choice is also saved to the account. */
export function LanguageSwitch({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { user } = useAuth();
  const lang = useLanguage();
  const t = useT();

  const choose = (next: Lang) => {
    setLanguage(next);
    if (user && user.role !== "pending_phc") void updatePreferences({ language: next }).catch(() => undefined);
  };

  if (compact) {
    const order = LANGUAGES.map((l) => l.value);
    const next = order[(order.indexOf(lang) + 1) % order.length];
    return (
      <button type="button" onClick={() => choose(next)} title={t("lang.label")} aria-label={t("lang.label")} className={className}>
        <Languages size={18} aria-hidden="true" />
      </button>
    );
  }

  return (
    <label className={className}>
      <Languages size={18} aria-hidden="true" className="shrink-0" />
      <span className="visually-hidden">{t("lang.label")}</span>
      <select
        value={lang}
        onChange={(e) => choose(e.target.value as Lang)}
        className="min-w-0 flex-1 cursor-pointer appearance-none bg-transparent text-sm font-medium text-inherit focus:outline-none"
      >
        {LANGUAGES.map((l) => (
          <option key={l.value} value={l.value}>{l.label}</option>
        ))}
      </select>
    </label>
  );
}
