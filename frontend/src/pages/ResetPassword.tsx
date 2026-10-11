import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Banner } from "../components/auth/Banner";
import { PasswordChecklist } from "../components/auth/PasswordChecklist";
import { Button } from "../components/ui/Button/Button";
import { Field } from "../components/ui/Field/Field";
import { paths } from "../lib/routes";
import { useForm } from "../lib/useForm";
import { newPasswordError } from "../lib/validation";
import { resetPassword } from "../services/auth";
import styles from "../components/auth/Auth.module.css";

export function ResetPassword() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  // Read once into state: the link's token should not stay in the address bar or history.
  const [token] = useState(() => params.get("token"));
  useEffect(() => setParams({}, { replace: true }), [setParams]);

  const form = useForm({ password: "", confirm: "" }, (v) => ({
    password: newPasswordError(v.password),
    confirm: v.confirm === v.password ? undefined : "The passwords do not match",
  }));

  const onSubmit = form.handleSubmit(async ({ password }) => {
    await resetPassword(token ?? "", password);
    navigate(paths.login, { replace: true, state: { notice: "Password updated. Sign in with your new password." } });
  });

  if (!token) {
    return (
      <AuthLayout title="This link is not valid" footer={<Link to={paths.login}>Back to sign in</Link>}>
        <div className={styles.stack}>
          <Banner tone="error">The reset link is missing its code. Open the link from your email again.</Banner>
          <Button to={paths.forgotPassword}>Request a new link</Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Choose a new password"
      subtitle="You will be signed out of every device."
      footer={<Link to={paths.login}>Back to sign in</Link>}
    >
      <form className={styles.form} onSubmit={onSubmit} noValidate>
        {form.formError && (
          <Banner tone="error">
            {form.formError}{" "}
            <Link to={paths.forgotPassword} className={styles.link}>
              Request a new link
            </Link>
          </Banner>
        )}
        <Field
          label="New password"
          type="password"
          revealable
          autoComplete="new-password"
          required
          aria-describedby="reset-password-rules"
          {...form.field("password")}
        />
        <PasswordChecklist value={form.values.password} id="reset-password-rules" />
        <Field
          label="Confirm new password"
          type="password"
          revealable
          autoComplete="new-password"
          required
          {...form.field("confirm")}
          success={form.values.confirm && !form.problems.confirm ? "Passwords match" : undefined}
        />
        <Button type="submit" size="lg" fullWidth loading={form.submitting}>
          {form.submitting ? "Saving" : "Set new password"}
        </Button>
      </form>
    </AuthLayout>
  );
}
