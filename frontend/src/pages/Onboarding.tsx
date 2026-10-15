import { useEffect, useRef, useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { AppHeader } from "../components/AppHeader";
import { Banner } from "../components/auth/Banner";
import {
  ConsentStep,
  DeviceStep,
  LocationStep,
  MedicalStep,
  PersonalStep,
} from "../components/onboarding/steps";
import { Button } from "../components/ui/Button/Button";
import { useAuth } from "../context/AuthContext";
import { clearDrafts, loadDraft, saveDraft, type OnboardingValues } from "../lib/onboardingDraft";
import { paths } from "../lib/routes";
import { useForm } from "../lib/useForm";
import { integerInRange, numberInRange, phoneError } from "../lib/validation";
import { ApiError } from "../services/api";
import { createProfile, type Gender, type ProfilePayload } from "../services/onboarding";
import styles from "../components/onboarding/Onboarding.module.css";
import { Doodle } from "../components/landing/Doodle/Doodle";
import { Check } from "lucide-react";

const STEPS = [
  { title: "About you", why: "Your health worker sees this on your record.", fields: ["age", "gender", "height_cm", "weight_kg", "blood_group"] },
  { title: "Location", why: "Links you to the health centre whose workers review your readings.", fields: ["state", "district", "phc_id", "pincode", "area"] },
  { title: "Medical history", why: "Conditions and medicines help your health worker read a flag in context.", fields: ["existing_conditions", "current_medications"] },
  { title: "Device and contact", why: "Your emergency contact is shown to your health worker.", fields: ["has_smartwatch", "smartwatch_brand", "emergency_contact_name", "emergency_contact_phone"] },
  { title: "Consent", why: "You can change these at any time in Settings.", fields: ["health_tracking", "phc_worker_access", "community_surveillance"] },
] as const satisfies readonly { title: string; why: string; fields: readonly (keyof OnboardingValues)[] }[];

type Problems = Partial<Record<keyof OnboardingValues, string>>;

// The same rules the API enforces, so most mistakes are caught before a request is made.
function validate(v: OnboardingValues): Problems {
  const name = v.emergency_contact_name.trim();
  const phone = v.emergency_contact_phone.trim();
  return {
    age: integerInRange("Age", v.age, 1, 120),
    gender: v.gender ? undefined : "Choose a gender",
    height_cm: numberInRange("Height", v.height_cm, 50, 300),
    weight_kg: numberInRange("Weight", v.weight_kg, 1, 300),
    state: v.state ? undefined : "Choose your state",
    district: v.district ? undefined : "Choose your district",
    phc_id: v.phc_id ? undefined : "Choose your health centre",
    pincode: /^\d{6}$/.test(v.pincode.trim()) ? undefined : "Enter a 6-digit pincode",
    area: !v.area.trim() ? "Area or locality is required" : v.area.trim().length > 120 ? "Use at most 120 characters" : undefined,
    smartwatch_brand: !v.has_smartwatch && v.smartwatch_brand.trim() ? "Tick the smartwatch box to add a brand" : undefined,
    emergency_contact_name: phone && !name ? "Add a name for this contact" : undefined,
    emergency_contact_phone: phone ? phoneError(phone) : name ? "Add a phone number for this contact" : undefined,
  };
}

const firstInvalidStep = (problems: Problems) =>
  STEPS.findIndex((s) => s.fields.some((f) => problems[f]));

const orNull = (s: string) => s.trim() || null;

function toPayload(v: OnboardingValues): ProfilePayload {
  return {
    age: Number(v.age),
    gender: v.gender as Gender,
    height_cm: Number(v.height_cm),
    weight_kg: Number(v.weight_kg),
    blood_group: orNull(v.blood_group),
    state: v.state,
    district: v.district,
    phc_id: v.phc_id,
    pincode: v.pincode.trim(),
    area: v.area.trim(),
    existing_conditions: v.existing_conditions,
    current_medications: v.current_medications,
    has_smartwatch: v.has_smartwatch,
    smartwatch_brand: v.has_smartwatch ? orNull(v.smartwatch_brand) : null,
    emergency_contact_name: orNull(v.emergency_contact_name),
    emergency_contact_phone: orNull(v.emergency_contact_phone),
    consents: {
      health_tracking: v.health_tracking,
      community_surveillance: v.community_surveillance,
      phc_worker_access: v.phc_worker_access,
    },
  };
}

/** A finished profile has nothing to do here. Kept apart from the flow so none of its effects run. */
export function Onboarding() {
  const { user } = useAuth();
  if (user?.profile_completed) return <Navigate to={paths.citizenHome} replace />;
  return <OnboardingFlow />;
}

function OnboardingFlow() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [draft] = useState(() => (user ? loadDraft(user.id) : loadDraft("")));

  const form = useForm<OnboardingValues>(draft, validate);
  const { values, serverErrors } = form;

  // Answers survive a reload. Once the profile is saved the draft must stay gone,
  // so the refreshed user (now completed) must not write it back.
  useEffect(() => {
    if (user && !user.profile_completed) saveDraft(user.id, values);
  }, [user, values]);

  // The URL holds the step, but never lets you skip past one that is not valid yet.
  const invalid = firstInvalidStep(form.problems);
  const furthest = invalid === -1 ? STEPS.length : invalid + 1;
  const requested = Number.parseInt(params.get("step") ?? "1", 10);
  const step = Math.min(Math.max(Number.isNaN(requested) ? 1 : requested, 1), furthest);

  useEffect(() => {
    if (String(step) !== params.get("step")) setParams({ step: String(step) }, { replace: true });
  }, [step, params, setParams]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  const goTo = (n: number) => setParams({ step: String(n) });

  // A 422 on a field from an earlier step: take the user to it.
  useEffect(() => {
    const bad = STEPS.findIndex((s) => s.fields.some((f) => serverErrors[f]));
    if (bad !== -1 && bad + 1 !== step) goTo(bad + 1);
    // goTo only sets the search params
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverErrors]);

  const finish = form.handleSubmit(async (v) => {
    try {
      await createProfile(toPayload(v));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        // Already saved, perhaps from another tab: nothing left to do here.
      } else {
        if (error instanceof ApiError && error.status === 422 && /health centre/i.test(error.detail)) goTo(2);
        throw error;
      }
    }
    clearDrafts();
    await refreshUser();
    navigate(paths.citizenHome, { replace: true });
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    if (step < STEPS.length) {
      event.preventDefault();
      if (!form.check([...STEPS[step - 1].fields])) goTo(step + 1);
      return;
    }
    if (invalid !== -1) {
      event.preventDefault();
      goTo(invalid + 1);
      return;
    }
    void finish(event);
  };

  const isLast = step === STEPS.length;

  return (
    <>
      <AppHeader />
      <main className={styles.main}>
        <aside className={styles.aside} aria-label="Setup steps">
          <Doodle piece="beads" className={styles.beads} />
          <Doodle piece="helix" className={styles.helix} delay={1} />
          <p className={styles.asideTitle}>Set up your health profile</p>
          <p className={styles.asideLead}>Five short steps. Your answers are kept if you reload this tab.</p>
          <ol className={styles.steps}>
            {STEPS.map((s, i) => {
              const n = i + 1;
              const state = n < step ? "done" : n === step ? "current" : "todo";
              return (
                <li key={s.title} className={styles[state]} aria-current={state === "current" ? "step" : undefined}>
                  <span className={styles.dot} aria-hidden="true">
                    {state === "done" ? <Check size={14} /> : n}
                  </span>
                  <span>
                    <span className={styles.stepName}>{s.title}</span>
                    {state === "current" && <span className={styles.why}>{s.why}</span>}
                    <span className="visually-hidden">{state === "done" ? " (done)" : state === "todo" ? " (to do)" : ""}</span>
                  </span>
                </li>
              );
            })}
          </ol>
        </aside>
        <div className={styles.card}>
          <div
            className={styles.progress}
            role="progressbar"
            aria-label="Onboarding progress"
            aria-valuemin={1}
            aria-valuemax={STEPS.length}
            aria-valuenow={step}
            aria-valuetext={`Step ${step} of ${STEPS.length}: ${STEPS[step - 1].title}`}
          >
            <div className={styles.fill} style={{ width: `${(step / STEPS.length) * 100}%` }} />
          </div>
          <p className={styles.stepLabel}>
            Step {step} of {STEPS.length}
          </p>
          <h1 ref={headingRef} tabIndex={-1} className={styles.title}>
            {STEPS[step - 1].title}
          </h1>

          <form onSubmit={onSubmit} noValidate className={styles.form}>
            {form.formError && <Banner tone="error">{form.formError}</Banner>}
            {step === 1 && <PersonalStep form={form} />}
            {step === 2 && <LocationStep form={form} />}
            {step === 3 && <MedicalStep form={form} />}
            {step === 4 && <DeviceStep form={form} />}
            {step === 5 && <ConsentStep form={form} />}

            <div className={styles.nav}>
              {step > 1 ? (
                <Button variant="secondary" size="lg" onClick={() => goTo(step - 1)}>
                  Back
                </Button>
              ) : (
                <span />
              )}
              <Button type="submit" size="lg" loading={form.submitting}>
                {isLast ? (form.submitting ? "Saving" : "Finish") : "Continue"}
              </Button>
            </div>
          </form>
        </div>
      </main>
    </>
  );
}
