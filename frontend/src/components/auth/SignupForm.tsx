import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { isValidEmployeeId } from "../../lib/patterns";
import { destinationFor, paths } from "../../lib/routes";
import { useForm } from "../../lib/useForm";
import { emailError, integerInRange, newPasswordError, required } from "../../lib/validation";
import { ApiError } from "../../services/api";
import { DESIGNATIONS, registerCitizen, registerPhcWorker, type Designation } from "../../services/auth";
import { Banner } from "./Banner";
import { PasswordChecklist } from "./PasswordChecklist";
import { Button } from "../ui/Button/Button";
import { Field } from "../ui/Field/Field";
import { Select } from "../ui/Select/Select";
import styles from "./Auth.module.css";

const EMPLOYEE_ID_HINT = "Issuing body, area and number, for example TNPHC-CHN-2847";
const EMAIL_TAKEN = /already exists/i;

type Name = "name" | "email" | "password" | "employee_id" | "designation" | "phc_name" | "district" | "state" | "years_of_service";

const PHC_STEPS: { title: string; fields: Name[] }[] = [
  { title: "Your account", fields: ["name", "email", "password"] },
  { title: "Your role", fields: ["employee_id", "designation", "years_of_service"] },
  { title: "Your health centre", fields: ["phc_name", "district", "state"] },
];
const CITIZEN_STEPS: { title: string; fields: Name[] }[] = [{ title: "Your account", fields: ["name", "email", "password"] }];

export function SignupForm({ variant }: { variant: "citizen" | "phc" }) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const phc = variant === "phc";
  const steps = phc ? PHC_STEPS : CITIZEN_STEPS;
  const [step, setStep] = useState(0);
  const stepHeading = useRef<HTMLHeadingElement>(null);
  const checklistId = useId();

  const form = useForm(
    {
      name: "",
      email: "",
      password: "",
      employee_id: "",
      designation: "",
      phc_name: "",
      district: "",
      state: "",
      years_of_service: "",
    },
    (v) => ({
      name: required("Full name", v.name),
      email: emailError(v.email),
      password: newPasswordError(v.password),
      ...(phc && {
        employee_id: !v.employee_id.trim()
          ? "Employee ID is required"
          : isValidEmployeeId(v.employee_id.trim())
            ? undefined
            : "Use capital letters and digits, like TNPHC-CHN-2847",
        designation: v.designation ? undefined : "Choose your designation",
        phc_name: required("Health centre name", v.phc_name),
        district: required("District", v.district),
        state: required("State", v.state),
        years_of_service: integerInRange("Years of service", v.years_of_service, 0, 60),
      }),
    }),
  );

  const { serverErrors } = form;
  useEffect(() => {
    const failed = steps.findIndex((s) => s.fields.some((f) => serverErrors[f]));
    if (failed !== -1) setStep((current) => Math.min(current, failed));
  }, [serverErrors, steps]);

  const [moved, setMoved] = useState(false);
  useEffect(() => {
    if (moved) stepHeading.current?.focus();
  }, [step, moved]);

  const goTo = (next: number) => {
    setMoved(true);
    setStep(next);
  };

  const live = (name: Name) => {
    const props = form.field(name);
    const valid = !form.problems[name];
    return { ...props, required: true, success: valid && props.value ? "Looks good" : undefined };
  };

  const submit = form.handleSubmit(async (v) => {
    const base = { name: v.name.trim(), email: v.email.trim(), password: v.password };
    try {
      if (phc) {
        await registerPhcWorker({
          ...base,
          employee_id: v.employee_id.trim(),
          designation: v.designation as Designation,
          phc_name: v.phc_name.trim(),
          district: v.district.trim(),
          state: v.state.trim(),
          years_of_service: Number(v.years_of_service),
        });
      } else {
        await registerCitizen(base);
      }
    } catch (error) {
      if (error instanceof ApiError && EMAIL_TAKEN.test(error.detail)) {
        throw new ApiError(error.status, error.detail, { email: error.detail });
      }
      throw error;
    }
    try {
      const user = await login(base.email, base.password);
      navigate(destinationFor(user), { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        navigate(paths.login, { replace: true, state: { notice: "Account created. Sign in to continue." } });
        return;
      }
      throw error;
    }
  });

  const last = step === steps.length - 1;

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    if (!last) {
      event.preventDefault();
      if (!form.check(steps[step].fields)) goTo(step + 1);
      return;
    }
    const earlier = steps.findIndex((s, i) => i < step && s.fields.some((f) => form.problems[f]));
    if (earlier !== -1) {
      event.preventDefault();
      form.touch(steps[earlier].fields);
      goTo(earlier);
      return;
    }
    void submit(event);
  };

  const password = live("password");
  const employeeId = live("employee_id");

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {steps.length > 1 && (
        <div className={styles.stepper}>
          <ol className={styles.progress} aria-label="Progress">
            {steps.map((s, i) => (
              <li key={s.title} className={i <= step ? styles.done : undefined} aria-current={i === step ? "step" : undefined}>
                <span className="visually-hidden">
                  Step {i + 1}: {s.title}
                </span>
              </li>
            ))}
          </ol>
          <p className={styles.stepCount}>
            Step {step + 1} of {steps.length}
          </p>
          <h2 ref={stepHeading} tabIndex={-1} className={styles.stepTitle}>
            {steps[step].title}
          </h2>
        </div>
      )}

      {form.formError && <Banner tone="error">{form.formError}</Banner>}

      {step === 0 && (
        <div className={styles.grid}>
          <Field label="Full name" autoComplete="name" {...live("name")} />
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            inputMode="email"
            {...live("email")}
          />
          <Field
            label="Password"
            type="password"
            revealable
            autoComplete="new-password"
            className={styles.span}
            {...password}
            success={undefined}
            aria-describedby={checklistId}
          />
          <div className={styles.span}>
            <PasswordChecklist value={form.values.password} id={checklistId} />
          </div>
        </div>
      )}

      {phc && step === 1 && (
        <div className={styles.grid}>
          <Field
            label="Employee ID"
            autoComplete="off"
            spellCheck={false}
            placeholder="TNPHC-CHN-2847"
            hint={EMPLOYEE_ID_HINT}
            className={styles.span}
            {...employeeId}
            onChange={(e) => form.setValue("employee_id", e.target.value.toUpperCase())}
          />
          <Select
            label="Designation"
            options={DESIGNATIONS}
            placeholder="Choose designation"
            {...live("designation")}
          />
          <Field label="Years of service" inputMode="numeric" {...live("years_of_service")} />
        </div>
      )}

      {phc && step === 2 && (
        <div className={styles.grid}>
          <Field
            label="Health centre name"
            hint="As it appears on your appointment order, e.g. Mylapore PHC"
            className={styles.span}
            {...live("phc_name")}
          />
          <Field label="District" autoComplete="address-level2" {...live("district")} />
          <Field label="State" autoComplete="address-level1" {...live("state")} />
        </div>
      )}

      <div className={styles.stepActions}>
        {step > 0 && (
          <Button type="button" variant="secondary" size="lg" onClick={() => goTo(step - 1)}>
            <ArrowLeft size={18} aria-hidden="true" />
            Back
          </Button>
        )}
        <Button type="submit" size="lg" fullWidth={step === 0} loading={form.submitting} className={styles.grow}>
          {!last ? "Continue" : form.submitting ? "Creating account" : phc ? "Send application" : "Create account"}
          {!last && <ArrowRight size={18} aria-hidden="true" />}
        </Button>
      </div>
    </form>
  );
}
