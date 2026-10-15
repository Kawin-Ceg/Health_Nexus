import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { Btn, Card, Empty, ErrorNote, Labelled, Loading, PageHeader, cx, inputCls } from "../../components/app/ui";
import { useToast } from "../../components/app/Toaster";
import { useDebounced } from "../../lib/useDebounced";
import { useResource } from "../../lib/useResource";
import { errorMessage } from "../../services/api";
import {
  createCentre,
  editCentre,
  getCentres,
  setCentreActive,
  type Centre,
  type CentreInput,
} from "../../services/admin";

const PAGE = 50;

type Draft = Record<keyof CentreInput, string>;

const EMPTY: Draft = {
  facility_code: "",
  name: "",
  district: "",
  state: "Tamil Nadu",
  block: "",
  official_email_domain: "",
  latitude: "",
  longitude: "",
};

function toDraft(c: Centre): Draft {
  return {
    facility_code: c.facility_code,
    name: c.name,
    district: c.district,
    state: c.state,
    block: c.block ?? "",
    official_email_domain: c.official_email_domain ?? "",
    latitude: c.latitude?.toString() ?? "",
    longitude: c.longitude?.toString() ?? "",
  };
}

function fromDraft(d: Draft): CentreInput {
  const num = (v: string) => (v.trim() === "" ? null : Number(v));
  const text = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    facility_code: d.facility_code.trim(),
    name: d.name.trim(),
    district: d.district.trim(),
    state: d.state.trim(),
    block: text(d.block),
    official_email_domain: text(d.official_email_domain),
    latitude: num(d.latitude),
    longitude: num(d.longitude),
  };
}

export function Centres() {
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const [district, setDistrict] = useState("");
  const [state, setState] = useState<"all" | "active" | "inactive">("all");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<Centre | "new" | null>(null);

  const query = { q, district, state, limit: PAGE, offset };
  const res = useResource((s) => getCentres(query, s), JSON.stringify(query));
  const d = res.data;

  const reset = (fn: () => void) => {
    fn();
    setOffset(0);
  };

  return (
    <>
      <PageHeader
        title="Health centres"
        lead="The registry citizens choose from and worker applications are matched against. Deactivating a centre hides it from new sign-ups; people already linked stay linked."
        actions={
          <Btn tone="primary" onClick={() => setEditing("new")}>
            <Plus size={16} aria-hidden="true" /> Add a centre
          </Btn>
        }
      />
      {editing && (
        <CentreForm
          centre={editing === "new" ? null : editing}
          onDone={() => {
            setEditing(null);
            res.reload();
          }}
        />
      )}
      <div className="mb-4 flex flex-wrap gap-3">
        <input type="search" value={search} onChange={(e) => reset(() => setSearch(e.target.value))} placeholder="Search name, code or block" aria-label="Search" className={cx(inputCls, "max-w-xs")} />
        <select aria-label="District" value={district} onChange={(e) => reset(() => setDistrict(e.target.value))} className={cx(inputCls, "w-auto")}>
          <option value="">All districts</option>
          {d?.districts.map((x) => (
            <option key={x} value={x}>{x}</option>
          ))}
        </select>
        <select aria-label="Status" value={state} onChange={(e) => reset(() => setState(e.target.value as typeof state))} className={cx(inputCls, "w-auto")}>
          <option value="all">Active and inactive</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>
      {res.error && <ErrorNote message={res.error} onRetry={res.reload} />}
      {!d ? (
        !res.error && <Loading />
      ) : d.items.length === 0 ? (
        <Empty title="No health centres match" />
      ) : (
        <Card className={cx("overflow-x-auto p-0", res.loading && "opacity-60")}>
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">Centre</th>
                <th className="px-4 py-3 font-medium">District</th>
                <th className="px-4 py-3 font-medium">Workers</th>
                <th className="px-4 py-3 font-medium">Citizens</th>
                <th className="px-4 py-3 font-medium">Map</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium"><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.items.map((c) => (
                <CentreRow key={c.id} centre={c} onEdit={() => setEditing(c)} onChanged={res.reload} />
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

function CentreRow({ centre: c, onEdit, onChanged }: { centre: Centre; onEdit: () => void; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();
  const linked = c.workers + c.citizens;

  const toggle = async () => {
    if (c.is_active && linked && !window.confirm(`${linked} people are linked to ${c.name}. They keep their link, but nobody new can choose it. Deactivate?`)) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await setCentreActive(c.id, !c.is_active);
      notify({ tone: "success", title: updated.is_active ? "Centre reactivated" : "Centre deactivated", body: updated.name });
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
        <span className="block font-medium text-ink">{c.name}</span>
        <span className="block text-xs text-ink-soft">
          {c.facility_code}
          {c.block && ` · ${c.block}`}
          {c.is_placeholder && <span className="ml-1 text-warn">· not yet checked</span>}
        </span>
      </td>
      <td className="px-4 py-3 text-ink">{c.district}</td>
      <td className={cx("px-4 py-3 tabular-nums", c.workers === 0 && c.is_active ? "text-warn" : "text-ink")}>{c.workers}</td>
      <td className="px-4 py-3 tabular-nums text-ink">{c.citizens}</td>
      <td className="px-4 py-3 text-ink-soft">{c.latitude != null ? "Located" : <span className="text-warn">No location</span>}</td>
      <td className="px-4 py-3">{c.is_active ? <span className="text-success">Active</span> : <span className="text-danger">Inactive</span>}</td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        <Btn tone="ghost" onClick={onEdit}>Edit</Btn>
        <Btn tone="ghost" busy={busy} onClick={() => void toggle()}>{c.is_active ? "Deactivate" : "Reactivate"}</Btn>
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
      </td>
    </tr>
  );
}

function CentreForm({ centre, onDone }: { centre: Centre | null; onDone: () => void }) {
  const [draft, setDraft] = useState<Draft>(centre ? toDraft(centre) : EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { notify } = useToast();
  const set = (key: keyof Draft) => (e: { target: { value: string } }) => setDraft({ ...draft, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const input = fromDraft(draft);
      const saved = centre
        ? await editCentre(centre.id, { ...input, facility_code: undefined })
        : await createCentre(input);
      notify({ tone: "success", title: centre ? "Centre updated" : "Centre added", body: saved.name });
      onDone();
    } catch (e2) {
      setError(errorMessage(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mb-6" title={centre ? `Edit ${centre.name}` : "Add a health centre"}>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <Labelled label="Facility code" hint={centre ? "Codes cannot change." : "Letters, numbers and dashes, e.g. TN-CHN-PHC-0123."}>
          <input required disabled={!!centre} value={draft.facility_code} onChange={set("facility_code")} className={inputCls} />
        </Labelled>
        <Labelled label="Name">
          <input required minLength={2} value={draft.name} onChange={set("name")} className={inputCls} />
        </Labelled>
        <Labelled label="District">
          <input required minLength={2} value={draft.district} onChange={set("district")} className={inputCls} />
        </Labelled>
        <Labelled label="State">
          <input required minLength={2} value={draft.state} onChange={set("state")} className={inputCls} />
        </Labelled>
        <Labelled label="Block (optional)">
          <input value={draft.block} onChange={set("block")} className={inputCls} />
        </Labelled>
        <Labelled label="Official email domain (optional)" hint="Used when matching worker applications.">
          <input value={draft.official_email_domain} onChange={set("official_email_domain")} placeholder="tn.gov.in" className={inputCls} />
        </Labelled>
        <Labelled label="Latitude (optional)" hint="Both or neither. Puts the centre on the risk map.">
          <input type="number" step="any" min={-90} max={90} value={draft.latitude} onChange={set("latitude")} className={inputCls} />
        </Labelled>
        <Labelled label="Longitude (optional)">
          <input type="number" step="any" min={-180} max={180} value={draft.longitude} onChange={set("longitude")} className={inputCls} />
        </Labelled>
        {error && <p className="text-sm text-danger md:col-span-2">{error}</p>}
        <div className="flex gap-2 md:col-span-2">
          <Btn tone="primary" type="submit" busy={busy}>{centre ? "Save changes" : "Add centre"}</Btn>
          <Btn tone="ghost" onClick={onDone}>Cancel</Btn>
        </div>
      </form>
    </Card>
  );
}
