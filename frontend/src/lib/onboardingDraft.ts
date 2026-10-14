/**
 * Onboarding answers survive a reload in sessionStorage: per tab, gone when the tab
 * closes, and cleared on sign-out. Auth tokens never go here (see services/api.ts).
 */

export type OnboardingValues = {
  age: string;
  gender: string;
  height_cm: string;
  weight_kg: string;
  blood_group: string;
  state: string;
  district: string;
  phc_id: string;
  pincode: string;
  area: string;
  existing_conditions: string[];
  current_medications: string[];
  has_smartwatch: boolean;
  smartwatch_brand: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  health_tracking: boolean;
  community_surveillance: boolean;
  phc_worker_access: boolean;
};

export const EMPTY_ONBOARDING: OnboardingValues = {
  age: "",
  gender: "",
  height_cm: "",
  weight_kg: "",
  blood_group: "",
  state: "",
  district: "",
  phc_id: "",
  pincode: "",
  area: "",
  existing_conditions: [],
  current_medications: [],
  has_smartwatch: false,
  smartwatch_brand: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  health_tracking: false,
  community_surveillance: false,
  phc_worker_access: false,
};

const PREFIX = "hn.onboarding.";
const keyFor = (userId: string) => `${PREFIX}${userId}`;

export function loadDraft(userId: string): OnboardingValues {
  try {
    const saved = JSON.parse(sessionStorage.getItem(keyFor(userId)) ?? "null") as Partial<OnboardingValues> | null;
    if (!saved || typeof saved !== "object") return EMPTY_ONBOARDING;
    // Keep only known keys whose type matches, so a stale or edited draft cannot break the form.
    const merged = { ...EMPTY_ONBOARDING };
    for (const key of Object.keys(EMPTY_ONBOARDING) as (keyof OnboardingValues)[]) {
      const value = saved[key];
      const expected = EMPTY_ONBOARDING[key];
      const ok = Array.isArray(expected)
        ? Array.isArray(value) && value.every((v) => typeof v === "string")
        : typeof value === typeof expected;
      if (ok) (merged as Record<string, unknown>)[key] = value;
    }
    return merged;
  } catch {
    return EMPTY_ONBOARDING;
  }
}

export function saveDraft(userId: string, values: OnboardingValues): void {
  try {
    sessionStorage.setItem(keyFor(userId), JSON.stringify(values));
  } catch {
    // Storage full or blocked: the form still works, it just will not survive a reload.
  }
}

export function clearDrafts(): void {
  try {
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith(PREFIX))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // Nothing to clear.
  }
}
