import { Link } from "react-router-dom";
import { AuthLayout } from "../components/auth/AuthLayout";
import { SignupForm } from "../components/auth/SignupForm";
import { paths } from "../lib/routes";

export function PHCSignup() {
  return (
    <AuthLayout
      title="Apply as a PHC worker"
      subtitle="Three short steps, then an administrator reviews it."
      footer={
        <>
          <span>
            Have an account? <Link to={paths.login}>Sign in</Link>
          </span>
          <Link to={paths.signup}>Create a citizen account</Link>
        </>
      }
    >
      <SignupForm variant="phc" />
    </AuthLayout>
  );
}
