import { useState } from "react";
import { Btn, Card, Empty, ErrorNote, Loading, PageHeader, cx, inputCls } from "../../components/app/ui";
import { fmtAgo } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import type { Role } from "../../services/auth";
import { deactivateAccount, getAccounts, reactivateAccount, type Account, type AccountStatus } from "../../services/admin";
import { useToast } from "../../components/app/Toaster";

const PAGE = 50;
const ROLE_LABEL: Record<Role, string> = { user: "Citizen", pending_phc: "Awaiting approval", phc_worker: "PHC worker", admin: "Admin" };

export function Accounts() {
  const [role, setRole] = useState<Role | "">("");
  const [status, setStatus] = useState<AccountStatus | "">("");
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const [offset, setOffset] = useState(0);

  const query = { role, status, q, limit: PAGE, offset };
  const res = useResource((s) => getAccounts(query, s), JSON.stringify(query));
  const d = res.data;

  return (
    <>
      <PageHeader title="Accounts" lead="Every account. Deactivating one signs it out everywhere at once; administrators cannot be changed here." />
      <div className="mb-4 flex flex-wrap gap-3">
        <input type="search" value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0); }} placeholder="Search name or email" aria-label="Search" className={cx(inputCls, "max-w-xs")} />
        <select aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value as Role | ""); setOffset(0); }} className={cx(inputCls, "w-auto")}>
          <option value="">All roles</option>
          {(Object.keys(ROLE_LABEL) as Role[]).map((r) => (
            <option key={r} value={r}>{ROLE_LABEL[r]}</option>
          ))}
        </select>
        <select aria-label="Status" value={status} onChange={(e) => { setStatus(e.target.value as AccountStatus | ""); setOffset(0); }} className={cx(inputCls, "w-auto")}>
          <option value="">Any status</option>
          <option value="active">Active</option>
          <option value="inactive">Deactivated</option>
          <option value="unverified">Email not confirmed</option>
        </select>
      </div>
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No accounts match" />
      ) : (
        <Card className={cx("overflow-x-auto p-0", res.loading && "opacity-60")}>
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Health centre</th>
                <th className="px-4 py-3 font-medium">Joined</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium"><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.items.map((a) => (
                <AccountRow key={a.id} account={a} onChanged={res.reload} />
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {d && d.total > PAGE && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between text-sm text-ink-soft">
          <span>{offset + 1}–{Math.min(offset + PAGE, d.total)} of {d.total}</span>
          <div className="flex gap-2">
            <Btn disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</Btn>
            <Btn disabled={offset + PAGE >= d.total} onClick={() => setOffset(offset + PAGE)}>Next</Btn>
          </div>
        </nav>
      )}
    </>
  );
}

function AccountRow({ account: a, onChanged }: { account: Account; onChanged: () => void }) {
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();

  const run = async (fn: () => Promise<Account>) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await fn();
      notify({ tone: "success", title: updated.is_active ? "Account reactivated" : "Account deactivated", body: updated.name });
      setAsking(false);
      setReason("");
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <tr className="align-top">
      <td className="px-4 py-3">
        <span className="block font-medium text-ink">{a.name}</span>
        <span className="block text-xs text-ink-soft">{a.email}</span>
      </td>
      <td className="px-4 py-3 text-ink">{ROLE_LABEL[a.role]}</td>
      <td className="px-4 py-3 text-ink-soft">{a.facility ?? (a.role === "phc_worker" ? <span className="text-danger">Not linked</span> : "—")}</td>
      <td className="px-4 py-3 text-ink-soft">{fmtAgo(a.created_at)}</td>
      <td className="px-4 py-3">
        {a.is_active ? <span className="text-success">Active</span> : <span className="text-danger">Deactivated</span>}
        {!a.is_verified && <span className="block text-xs text-warn">Email not confirmed</span>}
      </td>
      <td className="px-4 py-3 text-right">
        {a.role === "admin" ? null : a.is_active ? (
          asking ? (
            <div className="flex min-w-56 flex-col gap-2">
              <input className={inputCls} autoFocus placeholder="Reason" value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
              <div className="flex gap-2">
                <Btn tone="danger" busy={busy} disabled={reason.trim().length < 3} onClick={() => run(() => deactivateAccount(a.id, reason))}>Deactivate</Btn>
                <Btn tone="ghost" onClick={() => setAsking(false)}>Cancel</Btn>
              </div>
            </div>
          ) : (
            <Btn tone="ghost" onClick={() => setAsking(true)}>Deactivate</Btn>
          )
        ) : (
          <Btn busy={busy} onClick={() => run(() => reactivateAccount(a.id))}>Reactivate</Btn>
        )}
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
      </td>
    </tr>
  );
}
