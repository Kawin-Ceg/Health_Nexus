import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";
import styles from "./Field.module.css";

interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: string;
  /** One clear message, shown after the field has been touched. */
  error?: string;
  hint?: ReactNode;
  /** Adds a show/hide toggle. Only meaningful with type="password". */
  revealable?: boolean;
  /** A control beside the label, such as a "Forgot password?" link. */
  labelAside?: ReactNode;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, revealable, labelAside, type = "text", className, ...input },
  ref,
) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const describedBy = [error && `${id}-error`, hint && !error && `${id}-hint`].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className ? `${styles.field} ${className}` : styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={id} className={styles.label}>
          {label}
        </label>
        {labelAside}
      </div>
      <div className={styles.control}>
        <input
          {...input}
          ref={ref}
          id={id}
          type={revealable && revealed ? "text" : type}
          className={revealable ? `${styles.input} ${styles.padded}` : styles.input}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
        {revealable && (
          <button
            type="button"
            className={styles.reveal}
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide password" : "Show password"}
            aria-pressed={revealed}
          >
            {revealed ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
          </button>
        )}
      </div>
      {hint && !error && (
        <p id={`${id}-hint`} className={styles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
});
