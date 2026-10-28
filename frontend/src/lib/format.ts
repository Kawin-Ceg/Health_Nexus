export const TIME_ZONE = "Asia/Kolkata";

const dateOnly = new Intl.DateTimeFormat("en-IN", { timeZone: TIME_ZONE, day: "numeric", month: "short", year: "numeric" });
const shortDay = new Intl.DateTimeFormat("en-IN", { timeZone: TIME_ZONE, day: "numeric", month: "short" });

export const fmtDateTime = (iso: string) => fmtStamp(iso);
export const fmtDate = (iso: string) => dateOnly.format(new Date(iso));
export const fmtShortDay = (iso: string) => shortDay.format(new Date(iso));
export const fmtVisit = (iso: string) => fmtStamp(iso);

const stampDay = new Intl.DateTimeFormat("en-IN", { timeZone: TIME_ZONE, weekday: "short", day: "numeric", month: "short", year: "numeric" });
const stampTime = new Intl.DateTimeFormat("en-IN", { timeZone: TIME_ZONE, hour: "numeric", minute: "2-digit" });
export const fmtStamp = (iso: string) => `${stampDay.format(new Date(iso))} · ${stampTime.format(new Date(iso))}`;

export function fmtSpan(fromIso: string, to: number = Date.now()): string {
  const mins = Math.max(0, Math.round((to - new Date(fromIso).getTime()) / 60000));
  if (mins < 60) return `${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"}`;
  const days = Math.round(hours / 24);
  return `${days} days`;
}

export function fmtAgo(iso: string | null): string {
  if (!iso) return "never";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export const plural = (n: number, word: string, many = `${word}s`) => `${n.toLocaleString("en-IN")} ${n === 1 ? word : many}`;

export function fmtValue(value: number, decimals: number): string {
  return value.toFixed(decimals);
}

export function toLocalInput(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

export const fromLocalInput = (value: string) => `${value}:00+05:30`;
