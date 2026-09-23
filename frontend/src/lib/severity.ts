import { AlertOctagon, AlertTriangle, CircleAlert, Info, type LucideIcon } from "lucide-react";

export type Severity = "critical" | "high" | "moderate" | "low";

export const SEVERITIES: Severity[] = ["critical", "high", "moderate", "low"];

/**
 * The one definition of how a severity looks. A severity drawn differently on
 * two pages reads as two different severities, so every page imports this.
 * Colour is never the only signal: each band has a label and an icon too.
 */
export const SEVERITY: Record<Severity, { label: string; icon: LucideIcon; text: string; badge: string; dot: string }> = {
  critical: {
    label: "Critical",
    icon: AlertOctagon,
    text: "text-sev-critical",
    badge: "bg-sev-critical/12 text-sev-critical ring-1 ring-sev-critical/30",
    dot: "bg-sev-critical",
  },
  high: {
    label: "High",
    icon: AlertTriangle,
    text: "text-sev-high",
    badge: "bg-sev-high/12 text-sev-high ring-1 ring-sev-high/30",
    dot: "bg-sev-high",
  },
  moderate: {
    label: "Moderate",
    icon: CircleAlert,
    text: "text-sev-moderate",
    badge: "bg-sev-moderate/12 text-sev-moderate ring-1 ring-sev-moderate/30",
    dot: "bg-sev-moderate",
  },
  low: {
    label: "Low",
    icon: Info,
    text: "text-sev-low",
    badge: "bg-sev-low/12 text-sev-low ring-1 ring-sev-low/30",
    dot: "bg-sev-low",
  },
};

export const isSeverity = (value: unknown): value is Severity =>
  typeof value === "string" && (SEVERITIES as string[]).includes(value);
