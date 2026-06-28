import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, Image as ImageIcon, Loader2, Pencil, Plus, Trash2, User as UserIcon, Users, X } from "lucide-react";

import { extractErrorMessage, isLostResponse } from "../../lib/api";
import {
  useBulkTree, useCreatePerson, useCreateRelationship, useDeletePerson,
  useDeleteRelationship, useFamilyTree, useMedia, useUpdatePerson,
  type BulkPersonInput, type BulkRelInput,
} from "../../lib/hooks";
import type { MediaFile, Person } from "../../lib/types";
import Photo from "../media/Photo";

// ── Person avatar (profile photo, or initials fallback) ───────────────────────

function PersonAvatar({ photoId, name, size = 40 }: { photoId?: number | null; name: string; size?: number }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
  return (
    <div
      className="relative shrink-0 overflow-hidden rounded-full bg-stone-200 text-stone-500 dark:bg-stone-800 dark:text-stone-400"
      style={{ width: size, height: size }}
    >
      {photoId ? (
        <Photo mediaId={photoId} alt={name} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-xs font-semibold">
          {initials || <UserIcon className="h-4 w-4" />}
        </div>
      )}
    </div>
  );
}

// ── Photo picker grid (choose a profile photo from the library) ───────────────

function PhotoPicker({ onPick, onClose }: { onPick: (id: number) => void; onClose: () => void }) {
  const { t } = useTranslation();
  const { data: media } = useMedia();
  const photos = useMemo(
    () => (media ?? []).filter((m: MediaFile) => m.media_type === "photo"),
    [media],
  );
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-2xl border border-stone-200 bg-white p-5 shadow-lift dark:border-stone-800 dark:bg-stone-900">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-serif text-lg font-semibold">{t("family.editor.pickPhoto")}</h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"><X className="h-4 w-4" /></button>
        </div>
        {photos.length === 0 ? (
          <p className="py-8 text-center text-sm text-stone-500">{t("family.editor.noPhotos")}</p>
        ) : (
          <div className="grid grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4">
            {photos.map((m) => (
              <button
                key={m.id}
                onClick={() => { onPick(m.id); onClose(); }}
                className="relative aspect-square overflow-hidden rounded-lg border border-stone-200 hover:ring-2 hover:ring-amber-500 dark:border-stone-800"
              >
                <Photo mediaId={m.id} alt={m.ai_description ?? ""} className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

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
  const [photoId, setPhotoId] = useState<number | null>(initial?.photo_media_id ?? null);
  const [picking, setPicking] = useState(false);

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
      photo_media_id: photoId,
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
          <div className="flex items-center gap-3">
            <PersonAvatar photoId={photoId} name={name || "?"} size={56} />
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setPicking(true)} className="btn btn-ghost !py-1.5 !text-xs">
                <ImageIcon className="h-3.5 w-3.5" /> {t("family.editor.choosePhoto")}
              </button>
              {photoId != null && (
                <button type="button" onClick={() => setPhotoId(null)} className="btn btn-ghost !py-1.5 !text-xs">
                  <Trash2 className="h-3.5 w-3.5" /> {t("family.editor.removePhoto")}
                </button>
              )}
            </div>
          </div>
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
      {picking && <PhotoPicker onPick={setPhotoId} onClose={() => setPicking(false)} />}
    </div>
  );
}

// ── Quick pedigree wizard (fixed template) ─────────────────────────────────────

const PEDIGREE_FIELDS: { key: string; labelKey: string; sex: string | null }[] = [
  { key: "eu",         labelKey: "family.editor.roleEu",     sex: null },
  { key: "pai",        labelKey: "family.editor.roleFather", sex: "M" },
  { key: "mae",        labelKey: "family.editor.roleMother", sex: "F" },
  { key: "avoPaterno", labelKey: "family.editor.roleGpP",    sex: "M" },
  { key: "avoPaterna", labelKey: "family.editor.roleGmP",    sex: "F" },
  { key: "avoMaterno", labelKey: "family.editor.roleGpM",    sex: "M" },
  { key: "avoMaterna", labelKey: "family.editor.roleGmM",    sex: "F" },
];
const SEX_OF_ROLE: Record<string, string | null> =
  Object.fromEntries(PEDIGREE_FIELDS.map((f) => [f.key, f.sex]));

// Which pedigree roles are the parents of each role — lets "irmão(ã) de"
// resolve to a sibling (so "irmão do Pai" becomes a tio, etc.).
const PARENT_OF: Record<string, [string, string]> = {
  eu:  ["pai", "mae"],
  pai: ["avoPaterno", "avoPaterna"],
  mae: ["avoMaterno", "avoMaterna"],
};
// The spouse of each pedigree role, so "filho(a) de X" can link the child
// to BOTH parents of the couple (pai e mãe), not just one.
const SPOUSE_OF: Record<string, string> = {
  pai: "mae", mae: "pai",
  avoPaterno: "avoPaterna", avoPaterna: "avoPaterno",
  avoMaterno: "avoMaterna", avoMaterna: "avoMaterno",
};

type Extra = { id: string; name: string; rel: "filho" | "casado" | "irmao"; target: string };

function PedigreeWizard({
  familyLabel, onClose,
}: {
  familyLabel?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const bulk = useBulkTree();
  const [vals, setVals] = useState<Record<string, string>>({});
  const [siblings, setSiblings] = useState("");
  const [extras, setExtras] = useState<Extra[]>([]);
  const [busy, setBusy] = useState(false);

  const dirty =
    Object.values(vals).some((x) => x?.trim()) ||
    siblings.trim().length > 0 ||
    extras.some((e) => e.name.trim());

  // Anyone already named (a pedigree role OR another extra) can be the
  // target an extra person is linked to.
  const targetOptions = (selfId: string) => ([
    ...PEDIGREE_FIELDS.filter((f) => (vals[f.key] ?? "").trim()).map((f) => ({ value: f.key, label: t(f.labelKey) })),
    ...extras.filter((e) => e.name.trim() && e.id !== selfId).map((e) => ({ value: `x_${e.id}`, label: e.name.trim() })),
  ]);
  const defaultTarget = PEDIGREE_FIELDS.find((f) => (vals[f.key] ?? "").trim())?.key ?? "eu";

  const close = () => {
    if (dirty && !window.confirm(t("family.editor.confirmLeave"))) return;
    onClose();
  };

  const buildPayload = (): { persons: BulkPersonInput[]; relationships: BulkRelInput[] } => {
    const persons: BulkPersonInput[] = [];
    const rel: BulkRelInput[] = [];
    const fl = familyLabel ?? null;

    for (const f of PEDIGREE_FIELDS) {
      persons.push({ ref: f.key, name: (vals[f.key] ?? "").trim(), sex: f.sex, family_label: fl });
    }
    // Core pedigree links (backend drops any whose person wasn't created).
    rel.push(
      { from_ref: "pai", to_ref: "eu", kind: "pai" },
      { from_ref: "mae", to_ref: "eu", kind: "mãe" },
      { from_ref: "avoPaterno", to_ref: "pai", kind: "pai" },
      { from_ref: "avoPaterna", to_ref: "pai", kind: "mãe" },
      { from_ref: "avoMaterno", to_ref: "mae", kind: "pai" },
      { from_ref: "avoMaterna", to_ref: "mae", kind: "mãe" },
      { from_ref: "pai", to_ref: "mae", kind: "cônjuge" },
      { from_ref: "avoPaterno", to_ref: "avoPaterna", kind: "cônjuge" },
      { from_ref: "avoMaterno", to_ref: "avoMaterna", kind: "cônjuge" },
    );

    siblings.split(",").map((s) => s.trim()).filter(Boolean).forEach((nm, i) => {
      const ref = `sib${i}`;
      persons.push({ ref, name: nm, sex: null, family_label: fl });
      rel.push({ from_ref: "pai", to_ref: ref, kind: "pai" });
      rel.push({ from_ref: "mae", to_ref: ref, kind: "mãe" });
    });

    extras.forEach((ex) => {
      if (!ex.name.trim() || !ex.target) return;
      const ref = `x_${ex.id}`;
      persons.push({ ref, name: ex.name.trim(), sex: null, family_label: fl });
      if (ex.rel === "casado") {
        rel.push({ from_ref: ref, to_ref: ex.target, kind: "cônjuge" });
      } else if (ex.rel === "filho") {
        // "filho(a) de target": link to target AND target's spouse, so the
        // child has both parents (pai e mãe) — not just the one selected.
        const linkParent = (parentRef: string) => {
          rel.push({ from_ref: parentRef, to_ref: ref, kind: SEX_OF_ROLE[parentRef] === "F" ? "mãe" : "pai" });
        };
        linkParent(ex.target);
        const spouse = SPOUSE_OF[ex.target];
        if (spouse && (vals[spouse] ?? "").trim()) linkParent(spouse);
      } else {
        // "irmão(ã) de target": share the target's parents (tio / sibling).
        const parents = PARENT_OF[ex.target];
        if (parents) for (const pr of parents) {
          rel.push({ from_ref: pr, to_ref: ref, kind: SEX_OF_ROLE[pr] === "F" ? "mãe" : "pai" });
        }
      }
    });

    return { persons, relationships: rel };
  };

  const build = async () => {
    setBusy(true);
    const payload = buildPayload();
    try {
      await bulk.mutateAsync(payload);
      toast.success(t("common.success"));
      onClose();
    } catch (err) {
      // One atomic request: a cold-start drop usually means it never landed,
      // so a single retry after a beat is safe.
      if (isLostResponse(err)) {
        try {
          await new Promise((r) => setTimeout(r, 2500));
          await bulk.mutateAsync(payload);
          toast.success(t("common.success"));
          onClose();
          return;
        } catch (err2) {
          toast.error(extractErrorMessage(err2));
          return;
        } finally {
          setBusy(false);
        }
      }
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
              <label className="label">{t(f.labelKey)}</label>
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
          <input className="input" value={siblings} onChange={(e) => setSiblings(e.target.value)} placeholder={t("family.editor.siblingsPlaceholder")} />
          <p className="mt-1 text-xs text-stone-500 dark:text-stone-500">{t("family.editor.siblingsHint")}</p>
        </div>

        {/* Outros familiares — adicionar mais pessoas ligadas a quem já existe */}
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between">
            <label className="label !mb-0">{t("family.editor.otherRelatives")}</label>
            <button
              type="button"
              onClick={() => setExtras((x) => [...x, { id: crypto.randomUUID(), name: "", rel: "filho", target: defaultTarget }])}
              className="btn btn-ghost !py-1 !text-xs"
            >
              <Plus className="h-3.5 w-3.5" /> {t("family.editor.addPerson")}
            </button>
          </div>
          <p className="mb-2 text-xs text-stone-500 dark:text-stone-500">
            {t("family.editor.extraHint")}
          </p>
          {extras.length > 0 && (
            <div className="space-y-2">
              {extras.map((ex) => (
                <div key={ex.id} className="flex flex-wrap items-center gap-2">
                  <input
                    className="input flex-1 min-w-[120px]"
                    placeholder={t("family.editor.namePlaceholder")}
                    value={ex.name}
                    onChange={(e) => setExtras((x) => x.map((r) => r.id === ex.id ? { ...r, name: e.target.value } : r))}
                  />
                  <select
                    className="input w-auto"
                    value={ex.rel}
                    onChange={(e) => setExtras((x) => x.map((r) => r.id === ex.id ? { ...r, rel: e.target.value as Extra["rel"] } : r))}
                  >
                    <option value="filho">{t("family.editor.relChildOf")}</option>
                    <option value="irmao">{t("family.editor.relSiblingOf")}</option>
                    <option value="casado">{t("family.editor.spouseOf")}</option>
                  </select>
                  <select
                    className="input w-auto"
                    value={ex.target}
                    onChange={(e) => setExtras((x) => x.map((r) => r.id === ex.id ? { ...r, target: e.target.value } : r))}
                  >
                    {targetOptions(ex.id).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <button type="button" onClick={() => setExtras((x) => x.filter((r) => r.id !== ex.id))} className="rounded-lg p-1.5 text-stone-500 hover:bg-rose-100 hover:text-rose-700 dark:hover:bg-rose-950/40">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
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
    const from = Number(fromId), to = Number(toId);
    const sexOf = (id: number) => persons.find((p) => p.id === id)?.sex;
    const kindFor = (id: number, fallback: string) =>
      sexOf(id) === "F" ? "mãe" : sexOf(id) === "M" ? "pai" : fallback;
    try {
      if (kind === "irmao") {
        // Siblings aren't a stored edge — they share parents. Copy the
        // chosen person's parents onto this one.
        const parents = rels.filter((r) => r.to === to && (r.kind === "pai" || r.kind === "mãe"));
        if (parents.length === 0) {
          toast.error(t("family.editor.noParentsDefined"));
          return;
        }
        for (const p of parents) {
          await createRel.mutateAsync({ from_person_id: p.from, to_person_id: from, kind: p.kind });
        }
      } else if (kind === "filho") {
        // "[from] filho(a) de [to]": link to BOTH parents — the chosen
        // person AND their spouse (so the child gets pai e mãe in one go).
        const toKind = kindFor(to, "pai");
        const links: { parent: number; kind: string }[] = [{ parent: to, kind: toKind }];
        for (const r of rels) {
          if (r.kind !== "cônjuge") continue;
          const sp = r.from === to ? r.to : (r.to === to ? r.from : null);
          if (sp != null && sp !== from && !links.some((l) => l.parent === sp)) {
            links.push({ parent: sp, kind: kindFor(sp, toKind === "pai" ? "mãe" : "pai") });
          }
        }
        for (const l of links) {
          await createRel.mutateAsync({ from_person_id: l.parent, to_person_id: from, kind: l.kind });
        }
      } else {
        await createRel.mutateAsync({ from_person_id: from, to_person_id: to, kind });
      }
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

  const relVerb = (k: string) => {
    if (k === "cônjuge") return t("family.editor.spouseOf");
    const kind = k === "pai" ? t("family.editor.kindFather")
      : k === "mãe" ? t("family.editor.kindMother") : k;
    return `${kind} ${t("family.editor.of")}`;
  };

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
              <div className="flex min-w-0 items-center gap-2.5">
                <PersonAvatar photoId={p.photo_media_id} name={p.name} size={36} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-stone-500">
                    {[p.sex === "M" ? "♂" : p.sex === "F" ? "♀" : null, p.birth_date?.slice(0, 4)].filter(Boolean).join(" · ")}
                  </p>
                </div>
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
            <option value="filho">{t("family.editor.relChildOf")}</option>
            <option value="irmao">{t("family.editor.relSiblingOf")}</option>
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
