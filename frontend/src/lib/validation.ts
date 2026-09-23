// Each rule returns one message, or undefined when the value is fine. They mirror the API's rules
// so most mistakes are caught on blur; the server stays the authority.

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const required = (label: string, value: string): string | undefined =>
  value.trim() ? undefined : `${label} is required`;

export function emailError(value: string): string | undefined {
  const v = value.trim();
  if (!v) return "Email is required";
  return v.length > 254 || !EMAIL_RE.test(v) ? "Enter a valid email address" : undefined;
}

export function newPasswordError(value: string): string | undefined {
  if (!value) return "Password is required";
  if (value.length < 8) return "Use at least 8 characters";
  // bcrypt only reads 72 bytes; the API refuses longer passwords rather than truncate.
  if (new TextEncoder().encode(value).length > 72) return "Use at most 72 bytes (about 72 characters)";
  return undefined;
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
