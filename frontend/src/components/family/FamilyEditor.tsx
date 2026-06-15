import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, Loader2, Pencil, Plus, Trash2, Users, X } from "lucide-react";

import { extractErrorMessage } from "../../lib/api";
import {
  useCreatePerson, useCreateRelationship, useDeletePerson,
  useDeleteRelationship, useFamilyTree, useUpdatePerson,
} from "../../lib/hooks";
import type { Person } from "../../lib/types";

const KINDS = ["pai", "mãe", "cônjuge"] as const;

// ── Person create/edit form ──────────────────────────────────────────────────

function PersonForm({
  initial, familyLabel, onClose,
}: {
  initial: Person | null;          // null = create new
  familyLabel?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const create = useCreatePerson();
  const update = useUpdatePerson();

  const [name,  setName]  = useState(initial?.name ?? "");
  const [sex,   setSex]   = useState(initial?.sex ?? "");
  const [birth, setBirth] = useState(initial?.birth_date?.slice(0, 10) ?? "");
  const [death, setDeath] = useState(initial?.death_date?.slice(0, 10) ?? "");
  const [place, setPlace] = useState(initial?.birth_place ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");

  const saving = create.isPending || update.isPending;

  const submit = async () => {
    if (name.trim().length < 1) return;
    const body = {
      name: name.trim(),
      sex: sex || null,
      birth_date: birth || null,
      death_date: death || null,
      birth_place: place || null,
      notes: notes || null,
    };
    try {
      if (initial?.id) {
        await update.mutateAsync({ id: initial.id, ...body });
      } else {
        await create.mutateAsync({ ...body, family_label: familyLabel ?? null });
      }
      toast.success(t("common.success"));
      onClose();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-lift dark:border-stone-800 dark:bg-stone-900">
        <div className="flex items-start justify-between">
          <h3 className="font-serif text-xl font-semibold tracking-tight">
            {initial ? t("family.editor.editPerson") : t("family.editor.addPerson")}
          </h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div>
            <label className="label">{t("family.editor.fName")}</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">{t("family.editor.fSex")}</label>
              <select className="input" value={sex ?? ""} onChange={(e) => setSex(e.target.value)}>
                <option value="">—</option>
                <option value="M">{t("family.editor.sexM")}</option>
                <option value="F">{t("family.editor.sexF")}</option>
              </select>
            </div>
            <div>
              <label className="label">{t("family.editor.fBirth")}</label>
              <input type="date" className="input [color-scheme:light] dark:[color-scheme:dark]" value={birth} onChange={(e) => setBirth(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">{t("family.editor.fDeath")}</label>
              <input type="date" className="input [color-scheme:light] dark:[color-scheme:dark]" value={death} onChange={(e) => setDeath(e.target.value)} />
            </div>
            <div>
              <label className="label">{t("family.editor.fPlace")}</label>
              <input className="input" value={place} onChange={(e) => setPlace(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">{t("family.editor.fNotes")}</label>
            <textarea className="input min-h-[70px] resize-y" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="btn btn-ghost">{t("common.cancel")}</button>
          <button onClick={submit} disabled={saving || !name.trim()} className="btn btn-primary">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            <span>{t("common.save")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Quick pedigree wizard (fixed template) ─────────────────────────────────────

const PEDIGREE_FIELDS: { key: string; label: string; sex: string | null }[] = [
  { key: "eu",         label: "Eu",            sex: null },
  { key: "pai",        label: "Pai",           sex: "M" },
  { key: "mae",        label: "Mãe",           sex: "F" },
  { key: "avoPaterno", label: "Avô paterno",   sex: "M" },
  { key: "avoPaterna", label: "Avó paterna",   sex: "F" },
  { key: "avoMaterno", label: "Avô materno",   sex: "M" },
  { key: "avoMaterna", label: "Avó materna",   sex: "F" },
];

function PedigreeWizard({
  familyLabel, onClose,
}: {
  familyLabel?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const create = useCreatePerson();
  const createRel = useCreateRelationship();
  const [vals, setVals] = useState<Record<string, string>>({});
  const [siblings, setSiblings] = useState("");
  const [busy, setBusy] = useState(false);

  const dirty = Object.values(vals).some((x) => x?.trim()) || siblings.trim().length > 0;

  const close = () => {
    if (dirty && !window.confirm(t("family.editor.confirmLeave"))) return;
    onClose();
  };

  const build = async () => {
    setBusy(true);
    try {
      const mk = async (name: string, sex: string | null): Promise<number | null> => {
        if (!name?.trim()) return null;
        const p = await create.mutateAsync({ name: name.trim(), sex, family_label: familyLabel ?? null });
        return p.id;
      };
      const rel = async (from: number | null, to: number | null, kind: string) => {
        if (from && to) await createRel.mutateAsync({ from_person_id: from, to_person_id: to, kind });
      };

      const id: Record<string, number | null> = {};
      for (const f of PEDIGREE_FIELDS) id[f.key] = await mk(vals[f.key] ?? "", f.sex);

      await rel(id.pai, id.eu, "pai");
      await rel(id.mae, id.eu, "mãe");
      await rel(id.avoPaterno, id.pai, "pai");
      await rel(id.avoPaterna, id.pai, "mãe");
      await rel(id.avoMaterno, id.mae, "pai");
      await rel(id.avoMaterna, id.mae, "mãe");
      await rel(id.pai, id.mae, "cônjuge");
      await rel(id.avoPaterno, id.avoPaterna, "cônjuge");
      await rel(id.avoMaterno, id.avoMaterna, "cônjuge");

      for (const nm of siblings.split(",").map((s) => s.trim()).filter(Boolean)) {
        const sib = await mk(nm, null);
        await rel(id.pai, sib, "pai");
        await rel(id.mae, sib, "mãe");
      }

      toast.success(t("common.success"));
      onClose();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-stone-200 bg-white p-6 shadow-lift dark:border-stone-800 dark:bg-stone-900">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-serif text-xl font-semibold tracking-tight">{t("family.editor.pedigree")}</h3>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t("family.editor.pedigreeLead")}</p>
          </div>
          <button onClick={close} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PEDIGREE_FIELDS.map((f) => (
            <div key={f.key}>
              <label className="label">{f.label}</label>
              <input
                className="input"
                value={vals[f.key] ?? ""}
                onChange={(e) => setVals((v) => ({ ...v, [f.key]: e.target.value }))}
                placeholder={t("family.editor.namePlaceholder")}
              />
            </div>
          ))}
        </div>

        <div className="mt-3">
          <label className="label">{t("family.editor.siblings")}</label>
          <input className="input" value={siblings} onChange={(e) => setSiblings(e.target.value)} placeholder="ex.: Ana, João" />
          <p className="mt-1 text-xs text-stone-500 dark:text-stone-500">{t("family.editor.siblingsHint")}</p>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={close} className="btn btn-ghost">{t("common.cancel")}</button>
          <button onClick={build} disabled={busy || !dirty} className="btn btn-primary">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            <span>{t("family.editor.createPedigree")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main editor overlay ────────────────────────────────────────────────────────

export default function FamilyEditor({
  familyLabel, onClose,
}: {
  familyLabel?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { data } = useFamilyTree(familyLabel ?? undefined);
  const persons = data?.persons ?? [];
  const rels    = data?.relationships ?? [];

  const delPerson = useDeletePerson();
  const delRel    = useDeleteRelationship();
  const createRel = useCreateRelationship();

  const [editing,  setEditing]  = useState<Person | null | undefined>(undefined); // undefined = closed
  const [pedigree, setPedigree] = useState(false);
  const [fromId, setFromId] = useState<string>("");
  const [toId,   setToId]   = useState<string>("");
  const [kind,   setKind]   = useState<string>("pai");

  // Warn before the tab/window is closed mid-edit.
  useEffect(() => {
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, []);

  const nameOf = (id: number) => persons.find((p) => p.id === id)?.name ?? `#${id}`;

  const addRelation = async () => {
    if (!fromId || !toId || fromId === toId) return;
    try {
      await createRel.mutateAsync({ from_person_id: Number(fromId), to_person_id: Number(toId), kind });
      toast.success(t("common.success"));
      setFromId(""); setToId("");
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  const removePerson = async (p: Person) => {
    if (!window.confirm(t("family.editor.confirmDeletePerson"))) return;
    try { await delPerson.mutateAsync(p.id); } catch (err) { toast.error(extractErrorMessage(err)); }
  };

  const relVerb = (k: string) => k === "cônjuge" ? t("family.editor.spouseOf") : `${k} ${t("family.editor.of")}`;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-stone-50 dark:bg-stone-950">
      {/* Header — the only way out is "Concluir". */}
      <div className="flex items-center justify-between border-b border-stone-200 px-5 py-4 dark:border-stone-800">
        <h2 className="font-serif text-xl font-semibold tracking-tight">{t("family.editor.title")}</h2>
        <button onClick={onClose} className="btn btn-primary">
          <Check className="h-4 w-4" />
          <span>{t("family.editor.finish")}</span>
        </button>
      </div>

      <div className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto p-5">
        <div className="mb-5 flex flex-wrap gap-2">
          <button onClick={() => setEditing(null)} className="btn btn-primary">
            <Plus className="h-4 w-4" /><span>{t("family.editor.addPerson")}</span>
          </button>
          <button onClick={() => setPedigree(true)} className="btn btn-ghost">
            <Users className="h-4 w-4" /><span>{t("family.editor.pedigree")}</span>
          </button>
        </div>

        {/* People */}
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-stone-500">{t("family.editor.people")} ({persons.length})</h3>
        <div className="mb-8 grid gap-2 sm:grid-cols-2">
          {persons.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-2 rounded-xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-stone-900">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{p.name}</p>
                <p className="text-xs text-stone-500">
                  {[p.sex === "M" ? "♂" : p.sex === "F" ? "♀" : null, p.birth_date?.slice(0, 4)].filter(Boolean).join(" · ")}
                </p>
              </div>
              <div className="flex shrink-0 gap-1">
                <button onClick={() => setEditing(p)} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={() => removePerson(p)} className="rounded-lg p-1.5 text-stone-500 hover:bg-rose-100 hover:text-rose-700 dark:hover:bg-rose-950/40"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            </div>
          ))}
          {persons.length === 0 && <p className="text-sm text-stone-500">{t("family.noTree")}</p>}
        </div>

        {/* Relationships */}
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-stone-500">{t("family.editor.relations")}</h3>
        <div className="mb-4 flex flex-wrap items-end gap-2 rounded-xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-stone-900">
          <select className="input max-w-[40%]" value={fromId} onChange={(e) => setFromId(e.target.value)}>
            <option value="">{t("family.editor.person")}…</option>
            {persons.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className="input w-auto" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => <option key={k} value={k}>{relVerb(k)}</option>)}
          </select>
          <select className="input max-w-[40%]" value={toId} onChange={(e) => setToId(e.target.value)}>
            <option value="">{t("family.editor.person")}…</option>
            {persons.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={addRelation} disabled={!fromId || !toId || fromId === toId || createRel.isPending} className="btn btn-primary">
            <Plus className="h-4 w-4" /><span>{t("family.editor.addRelation")}</span>
          </button>
        </div>
        <div className="space-y-1.5">
          {rels.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm dark:border-stone-800 dark:bg-stone-900">
              <span><strong>{nameOf(r.from)}</strong> — {relVerb(r.kind)} — <strong>{nameOf(r.to)}</strong></span>
              <button onClick={() => delRel.mutate(r.id)} className="rounded-lg p-1.5 text-stone-500 hover:bg-rose-100 hover:text-rose-700 dark:hover:bg-rose-950/40"><Trash2 className="h-3.5 w-3.5" /></button>
            </div>
          ))}
          {rels.length === 0 && <p className="text-sm text-stone-500">{t("family.editor.noRelations")}</p>}
        </div>
      </div>

      {editing !== undefined && (
        <PersonForm initial={editing} familyLabel={familyLabel} onClose={() => setEditing(undefined)} />
      )}
      {pedigree && (
        <PedigreeWizard familyLabel={familyLabel} onClose={() => setPedigree(false)} />
      )}
    </div>
  );
}
