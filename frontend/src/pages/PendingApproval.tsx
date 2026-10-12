import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Check, X } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { Doodle } from "../components/landing/Doodle/Doodle";
import { Button } from "../components/ui/Button/Button";
import { useAuth } from "../context/AuthContext";
import { fmtDate } from "../lib/format";
import { destinationFor, paths } from "../lib/routes";
import { DESIGNATIONS } from "../services/auth";
import styles from "./PendingApproval.module.css";

type StepState = "done" | "current" | "failed" | "todo";

export function PendingApproval() {
  const { user, refreshUser } = useAuth();
  const [checking, setChecking] = useState(false);
  const [stillPending, setStillPending] = useState(false);

  if (!user) return <Navigate to={paths.login} replace />;
  // Approved since the page loaded: this screen no longer applies.
  if (user.role !== "pending_phc") return <Navigate to={destinationFor(user)} replace />;

  const application = user.application;
  const designation = DESIGNATIONS.find((d) => d.value === application?.designation)?.label;
  const rejected = application?.status === "rejected";

  const check = async () => {
    setChecking(true);
    setStillPending(false);
    const fresh = await refreshUser();
    setChecking(false);
    setStillPending(fresh?.role === "pending_phc");
  };

  const steps: { title: string; detail: string; state: StepState }[] = [
    { title: "Application sent", detail: application ? fmtDate(application.created_at) : "Received", state: "done" },
    { title: "Email confirmed", detail: user.email, state: "done" },
    {
      title: "Administrator review",
      detail: rejected
        ? (application?.rejection_reason ?? "Not approved")
        : "An administrator checks your details against the health-centre registry.",
      state: rejected ? "failed" : "current",
    },
    { title: "Worker tools unlocked", detail: "You see the citizens registered at your health centre.", state: "todo" },
  ];

  return (
    <>
      <AppHeader />
      <main className={styles.main}>
        <Doodle piece="ecg" className={styles.ecg} />
        <Doodle piece="tree" className={styles.tree} delay={1} />
        <Doodle piece="capsules" className={styles.capsules} delay={2} />

        <p className={styles.eyebrow}>PHC worker application</p>
        <h1 className={styles.title}>
          {rejected ? "Your application was not approved" : "Your application is with an administrator"}
        </h1>
        <p className={styles.lead}>
          {rejected
            ? "An administrator reviewed your application and did not approve it. If you think this is a mistake, contact your block health office."
            : "Until it is approved your account has no access to anyone's health information. We will not send anything until an administrator decides."}
        </p>

        <div className={styles.layout}>
          <ol className={styles.timeline} aria-label="Application progress">
            {steps.map((s) => (
              <li key={s.title} className={styles[s.state]} aria-current={s.state === "current" ? "step" : undefined}>
                <span className={styles.dot} aria-hidden="true">
                  {s.state === "done" ? <Check size={14} /> : s.state === "failed" ? <X size={14} /> : null}
                </span>
                <span>
                  <span className={styles.stepTitle}>{s.title}</span>
                  <span className={styles.stepDetail}>{s.detail}</span>
                  <span className="visually-hidden">
                    {s.state === "done" ? " (done)" : s.state === "current" ? " (in progress)" : s.state === "failed" ? " (not approved)" : " (next)"}
                  </span>
                </span>
              </li>
            ))}
          </ol>

          {application && (
            <dl className={styles.details}>
              <div>
                <dt>Employee ID</dt>
                <dd>{application.employee_id}</dd>
              </div>
              <div>
                <dt>Designation</dt>
                <dd>{designation ?? application.designation}</dd>
              </div>
              <div>
                <dt>Health centre</dt>
                <dd>{application.phc_name}</dd>
              </div>
              <div>
                <dt>District, state</dt>
                <dd>
                  {application.district}, {application.state}
                </dd>
              </div>
              <div>
                <dt>Years of service</dt>
                <dd>{application.years_of_service}</dd>
              </div>
            </dl>
          )}
        </div>

        {!rejected && (
          <div className={styles.actions}>
            <Button size="lg" onClick={check} loading={checking}>
              Check status
            </Button>
          </div>
        )}
        {stillPending && (
          <p role="status" className={styles.note}>
            Still waiting for a decision. You can close this page; your status updates when you sign in.
          </p>
        )}
      </main>
    </>
  );
}
