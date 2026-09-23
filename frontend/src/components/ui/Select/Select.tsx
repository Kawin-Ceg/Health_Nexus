import { forwardRef, useId, type ReactNode, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import fieldStyles from "../Field/Field.module.css";
import styles from "./Select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  placeholder?: string;
  error?: string;
  hint?: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, placeholder = "Select", error, hint, className, ...select },
  ref,
) {
  const id = useId();
  const describedBy = [error && `${id}-error`, hint && !error && `${id}-hint`].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className ? `${fieldStyles.field} ${className}` : fieldStyles.field}>
      <label htmlFor={id} className={fieldStyles.label}>
        {label}
      </label>
      <div className={styles.wrap}>
        <select
          {...select}
          ref={ref}
          id={id}
          className={styles.select}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        >
          <option value="">{placeholder}</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className={styles.chevron} size={18} aria-hidden="true" />
      </div>
      {hint && !error && (
        <p id={`${id}-hint`} className={fieldStyles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className={fieldStyles.error}>
          {error}
        </p>
      )}
    </div>
  );
});
