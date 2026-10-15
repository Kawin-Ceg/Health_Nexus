import { useEffect, useState } from "react";
import { Banner } from "../auth/Banner";
import { Checkbox } from "../ui/Checkbox/Checkbox";
import { Field } from "../ui/Field/Field";
import { Select } from "../ui/Select/Select";
import { TagInput } from "../ui/TagInput/TagInput";
import type { useForm } from "../../lib/useForm";
import type { OnboardingValues } from "../../lib/onboardingDraft";
import { PHONE_HINT } from "../../lib/validation";
import { errorMessage } from "../../services/api";
import { BLOOD_GROUPS, getDistricts, getFacilities, getStates } from "../../services/onboarding";
import styles from "./Onboarding.module.css";

export type OnboardingForm = ReturnType<typeof useForm<OnboardingValues>>;

const GENDERS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

export function PersonalStep({ form }: { form: OnboardingForm }) {
  return (
    <div className={styles.grid}>
      <Field label="Age" inputMode="numeric" autoComplete="off" hint="In years" {...form.field("age")} />
      <Select label="Gender" options={GENDERS} placeholder="Choose" {...form.field("gender")} />
      <Field label="Height (cm)" inputMode="decimal" autoComplete="off" {...form.field("height_cm")} />
      <Field label="Weight (kg)" inputMode="decimal" autoComplete="off" {...form.field("weight_kg")} />
      <Select
        label="Blood group (optional)"
        options={BLOOD_GROUPS.map((g) => ({ value: g, label: g }))}
        placeholder="Not sure"
        className={styles.span}
        {...form.field("blood_group")}
      />
    </div>
  );
}

interface Loaded<T> {
  data: T[];
  loading: boolean;
  error: string | null;
}

/** Loads a registry list. `load` is null while its prerequisite choice is missing; `key` changes when it should reload. */
function useRegistryList<T>(load: (() => Promise<T[]>) | null, key: string, attempt: number): Loaded<T> {
  const [result, setResult] = useState<Loaded<T>>({ data: [], loading: false, error: null });

  useEffect(() => {
    if (!load) {
      setResult({ data: [], loading: false, error: null });
      return;
    }
    let cancelled = false;
    setResult({ data: [], loading: true, error: null });
    load()
      .then((data) => {
        if (!cancelled) setResult({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (!cancelled) setResult({ data: [], loading: false, error: errorMessage(error) });
      });
    return () => {
      cancelled = true; // a slower, older response must not overwrite a newer choice
    };
    // `load` is rebuilt every render; `key` and `attempt` say when it actually changes.
  }, [key, attempt]); // eslint-disable-line react-hooks/exhaustive-deps

  return result;
}

/** State → district → health centre. Each list loads from the choice before it. */
export function LocationStep({ form }: { form: OnboardingForm }) {
  const { state, district, phc_id } = form.values;
  const { setValue } = form;
  const [attempt, setAttempt] = useState(0);

  const states = useRegistryList(() => getStates(), "states", attempt);
  const districts = useRegistryList(state ? () => getDistricts(state) : null, state, attempt);
  const facilities = useRegistryList(state && district ? () => getFacilities(state, district) : null, `${state}|${district}`, attempt);

  // A remembered choice (restored after a reload) that the registry no longer offers must not survive.
  useEffect(() => {
    if (!states.loading && states.data.length && state && !states.data.includes(state)) setValue("state", "");
  }, [states.loading, states.data, state, setValue]);
  useEffect(() => {
    if (!districts.loading && districts.data.length && district && !districts.data.includes(district)) setValue("district", "");
  }, [districts.loading, districts.data, district, setValue]);
  useEffect(() => {
    if (!facilities.loading && facilities.data.length && phc_id && !facilities.data.some((f) => f.id === phc_id)) {
      setValue("phc_id", "");
    }
  }, [facilities.loading, facilities.data, phc_id, setValue]);

  const loadError = states.error ?? districts.error ?? facilities.error;
  const stateField = form.field("state");
  const districtField = form.field("district");
  const centreField = form.field("phc_id");
  const chosenCentre = facilities.data.find((f) => f.id === phc_id);

  return (
    <div className={styles.grid}>
      {loadError && (
        <div className={styles.span}>
          <Banner tone="error">
            {loadError}{" "}
            <button type="button" className={styles.inlineLink} onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          </Banner>
        </div>
      )}
      {!states.loading && !states.error && states.data.length === 0 && (
        <div className={styles.span}>
          <Banner tone="info">
            No health centres are registered yet, so onboarding cannot be completed. Please check back soon.
          </Banner>
        </div>
      )}

      <Select
        label="State"
        options={states.data.map((s) => ({ value: s, label: s }))}
        placeholder={states.loading ? "Loading" : "Choose state"}
        disabled={states.data.length === 0}
        {...stateField}
        onChange={(e) => {
          stateField.onChange(e);
          setValue("district", "");
          setValue("phc_id", "");
        }}
      />
      <Select
        label="District"
        options={districts.data.map((d) => ({ value: d, label: d }))}
        placeholder={districts.loading ? "Loading" : "Choose district"}
        disabled={districts.data.length === 0}
        {...districtField}
        onChange={(e) => {
          districtField.onChange(e);
          setValue("phc_id", "");
        }}
      />
      <Select
        label="Health centre"
        options={facilities.data.map((f) => ({
          value: f.id,
          // Staffing is shown in the option itself: choosing a centre with no
          // worker means nobody reviews your readings, and finding that out on
          // the dashboard afterwards is too late.
          label: `${f.block ? `${f.name} (${f.block})` : f.name} - ${
            f.workers_assigned > 0
              ? `${f.workers_assigned} health worker${f.workers_assigned > 1 ? "s" : ""}`
              : "no health worker yet"
          }`,
        }))}
        placeholder={facilities.loading ? "Loading" : "Choose your health centre"}
        disabled={facilities.data.length === 0}
        hint={
          chosenCentre && chosenCentre.workers_assigned === 0
            ? "No health worker is assigned to this centre yet, so your readings will not be reviewed. You can still choose it and change it later in Settings."
            : "The clinic that will follow your care. Pick the one you would actually visit."
        }
        className={styles.span}
        {...centreField}
      />
      <Field label="Pincode" inputMode="numeric" autoComplete="postal-code" maxLength={6} {...form.field("pincode")} />
      <Field label="Area or locality" autoComplete="address-level3" {...form.field("area")} />
    </div>
  );
}

export function MedicalStep({ form }: { form: OnboardingForm }) {
  return (
    <div className={styles.stack}>
      <TagInput
        label="Existing conditions"
        values={form.values.existing_conditions}
        onChange={(v) => form.setValue("existing_conditions", v)}
        placeholder="For example asthma, then Enter"
        hint="Optional. Add up to 10."
      />
      <TagInput
        label="Current medications"
        values={form.values.current_medications}
        onChange={(v) => form.setValue("current_medications", v)}
        placeholder="For example metformin 500 mg, then Enter"
        hint="Optional. Add up to 10."
      />
    </div>
  );
}

export function DeviceStep({ form }: { form: OnboardingForm }) {
  const hasWatch = form.values.has_smartwatch;
  const watch = form.checkbox("has_smartwatch");
  return (
    <div className={styles.grid}>
      <div className={styles.span}>
        <Checkbox
          label="I use a smartwatch or fitness band"
          {...watch}
          onChange={(e) => {
            watch.onChange(e);
            if (!e.target.checked) form.setValue("smartwatch_brand", ""); // never keep a brand for a watch that is not there
          }}
        />
      </div>
      {hasWatch && (
        <Field label="Brand (optional)" placeholder="For example Noise, Fitbit" className={styles.span} {...form.field("smartwatch_brand")} />
      )}
      <p className={`${styles.span} ${styles.sectionTitle}`}>Emergency contact</p>
      <Field label="Contact name" autoComplete="off" {...form.field("emergency_contact_name")} />
      <Field
        label="Contact phone"
        type="tel"
        autoComplete="off"
        hint={PHONE_HINT}
        {...form.field("emergency_contact_phone")}
      />
      <p className={`${styles.span} ${styles.muted}`}>Optional, but if you add one, add both the name and the number.</p>
    </div>
  );
}

export function ConsentStep({ form }: { form: OnboardingForm }) {
  return (
    <div className={styles.stack}>
      <p className={styles.muted}>
        Choose what you are comfortable with. Leaving a box empty means no.
      </p>
      <Checkbox
        label="Health tracking"
        description="Allow HealthNexus to store the readings you record and use them to show your trends and flag unusual values."
        {...form.checkbox("health_tracking")}
      />
      <Checkbox
        label="Health worker access"
        description="Let health workers at the centre you chose see your readings and contact details, so they can follow up on a flag and book a home visit."
        {...form.checkbox("phc_worker_access")}
      />
      <Checkbox
        label="Community health surveillance"
        description="Allow your readings, combined with others in your area, to help your health centre spot outbreaks early."
        {...form.checkbox("community_surveillance")}
      />
    </div>
  );
}
