import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Hourglass } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { Button } from "../components/ui/Button/Button";
import { useAuth } from "../context/AuthContext";
import { destinationFor, paths } from "../lib/routes";
import { DESIGNATIONS } from "../services/auth";
import styles from "./PendingApproval.module.css";

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

  return (
    <>
      <AppHeader />
      <main className={styles.main}>
        <span className={styles.icon}>
          <Hourglass size={28} aria-hidden="true" />
        </span>
        <h1>{rejected ? "Your application was not approved" : "Your application is awaiting approval"}</h1>
        <p className={styles.lead}>
          {rejected
            ? "An administrator reviewed your PHC worker application and did not approve it. If you think this is a mistake, contact your block health office."
            : "An administrator has to approve your PHC worker application before you can use the worker tools. Until then your account has no access to patient information."}
        </p>

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
            <div>
              <dt>Status</dt>
              <dd>{rejected ? "Not approved" : "Pending review"}</dd>
            </div>
            {rejected && application.rejection_reason && (
              <div>
                <dt>Reason</dt>
                <dd>{application.rejection_reason}</dd>
              </div>
            )}
          </dl>
        )}

        <div className={styles.actions}>
          <Button variant="secondary" onClick={check} loading={checking}>
            Check status
          </Button>
        </div>
        {stillPending && (
          <p role="status" className={styles.note}>
            Still pending. We will not send anything until an administrator decides.
          </p>
        )}
      </main>
    </>
  );
}
