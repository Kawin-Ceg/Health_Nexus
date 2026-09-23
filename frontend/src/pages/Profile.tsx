import { useEffect, useRef, useState, type FormEvent } from "react";
import { Camera, Mail, UserRound } from "lucide-react";
import { Btn, Card, ErrorNote, Labelled, Loading, PageHeader, inputCls } from "../components/app/ui";
import { useAuth } from "../context/AuthContext";
import { fmtDate } from "../lib/format";
import { useResource } from "../lib/useResource";
import { errorMessage } from "../services/api";
import * as account from "../services/account";
import type { Profile as ProfileData } from "../services/account";

const ACCEPT = "image/png,image/jpeg,image/webp";

function ImagePicker({ kind, onDone, label }: { kind: "avatar" | "cover"; onDone: (p: ProfileData) => void; label: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const limitMb = kind === "avatar" ? 2 : 5;

  const pick = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    if (file.size > limitMb * 1024 * 1024) {
      setError(`Images must be ${limitMb} MB or smaller.`);
      return;
    }
    setBusy(true);
    try {
      onDone(await account.uploadImage(kind, file));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };
  return (
    <span className="inline-flex flex-col gap-1">
      <input ref={input} type="file" accept={ACCEPT} hidden onChange={(e) => void pick(e.target.files?.[0])} />
      <Btn busy={busy} onClick={() => input.current?.click()}>
        <Camera size={16} aria-hidden="true" /> {label}
      </Btn>
      {error && <span className="text-xs text-danger">{error}</span>}
    </span>
  );
}

export function Profile() {
  const { refreshUser } = useAuth();
  const res = useResource(() => account.getProfile(), "profile");
  const [p, setP] = useState<ProfileData | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", bio: "", location: "", department: "", date_of_birth: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [fieldErrs, setFieldErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [emailMsg, setEmailMsg] = useState<string | null>(null);
  const [emailErr, setEmailErr] = useState<string | null>(null);

  useEffect(() => {
    if (!res.data) return;
    setP(res.data);
    setForm({
      name: res.data.name,
      phone: res.data.phone ?? "",
      bio: res.data.bio ?? "",
      location: res.data.location ?? "",
      department: res.data.department ?? "",
      date_of_birth: res.data.date_of_birth ?? "",
    });
  }, [res.data]);

  if (res.error) return <ErrorNote message={res.error} onRetry={res.reload} />;
  if (!p) return <Loading />;
  const worker = p.role === "phc_worker";

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setMsg(null);
    setFieldErrs({});
    try {
      const { department, ...rest } = form;
      const updated = await account.updateProfile({ ...rest, ...(worker ? { department } : {}), date_of_birth: form.date_of_birth || null });
      setP(updated);
      await refreshUser();
      setMsg("Profile saved.");
    } catch (e2) {
      setErr(errorMessage(e2));
      if (e2 && typeof e2 === "object" && "fieldErrors" in e2) setFieldErrs((e2 as { fieldErrors: Record<string, string> }).fieldErrors);
    } finally {
      setBusy(false);
    }
  };

  const requestEmail = async (e: FormEvent) => {
    e.preventDefault();
    setEmailErr(null);
    setEmailMsg(null);
    try {
      setEmailMsg((await account.requestEmailChange(newEmail, emailPassword)).detail);
      setEmailPassword("");
      res.reload();
    } catch (e2) {
      setEmailErr(errorMessage(e2));
    }
  };

  const field = (key: keyof typeof form, label: string, props: Record<string, unknown> = {}) => (
    <Labelled label={label} hint={fieldErrs[key] && <span className="text-danger">{fieldErrs[key]}</span>}>
      <input value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} className={inputCls} {...props} />
    </Labelled>
  );

  return (
    <>
      <PageHeader title="Profile" />
      <Card className="mb-6 overflow-hidden p-0">
        <div className="relative h-36 bg-brand-soft" style={p.cover_url ? { backgroundImage: `url(${p.cover_url})`, backgroundSize: "cover", backgroundPosition: "center" } : undefined}>
          <div className="absolute right-3 top-3 flex gap-2">
            <ImagePicker kind="cover" label="Cover" onDone={setP} />
            {p.cover_url && <Btn tone="ghost" className="bg-surface/80" onClick={async () => setP(await account.removeImage("cover"))}>Remove</Btn>}
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-4 px-5 pb-5">
          <div className="-mt-10 flex size-20 items-center justify-center overflow-hidden rounded-full border-4 border-surface bg-paper-raised">
            {p.avatar_url ? <img src={p.avatar_url} alt="" className="size-full object-cover" /> : <UserRound size={36} className="text-ink-soft" aria-hidden="true" />}
          </div>
          <div className="flex-1">
            <p className="text-lg font-semibold text-ink">{p.name}</p>
            <p className="text-sm text-ink-soft">{[worker && p.designation?.replace(/_/g, " "), p.facility, `joined ${fmtDate(p.created_at)}`].filter(Boolean).join(" · ")}</p>
          </div>
          <div className="flex gap-2">
            <ImagePicker kind="avatar" label="Photo" onDone={setP} />
            {p.avatar_url && <Btn tone="ghost" onClick={async () => setP(await account.removeImage("avatar"))}>Remove</Btn>}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Details">
          <form onSubmit={save} className="flex flex-col gap-3">
            {field("name", "Name", { required: true, maxLength: 100 })}
            {field("phone", "Phone", { inputMode: "tel", maxLength: 25 })}
            {field("location", "Location", { maxLength: 120 })}
            {worker && field("department", "Department", { maxLength: 120 })}
            {field("date_of_birth", "Date of birth", { type: "date" })}
            <Labelled label="About you" hint={`${form.bio.length}/280`}>
              <textarea value={form.bio} maxLength={280} rows={3} onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))} className={`${inputCls} py-2`} />
            </Labelled>
            {err && <p className="text-sm text-danger">{err}</p>}
            {msg && <p role="status" className="text-sm text-success">{msg}</p>}
            <div><Btn tone="primary" type="submit" busy={busy}>Save</Btn></div>
          </form>
        </Card>
        <Card title="Email address">
          <p className="flex items-center gap-2 text-sm text-ink"><Mail size={16} aria-hidden="true" /> {p.email}</p>
          {p.pending_email && <p className="mt-2 text-sm text-warn">Waiting for you to confirm {p.pending_email}. Check that inbox.</p>}
          <form onSubmit={requestEmail} className="mt-4 flex flex-col gap-3">
            <Labelled label="New email"><input type="email" required value={newEmail} onChange={(e) => setNewEmail(e.target.value)} className={inputCls} /></Labelled>
            <Labelled label="Your password"><input type="password" required value={emailPassword} onChange={(e) => setEmailPassword(e.target.value)} className={inputCls} /></Labelled>
            {emailErr && <p className="text-sm text-danger">{emailErr}</p>}
            {emailMsg && <p role="status" className="text-sm text-success">{emailMsg}</p>}
            <div><Btn type="submit">Send confirmation link</Btn></div>
          </form>
        </Card>
      </div>
    </>
  );
}
