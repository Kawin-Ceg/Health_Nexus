import { Link } from "react-router-dom";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Banner } from "../components/auth/Banner";
import { SignupForm } from "../components/auth/SignupForm";
import { paths } from "../lib/routes";

export function PHCSignup() {
  return (
    <AuthLayout
      title="Apply as a PHC worker"
      subtitle="Three short steps. An administrator checks every application before you can see anyone's records."
      footer={
        <>
          Already registered? <Link to={paths.login}>Sign in</Link>
          <br />
          Not a health worker? <Link to={paths.signup}>Create a citizen account</Link>
        </>
      }
    >
      <Banner tone="info">Your access begins once your application is approved.</Banner>
      <SignupForm variant="phc" />
    </AuthLayout>
  );
}
