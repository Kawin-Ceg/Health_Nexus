
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const required = (label: string, value: string): string | undefined =>
  value.trim() ? undefined : `${label} is required`;

export function emailError(value: string): string | undefined {
  const v = value.trim();
  if (!v) return "Email is required";
  return v.length > 254 || !EMAIL_RE.test(v) ? "Enter a valid email address" : undefined;
}

export const PASSWORD_RULES: { label: string; test: (value: string) => boolean }[] = [
  { label: "At least 8 characters", test: (v) => v.length >= 8 },
  { label: "At least one letter", test: (v) => /\p{L}/u.test(v) },
  { label: "At least one number", test: (v) => /\d/.test(v) },
  { label: "No more than 72 characters", test: (v) => new TextEncoder().encode(v).length <= 72 },
];

export function newPasswordError(value: string): string | undefined {
  if (!value) return "Password is required";
  const unmet = PASSWORD_RULES.find((rule) => !rule.test(value));
  return unmet ? `Password needs: ${unmet.label.toLowerCase()}` : undefined;
}

export function integerInRange(label: string, value: string, min: number, max: number): string | undefined {
  if (!value.trim()) return `${label} is required`;
  if (!/^\d+$/.test(value.trim())) return `${label} must be a whole number`;
  const n = Number(value);
  return n < min || n > max ? `${label} must be between ${min} and ${max}` : undefined;
}

export function numberInRange(label: string, value: string, min: number, max: number): string | undefined {
  if (!value.trim()) return `${label} is required`;
  const n = Number(value);
  if (!Number.isFinite(n)) return `${label} must be a number`;
  return n < min || n > max ? `${label} must be between ${min} and ${max}` : undefined;
}

export const PHONE_HINT = "Digits only, with an optional + and country code";

export function phoneError(value: string): string | undefined {
  return /^\+?[0-9]{7,15}$/.test(value.replace(/[\s\-()]/g, "")) ? undefined : "Enter a valid phone number";
}
