import { useState } from "react";
import { Card, Empty, ErrorNote, Loading, PageHeader, Tabs, cx } from "../../components/app/ui";
import { fmtDateTime } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { getAudit } from "../../services/admin";

type Source = "" | "account" | "verification";

export function AuditLog() {
  const [source, setSource] = useState<Source>("");
  const res = useResource((s) => getAudit(source, s), source);
  const d = res.data;

  return (
    <>
      <PageHeader title="Audit trail" lead="Read-only. Account changes, record views and every worker-verification decision, newest first." />
      <Tabs
        label="Source"
        value={source || "all"}
        onChange={(v) => setSource(v === "all" ? "" : v)}
        tabs={[
          { id: "all" as const, label: "Everything" },
          { id: "account" as const, label: "Accounts & records" },
          { id: "verification" as const, label: "Worker verification" },
        ]}
      />
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : d.length === 0 ? (
        <Empty title="No entries yet" />
      ) : (
        <Card className={cx("overflow-x-auto p-0", res.loading && "opacity-60")}>
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Who</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Detail</th>
                <th className="px-4 py-3 font-medium">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.map((a, i) => (
                <tr key={i}>
                  <td className="whitespace-nowrap px-4 py-3 text-ink-soft">{fmtDateTime(a.created_at)}</td>
                  <td className="px-4 py-3 text-ink">{a.actor ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink">{a.action}</td>
                  <td className="px-4 py-3 text-ink-soft">{a.detail ?? a.entity}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-soft">{a.ip_address}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
