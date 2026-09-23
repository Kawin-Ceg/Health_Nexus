import { useCallback, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { ApiError, errorMessage } from "../services/api";

type Values = Record<string, string | boolean | string[]>;
type Errors<T> = Partial<Record<keyof T & string, string>>;

/**
 * Small form state: inline validation on blur, one message per field, server 422s
 * mapped back onto their inputs, and a submitting flag for the button's loading state.
 */
export function useForm<T extends Values>(initial: T, validate: (values: T) => Errors<T>) {
  const [values, setValues] = useState<T>(initial);
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [serverErrors, setServerErrors] = useState<Errors<T>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const problems = validate(values);
  const errorFor = (name: keyof T & string) => (touched.has(name) ? (problems[name] ?? serverErrors[name]) : undefined);

  const touch = useCallback((names: string[]) => setTouched((prev) => new Set([...prev, ...names])), []);

  const setValue = useCallback(<K extends keyof T & string>(name: K, value: T[K]) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setServerErrors((prev) => (prev[name] ? { ...prev, [name]: undefined } : prev));
  }, []);

  const field = (name: keyof T & string) => ({
    name,
    value: values[name] as string,
    error: errorFor(name),
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setValue(name, event.target.value as T[typeof name]),
    onBlur: () => touch([name]),
  });

  const checkbox = (name: keyof T & string) => ({
    name,
    checked: values[name] as boolean,
    error: errorFor(name),
    onChange: (event: ChangeEvent<HTMLInputElement>) => setValue(name, event.target.checked as T[typeof name]),
    onBlur: () => touch([name]),
  });

  /** Marks the given fields (default all) as touched; true if any of them has a problem. */
  const check = (names: (keyof T & string)[] = Object.keys(values)): boolean => {
    touch(names);
    const bad = names.some((n) => problems[n]);
    if (bad) {
      // Wait a frame so the error markup exists, then move focus to the first bad input.
      requestAnimationFrame(() => {
        const scope = formRef.current ?? document;
        scope.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
      });
    }
    return bad;
  };

  const handleSubmit = (submit: (values: T) => Promise<void>) => async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    formRef.current = event.currentTarget;
    if (submitting || check()) return;
    setFormError(null);
    setSubmitting(true);
    try {
      await submit(values);
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
        const known = Object.keys(error.fieldErrors).filter((k) => k in values);
        if (known.length) {
          setServerErrors(Object.fromEntries(known.map((k) => [k, error.fieldErrors[k]])) as Errors<T>);
          touch(known);
        }
        setFormError(known.length ? null : error.detail);
      } else {
        setFormError(errorMessage(error));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return {
    values,
    setValue,
    field,
    checkbox,
    check,
    touch,
    problems,
    serverErrors,
    handleSubmit,
    submitting,
    formError,
    setFormError,
    formRef,
  };
}
