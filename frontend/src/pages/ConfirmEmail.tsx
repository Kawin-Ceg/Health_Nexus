import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { paths } from "../lib/routes";
import { errorMessage } from "../services/api";
import { confirmEmailChange } from "../services/account";

/** Opened from the email-change link, often on a device with no session. */
export function ConfirmEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<{ ok: boolean; message: string } | null>(null);
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    if (token.length < 10 || token.length > 256) {
      setState({ ok: false, message: "This confirmation link is invalid or has expired." });
      return;
    }
    confirmEmailChange(token)
      .then((r) => setState({ ok: true, message: r.detail }))
      .catch((e) => setState({ ok: false, message: errorMessage(e) }));
  }, [token]);

  return (
    <main className="mx-auto mt-20 max-w-md px-4 text-center">
      <h1 className="text-2xl font-semibold text-ink">Confirm your email</h1>
      <p role="status" className={`mt-4 text-sm ${state && !state.ok ? "text-danger" : "text-ink"}`}>
        {state ? state.message : "Confirming…"}
      </p>
      <Link to={paths.login} className="mt-6 inline-block text-sm font-semibold text-brand underline">
        Go to sign in
      </Link>
    </main>
  );
}
