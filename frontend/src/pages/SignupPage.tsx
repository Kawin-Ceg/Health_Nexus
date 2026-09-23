import { Link } from "react-router-dom";
import { AuthLayout } from "../components/auth/AuthLayout";
import { SignupForm } from "../components/auth/SignupForm";
import { paths } from "../lib/routes";

export function SignupPage() {
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Track your health and stay connected to your health centre."
      footer={
        <>
          Already registered? <Link to={paths.login}>Sign in</Link>
          <br />
          Health worker? <Link to={paths.phcSignup}>Apply as a PHC worker</Link>
        </>
      }
    >
      <SignupForm variant="citizen" />
    </AuthLayout>
  );
}
