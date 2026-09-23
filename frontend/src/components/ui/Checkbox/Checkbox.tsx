import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import styles from "./Checkbox.module.css";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: ReactNode;
  description?: ReactNode;
  error?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, description, error, className, ...input },
  ref,
) {
  const id = useId();
  const describedBy = [description && `${id}-desc`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className ? `${styles.wrap} ${className}` : styles.wrap}>
      <label htmlFor={id} className={styles.row}>
        <input
          {...input}
          ref={ref}
          id={id}
          type="checkbox"
          className={styles.box}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
        <span className={styles.text}>
          <span className={styles.label}>{label}</span>
          {description && (
            <span id={`${id}-desc`} className={styles.description}>
              {description}
            </span>
          )}
        </span>
      </label>
      {error && (
        <p id={`${id}-error`} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
});
