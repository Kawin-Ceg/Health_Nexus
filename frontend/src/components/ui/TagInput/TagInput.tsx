import { useId, useState, type KeyboardEvent } from "react";
import { X } from "lucide-react";
import fieldStyles from "../Field/Field.module.css";
import styles from "./TagInput.module.css";

interface TagInputProps {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  max?: number;
  placeholder?: string;
  hint?: string;
  error?: string;
}

export function TagInput({ label, values, onChange, max = 10, placeholder, hint, error }: TagInputProps) {
  const id = useId();
  const [draft, setDraft] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const full = values.length >= max;

  const add = () => {
    const tag = draft.trim().replace(/,+$/, "").trim();
    if (!tag) return;
    if (values.some((v) => v.toLowerCase() === tag.toLowerCase())) {
      setNotice(`"${tag}" is already added.`);
    } else if (full) {
      setNotice(`You can add up to ${max}.`);
    } else {
      onChange([...values, tag.slice(0, 60)]);
      setNotice(null);
    }
    setDraft("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      add();
    } else if (event.key === "Backspace" && !draft && values.length) {
      onChange(values.slice(0, -1));
    }
  };

  const message = error ?? notice;
  return (
    <div className={fieldStyles.field}>
      <div className={fieldStyles.labelRow}>
        <label htmlFor={id} className={fieldStyles.label}>
          {label}
        </label>
        <span className={styles.count} aria-live="polite">
          {values.length}/{max}
        </span>
      </div>
      <div className={styles.box} data-invalid={error ? true : undefined}>
        {values.map((tag) => (
          <span key={tag} className={styles.tag}>
            {tag}
            <button
              type="button"
              className={styles.remove}
              onClick={() => onChange(values.filter((v) => v !== tag))}
              aria-label={`Remove ${tag}`}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          id={id}
          className={styles.input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={add}
          placeholder={full ? "Limit reached" : placeholder}
          disabled={full}
          maxLength={60}
        />
      </div>
      {message ? <p className={fieldStyles.error}>{message}</p> : hint && <p className={fieldStyles.hint}>{hint}</p>}
    </div>
  );
}
