import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { CircleCheck, Eye, EyeOff } from "lucide-react";
import styles from "./Field.module.css";

interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: string;
  error?: string;
  hint?: ReactNode;
  revealable?: boolean;
  labelAside?: ReactNode;
  success?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, revealable, labelAside, success, type = "text", className, "aria-describedby": extraDescribedBy, ...input },
  ref,
) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const ok = !error && success;
  const describedBy =
    [error && `${id}-error`, ok && `${id}-ok`, hint && !error && `${id}-hint`, extraDescribedBy].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className ? `${styles.field} ${className}` : styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={id} className={styles.label}>
          {label}
          {input.required && (
            <span className={styles.required}>
              <span aria-hidden="true"> *</span>
              <span className="visually-hidden"> (required)</span>
            </span>
          )}
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
          aria-required={input.required || undefined}
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
      {ok && (
        <p id={`${id}-ok`} className={styles.success}>
          <CircleCheck size={14} aria-hidden="true" />
          {success}
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
