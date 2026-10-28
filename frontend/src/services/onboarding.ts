import { api } from "./api";

export type Gender = "male" | "female" | "other" | "prefer_not_to_say";
export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] as const;

export interface Facility {
  id: string;
  name: string;
  block: string | null;
  district: string;
  state: string;
  workers_assigned: number;
}

export interface ProfilePayload {
  age: number;
  gender: Gender;
  height_cm: number;
  weight_kg: number;
  blood_group: string | null;
  state: string;
  district: string;
  phc_id: string;
  pincode: string;
  area: string;
  existing_conditions: string[];
  current_medications: string[];
  has_smartwatch: boolean;
  smartwatch_brand: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  consents: { health_tracking: boolean; community_surveillance: boolean; phc_worker_access?: boolean | null };
}

export const getStates = () => api.get<string[]>("/onboarding/states").then((r) => r.data);

export const getDistricts = (state: string) =>
  api.get<string[]>("/onboarding/districts", { params: { state } }).then((r) => r.data);

export const getFacilities = (state: string, district: string) =>
  api.get<Facility[]>("/onboarding/facilities", { params: { state, district } }).then((r) => r.data);

export const createProfile = (body: ProfilePayload) => api.post("/onboarding/profile", body).then((r) => r.data);
