import { Link } from "react-router-dom";
import { paths } from "../../lib/routes";
import { LegalLayout, type LegalSection } from "./LegalLayout";

const sections: LegalSection[] = [
  {
    id: "the-service",
    title: "What Health Nexus is",
    body: (
      <p>
        Health Nexus lets citizens log their health readings and see how each one compares with their own usual
        values, and lets approved health workers at primary health centres review unusual readings in their area and
        arrange visits. It is free for citizens.
      </p>
    ),
  },
  {
    id: "not-medical-advice",
    title: "Not a medical service",
    body: (
      <ul>
        <li>Health Nexus explains readings; it does not diagnose, treat or prescribe.</li>
        <li>A flag means a reading is unusual for you. It is not a diagnosis, and no flag does not mean you are well.</li>
        <li>The assistant only answers from your records. It will not advise on medicines or doses.</li>
        <li>Always follow the advice of a qualified health professional. In an emergency, call 108.</li>
      </ul>
    ),
  },
  {
    id: "accounts",
    title: "Your account",
    body: (
      <ul>
        <li>Give accurate details and confirm your email address before using the app.</li>
        <li>Keep your password private. You are responsible for activity on your account.</li>
        <li>Each person should have their own account. Log only your own readings.</li>
      </ul>
    ),
  },
  {
    id: "health-workers",
    title: "Health worker accounts",
    body: (
      <ul>
        <li>
          Signing up as a PHC worker creates an application, not access. An administrator checks it and links your
          account to your health centre before you can see anyone's information.
        </li>
        <li>Apply only with your own, genuine employee details.</li>
        <li>
          You may see citizens only from your own health centre, and only to look after their health. Every record you
          open is logged.
        </li>
        <li>Access can be revoked if your role changes or these rules are broken.</li>
      </ul>
    ),
  },
  {
    id: "rules",
    title: "Rules of use",
    body: (
      <>
        <p>When using Health Nexus, you must not:</p>
        <ul>
          <li>log readings for someone else, or enter readings you know are false;</li>
          <li>try to see, guess or collect other people's information, including by probing addresses or IDs;</li>
          <li>use health information you see as a health worker for anything other than that person's care;</li>
          <li>share, copy or publish any person's details from the app;</li>
          <li>harass, threaten or discriminate against anyone, including when raising a concern;</li>
          <li>try to get around sign-in, permissions or rate limits, or disrupt the service;</li>
          <li>use automated tools to scrape the app or send large numbers of requests.</li>
        </ul>
        <p>Accounts that break these rules may be deactivated by an administrator.</p>
      </>
    ),
  },
  {
    id: "your-data",
    title: "Your data",
    body: (
      <p>
        Your records belong to you. How we collect, use and protect them is explained in our{" "}
        <Link to={paths.privacy} className="text-brand underline underline-offset-4">
          privacy policy
        </Link>
        . You can download your data, delete readings and deactivate your account from Settings.
      </p>
    ),
  },
  {
    id: "availability",
    title: "Availability",
    body: (
      <p>
        We work to keep Health Nexus available and accurate, but it may sometimes be unavailable or contain errors.
        Do not rely on it as your only way of noticing a health problem or contacting a health worker.
      </p>
    ),
  },
  {
    id: "ending",
    title: "Ending your use",
    body: (
      <p>
        You can deactivate your account at any time from Settings. We may deactivate accounts that break these terms.
      </p>
    ),
  },
  {
    id: "changes",
    title: "Changes to these terms",
    body: <p>If these terms change, we will update this page and the date at the top.</p>,
  },
];

export function Terms() {
  return (
    <LegalLayout
      title="Terms of service"
      updated="11 October 2026"
      intro={<p>The rules for using Health Nexus, in plain words. By creating an account you agree to them.</p>}
      sections={sections}
    />
  );
}
