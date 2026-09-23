import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { destinationFor, paths } from "../../lib/routes";
import { useForm } from "../../lib/useForm";
import { emailError, required } from "../../lib/validation";
import { Banner } from "./Banner";
import { Button } from "../ui/Button/Button";
import { Field } from "../ui/Field/Field";
import styles from "./Auth.module.css";

export function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const form = useForm({ email: "", password: "" }, (v) => ({
    email: emailError(v.email),
    password: required("Password", v.password),
  }));

  const onSubmit = form.handleSubmit(async ({ email, password }) => {
    const user = await login(email.trim(), password);
    navigate(destinationFor(user), { replace: true });
  });

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {form.formError && <Banner tone="error">{form.formError}</Banner>}
      <Field label="Email" type="email" autoComplete="email" inputMode="email" {...form.field("email")} />
      <Field
        label="Password"
        type="password"
        revealable
        autoComplete="current-password"
        labelAside={
          <Link to={paths.forgotPassword} className={styles.link}>
            Forgot password?
          </Link>
        }
        {...form.field("password")}
      />
      <Button type="submit" size="lg" fullWidth loading={form.submitting}>
        {form.submitting ? "Signing in" : "Sign in"}
      </Button>
    </form>
  );
}
