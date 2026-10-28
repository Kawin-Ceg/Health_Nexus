import { useState } from "react";
import { Link } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Banner } from "../components/auth/Banner";
import { Button } from "../components/ui/Button/Button";
import { Field } from "../components/ui/Field/Field";
import { paths } from "../lib/routes";
import { useForm } from "../lib/useForm";
import { emailError } from "../lib/validation";
import { forgotPassword } from "../services/auth";
import styles from "../components/auth/Auth.module.css";

export function ForgotPassword() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useForm({ email: "" }, (v) => ({ email: emailError(v.email) }));

  const onSubmit = form.handleSubmit(async ({ email }) => {
    await forgotPassword(email.trim());
    setSentTo(email.trim());
  });

  return (
    <AuthLayout
      title="Reset your password"
      subtitle={sentTo ? undefined : "Enter your email and we will send you a link to choose a new password."}
      footer={<Link to={paths.login}>Back to sign in</Link>}
    >
      {sentTo ? (
        <div className={styles.stack}>
          <span className={styles.badge}>
            <MailCheck size={28} aria-hidden="true" />
          </span>
          <p>
            If an account exists for <strong>{sentTo}</strong>, a reset link is on its way. It works once and expires in
            1 hour.
          </p>
          <p className={styles.muted}>Nothing arrived? Check your spam folder, or try again in a minute.</p>
        </div>
      ) : (
        <form className={styles.form} onSubmit={onSubmit} noValidate>
          {form.formError && <Banner tone="error">{form.formError}</Banner>}
          <Field label="Email" type="email" autoComplete="email" inputMode="email" {...form.field("email")} />
          <Button type="submit" size="lg" fullWidth loading={form.submitting}>
            {form.submitting ? "Sending" : "Send reset link"}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
