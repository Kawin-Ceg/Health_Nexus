import { CircleCheck, CircleX } from "lucide-react";
import { PASSWORD_RULES } from "../../lib/validation";
import styles from "./PasswordChecklist.module.css";

export function PasswordChecklist({ value, id }: { value: string; id: string }) {
  const met = PASSWORD_RULES.filter((rule) => rule.test(value)).length;
  return (
    <div id={id}>
      <ul className={styles.list} aria-label="Password rules">
        {PASSWORD_RULES.map((rule) => {
          const ok = rule.test(value);
          return (
            <li key={rule.label} className={ok ? styles.ok : styles.todo}>
              {ok ? <CircleCheck size={16} aria-hidden="true" /> : <CircleX size={16} aria-hidden="true" />}
              {rule.label}
              <span className="visually-hidden">{ok ? ": done" : ": not yet"}</span>
            </li>
          );
        })}
      </ul>
      <p className="visually-hidden" aria-live="polite">
        {met} of {PASSWORD_RULES.length} password rules met
      </p>
    </div>
  );
}
