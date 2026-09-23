import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { isValidEmployeeId } from "../../lib/patterns";
import { destinationFor, paths } from "../../lib/routes";
import { useForm } from "../../lib/useForm";
import { emailError, integerInRange, newPasswordError, required } from "../../lib/validation";
import { ApiError } from "../../services/api";
import { DESIGNATIONS, registerCitizen, registerPhcWorker, type Designation } from "../../services/auth";
import { Banner } from "./Banner";
import { Button } from "../ui/Button/Button";
import { Field } from "../ui/Field/Field";
import { Select } from "../ui/Select/Select";
import styles from "./Auth.module.css";

const EMPLOYEE_ID_HINT = "Issuing body, area and number, for example TNPHC-CHN-2847";

/** One form for both sign-ups; `phc` adds the worker's details. */
export function SignupForm({ variant }: { variant: "citizen" | "phc" }) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const phc = variant === "phc";

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
      name: required("Name", v.name),
      email: emailError(v.email),
      password: newPasswordError(v.password),
      ...(phc && {
        employee_id: !v.employee_id.trim()
          ? "Employee ID is required"
          : isValidEmployeeId(v.employee_id.trim())
            ? undefined
            : "Use capital letters and digits, like TNPHC-CHN-2847",
        designation: v.designation ? undefined : "Choose your designation",
        phc_name: required("PHC name", v.phc_name),
        district: required("District", v.district),
        state: required("State", v.state),
        years_of_service: integerInRange("Years of service", v.years_of_service, 0, 60),
      }),
    }),
  );

  const onSubmit = form.handleSubmit(async (v) => {
    const base = { name: v.name.trim(), email: v.email.trim(), password: v.password };
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
    // Sign in straight away: the next screen ("check your inbox") needs a session to resend the email.
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

  const employeeId = form.field("employee_id");

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {form.formError && <Banner tone="error">{form.formError}</Banner>}
      <div className={styles.grid}>
        <Field label="Full name" autoComplete="name" className={styles.span} {...form.field("name")} />
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          inputMode="email"
          className={styles.span}
          {...form.field("email")}
        />
        <Field
          label="Password"
          type="password"
          revealable
          autoComplete="new-password"
          hint="At least 8 characters"
          className={styles.span}
          {...form.field("password")}
        />
        {phc && (
          <>
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
              className={styles.span}
              {...form.field("designation")}
            />
            <Field label="PHC name" className={styles.span} {...form.field("phc_name")} />
            <Field label="District" {...form.field("district")} />
            <Field label="State" {...form.field("state")} />
            <Field
              label="Years of service"
              inputMode="numeric"
              className={styles.span}
              {...form.field("years_of_service")}
            />
          </>
        )}
      </div>
      <Button type="submit" size="lg" fullWidth loading={form.submitting}>
        {form.submitting ? "Creating account" : phc ? "Apply as PHC worker" : "Create account"}
      </Button>
    </form>
  );
}
