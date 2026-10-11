import { LegalLayout, type LegalSection } from "./LegalLayout";

const sections: LegalSection[] = [
  {
    id: "what-we-collect",
    title: "What we collect",
    body: (
      <>
        <p>We only collect what you give us while using Health Nexus:</p>
        <ul>
          <li>
            <strong>Account details:</strong> your name, email address and password. The password is stored only as a
            one-way hash; nobody, including us, can read it.
          </li>
          <li>
            <strong>Health profile:</strong> age, gender, height, weight, blood group, existing conditions, current
            medications and an emergency contact, if you choose to add them.
          </li>
          <li>
            <strong>Location:</strong> your state, district, pincode, locality and the health centre you choose.
          </li>
          <li>
            <strong>Readings:</strong> the vitals and symptoms you log, when you measured them, and, if your device
            shares it, the place a reading was taken.
          </li>
          <li>
            <strong>Health worker applications:</strong> for PHC workers, your employee ID, designation, health centre
            and years of service.
          </li>
          <li>
            <strong>Assistant conversations:</strong> the questions you ask the assistant and its answers, including
            the records each answer was based on.
          </li>
          <li>
            <strong>Security records:</strong> the devices you are signed in on, IP addresses for sign-ins and for
            sensitive actions (such as deleting a reading or a health worker opening your record), and your consent
            history.
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "how-we-use-it",
    title: "How we use it",
    body: (
      <ul>
        <li>To compare each reading with your own usual values and flag readings that look unusual for you.</li>
        <li>To let the health workers at your chosen health centre review flagged readings and book visits with you.</li>
        <li>To show health workers grouped, locality-level counts so they can notice unusual local patterns.</li>
        <li>To answer your questions in the assistant, using only your own records.</li>
        <li>To send account emails: confirming your address, resetting your password, and confirming an email change.</li>
        <li>To keep the service secure and to investigate concerns you raise.</li>
      </ul>
    ),
  },
  {
    id: "who-can-see-it",
    title: "Who can see your information",
    body: (
      <ul>
        <li>
          <strong>You</strong> can see everything you have logged.
        </li>
        <li>
          <strong>Health workers</strong> can see your details, readings and flags only if you are registered at their
          health centre and they have been approved by an administrator. Each time a health worker opens your record,
          it is logged.
        </li>
        <li>
          <strong>Administrators</strong> manage accounts, worker approvals and support concerns. The admin console
          shows account details and totals, not your readings.
        </li>
        <li>
          <strong>Community views</strong> show counts per locality. Localities with fewer than three people are
          merged into a larger group so nobody can be picked out.
        </li>
        <li>
          <strong>The AI assistant</strong> may use Google's Gemini service, if it is enabled. When it is, your question
          and the records retrieved to answer it are sent to Gemini to word the answer. When it is not, answers are
          written by Health Nexus itself and nothing is sent outside.
        </li>
      </ul>
    ),
  },
  {
    id: "your-choices",
    title: "Your choices and controls",
    body: (
      <ul>
        <li>
          <strong>Consent:</strong> turn health tracking, health worker access, community surveillance, research and
          marketing updates on or off in Settings, under Privacy. Every change is kept in a history you can view.
          With health tracking off, no new readings are accepted.
        </li>
        <li>
          <strong>Download your data:</strong> Settings, under Privacy, gives you all your data as one file.
          Passwords and sign-in tokens are never included.
        </li>
        <li>
          <strong>Delete a reading:</strong> remove any reading from your History.
        </li>
        <li>
          <strong>Change your health centre</strong> in Settings. Health workers at your old centre can no longer see you.
        </li>
        <li>
          <strong>Delete your assistant conversations</strong> from the assistant page.
        </li>
        <li>
          <strong>Deactivate your account</strong> in Settings. You are signed out everywhere and any booked visits are
          cancelled. Deactivation does not erase your records; an administrator can reactivate the account. To ask for
          your records to be erased, raise a concern under Support.
        </li>
      </ul>
    ),
  },
  {
    id: "cookies",
    title: "Cookies and storage",
    body: (
      <>
        <p>
          We use one cookie: a secure, http-only sign-in cookie that keeps you logged in. It cannot be read by page
          scripts. Your onboarding answers are kept in your browser tab until you finish, then removed.
        </p>
        <p>We do not use advertising or analytics cookies, and we do not sell your data.</p>
        <p>
          The health worker risk map loads map tiles from OpenStreetMap, which receives the usual request details,
          such as your IP address, when those tiles load.
        </p>
      </>
    ),
  },
  {
    id: "security",
    title: "Security",
    body: (
      <ul>
        <li>Passwords and sign-in tokens are stored only as one-way hashes.</li>
        <li>Sign-in sessions expire after a period of inactivity, and you can sign out other devices from your account.</li>
        <li>Every health worker request is checked on the server against their health centre, not only in the app.</li>
        <li>No system is perfectly secure. If you notice something wrong, raise a concern straight away.</li>
      </ul>
    ),
  },
  {
    id: "not-medical-advice",
    title: "Health information, not medical advice",
    body: (
      <p>
        Health Nexus explains readings; it does not diagnose. A flag means a reading looks unusual for you, not that
        something is wrong. In an emergency, call 108.
      </p>
    ),
  },
  {
    id: "changes",
    title: "Changes to this policy",
    body: <p>If we change how we handle your data, we will update this page and the date at the top.</p>,
  },
];

export function PrivacyPolicy() {
  return (
    <LegalLayout
      title="Privacy policy"
      updated="11 October 2026"
      intro={<p>What Health Nexus collects, who can see it, and how you stay in control. Written in plain words.</p>}
      sections={sections}
    />
  );
}
