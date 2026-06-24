import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Download, FileUp, Loader2, Pencil, Search, Trash2, User as UserIcon, Users, X } from "lucide-react";

import { useQueryClient } from "@tanstack/react-query";

import PageHeader from "../components/ui/PageHeader";
import FamilyTree from "../components/family/FamilyTree";
import FamilyEditor from "../components/family/FamilyEditor";
import PersonGallery from "../components/family/PersonGallery";
import { downloadGedcom, extractErrorMessage, isLostResponse } from "../lib/api";
import { useClearFamily, useFamilies, usePersons, useUploadGedcom } from "../lib/hooks";
import type { Person } from "../lib/types";
import { cn, initials } from "../lib/utils";

const UNLABELED = "__unlabeled__";

export default function FamilyPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: persons, isLoading } = usePersons();
  const { data: families } = useFamilies();
  const upload = useUploadGedcom();
  const clear  = useClearFamily();

  const [query, setQuery] = useState("");
  /** Active label filter; "" means "all". */
  const [activeLabel, setActiveLabel] = useState<string>("");
  /** Holds the file selected by drag/click until the user confirms a label. */
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [labelInput, setLabelInput]   = useState("");
  /** Family page view: flat list of people or the interactive tree. */
  const [view, setView] = useState<"list" | "tree">("list");
  /** Full-screen manual tree editor overlay. */
  const [editorOpen, setEditorOpen] = useState(false);
  /** Person whose photo gallery is open (null = closed). */
  const [galleryPerson, setGalleryPerson] = useState<Person | null>(null);

  const onDrop = useCallback((files: File[]) => {
    if (!files.length) return;
    setPendingFile(files[0]);
    // Pre-fill the family label from the file name so each import lands in its
    // own group by default — keeps multiple trees cleanly separated instead of
    // piling several unlabelled families together. The user can still edit it.
    const stem = files[0].name
      .replace(/\.(ged|gedcom)$/i, "")
      .replace(/[_-]+/g, " ")
      .trim();
    setLabelInput(stem.slice(0, 120));
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "application/octet-stream": [".ged", ".gedcom"], "text/plain": [".ged", ".gedcom"] },
    maxFiles: 1,
    noClick: true,
    noKeyboard: true,
  });

  const handleConfirmUpload = async () => {
    if (!pendingFile) return;
    const label = labelInput.trim();
    const before = (persons ?? []).length;
    try {
      const r = await upload.mutateAsync({ file: pendingFile, familyLabel: label || undefined });
      const count   = (r.persons_created ?? 0) + (r.persons_updated ?? 0);
      const skipped = r.persons_skipped ?? 0;
      const lbl     = label || t("family.unlabeled");
      toast.success(
        skipped > 0
          ? t("family.importedSummaryWithSkipped", { created: count, skipped, label: lbl })
          : t("family.importedSummary", { count, label: lbl }),
        { description: `${r.families_processed ?? 0} famílias · ${r.relations_added ?? 0} ligações` },
      );
      setPendingFile(null);
      setLabelInput("");
    } catch (err) {
      // A lost response (no HTTP status) is the classic free-tier symptom:
      // the backend was asleep, the import still ran and committed, but the
      // connection dropped before the reply came back. Rather than scaring
      // the user with "Network Error", give the server a moment, refetch,
      // and report honestly based on whether the data actually landed. We do
      // NOT re-POST — that would duplicate events; the import isn't fully
      // idempotent. The user can simply retry if nothing came through.
      if (isLostResponse(err)) {
        await new Promise((r) => setTimeout(r, 2500));
        await qc.refetchQueries({ queryKey: ["persons"] });
        await qc.invalidateQueries({ queryKey: ["families"] });
        await qc.invalidateQueries({ queryKey: ["graph"] });
        const after = (qc.getQueryData<Person[]>(["persons"]) ?? []).length;
        if (after > before) {
          toast.success(t("family.importColdSuccess"));
          setPendingFile(null);
          setLabelInput("");
        } else {
          toast.error(t("family.importColdRetry"));
        }
        return;
      }
      toast.error(extractErrorMessage(err));
    }
  };

  const handleClearLabel = async (label: string | null) => {
    if (!confirm(t(label ? "family.confirmRemoveLabel" : "family.confirmRemoveAll", { label }))) return;
    try {
      await clear.mutateAsync({ familyLabel: label ?? undefined });
      toast.success(t("common.success"));
      if (activeLabel === (label ?? UNLABELED)) setActiveLabel("");
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  const items = persons ?? [];
  // The tree endpoint filters by a concrete label only (not the "unlabeled" bucket).
  const treeLabel = activeLabel && activeLabel !== UNLABELED ? activeLabel : undefined;
  const filtered = useMemo(() => {
    let list = items;
    if (activeLabel) {
      const want = activeLabel === UNLABELED ? null : activeLabel;
      list = list.filter((p) => (p.family_label ?? null) === want);
    }
    if (query) {
      const q = query.toLowerCase();
      list = list.filter((p) => p.name.toLowerCase().includes(q));
    }
    return list;
  }, [items, activeLabel, query]);

  const familyChips = families ?? [];

  return (
    <>
      <PageHeader
        title={t("family.title")}
        subtitle={t("family.subtitle")}
        actions={
          <>
            <span className="chip">{t("family.persons")}: {items.length}</span>
            <button className="btn btn-ghost" onClick={() => setEditorOpen(true)}>
              <Pencil className="h-4 w-4" />
              <span>{t("family.editTree")}</span>
            </button>
            {items.length > 0 && (
              <button
                className="btn btn-ghost"
                onClick={async () => {
                  try { await downloadGedcom(treeLabel); }
                  catch (err) { toast.error(extractErrorMessage(err)); }
                }}
              >
                <Download className="h-4 w-4" />
                <span>{t("family.exportGedcom")}</span>
              </button>
            )}
            <button className="btn btn-primary" onClick={open} disabled={upload.isPending}>
              {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
              <span>{t("family.importGedcom")}</span>
            </button>
          </>
        }
      />

      <div
        {...getRootProps()}
        className={
          "mb-6 rounded-2xl border-2 border-dashed p-6 text-center transition " +
          (isDragActive
            ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
            : "border-stone-300 bg-white/60 dark:border-stone-700 dark:bg-stone-900/40")
        }
      >
        <input {...getInputProps()} />
        <p className="text-sm text-stone-600 dark:text-stone-400">
          {t("family.dropGedcom")}{" "}
          <button type="button" onClick={open} className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("library.browseFiles")}
          </button>
        </p>
      </div>

      {/* Family group chips */}
      {familyChips.length > 0 && (
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <FamilyChip
            active={activeLabel === ""}
            label={t("family.allFamilies")}
            count={items.length}
            onClick={() => setActiveLabel("")}
          />
          {familyChips.map((f) => {
            const key   = f.label ?? UNLABELED;
            const name  = f.label ?? t("family.unlabeled");
            return (
              <FamilyChip
                key={key}
                active={activeLabel === key}
                label={name}
                count={f.count}
                onClick={() => setActiveLabel(key)}
                onDelete={() => handleClearLabel(f.label)}
              />
            );
          })}
        </div>
      )}

      {items.length > 0 && (
        <div className="mb-4 flex w-fit gap-1 rounded-xl border border-stone-200 p-1 text-sm dark:border-stone-800">
          <button
            onClick={() => setView("list")}
            className={cn("rounded-lg px-3 py-1.5", view === "list"
              ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
              : "text-stone-600 dark:text-stone-400")}
          >
            {t("family.viewList")}
          </button>
          <button
            onClick={() => setView("tree")}
            className={cn("rounded-lg px-3 py-1.5", view === "tree"
              ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
              : "text-stone-600 dark:text-stone-400")}
          >
            {t("family.viewTree")}
          </button>
        </div>
      )}

      {view === "tree" ? (
        <FamilyTree familyLabel={treeLabel} />
      ) : (
      <>
      {items.length > 0 && (
        <div className="mb-5 relative max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("common.search")}
            className="input pl-9"
          />
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          {t("family.noTree")}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          {t("family.noMatch")}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <button
              key={p.id}
              onClick={() => setGalleryPerson(p)}
              className="card-soft p-4 text-left transition hover:-translate-y-0.5 hover:shadow-lift"
              title={t("person.addPhotos")}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold text-white">
                  {initials(p.name) || <UserIcon className="h-4 w-4" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="truncate font-medium">{p.name}</p>
                    {p.family_label && (
                      <span className="chip chip-accent shrink-0">{p.family_label}</span>
                    )}
                  </div>
                  {p.birth_date && (
                    <p className="text-xs text-stone-500 dark:text-stone-500">
                      {t("family.born", { date: p.birth_date })}
                      {p.birth_place && " " + t("family.bornAt", { place: p.birth_place })}
                    </p>
                  )}
                  {p.gedcom_id && (
                    <p className="mt-1 font-mono text-[10px] text-stone-400">{p.gedcom_id}</p>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
      </>
      )}

      {editorOpen && (
        <FamilyEditor familyLabel={treeLabel} onClose={() => setEditorOpen(false)} />
      )}

      {galleryPerson && (
        <PersonGallery
          personId={galleryPerson.id}
          personName={galleryPerson.name}
          onClose={() => setGalleryPerson(null)}
        />
      )}

      {/* ── Family-label dialog ─────────────────────────────── */}
      {pendingFile && (
        <LabelDialog
          fileName={pendingFile.name}
          value={labelInput}
          onChange={setLabelInput}
          onCancel={() => setPendingFile(null)}
          onConfirm={handleConfirmUpload}
          pending={upload.isPending}
        />
      )}
    </>
  );
}

// ── Helpers ───────────────────────────────────────────────

function FamilyChip({
  label, count, active, onClick, onDelete,
}: {
  label: string; count: number; active: boolean;
  onClick: () => void; onDelete?: () => void;
}) {
  return (
    <div className={cn(
      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition",
      active
        ? "border-brand-400 bg-brand-100 text-brand-800 dark:border-brand-700 dark:bg-brand-900/40 dark:text-brand-200"
        : "border-stone-200 bg-white text-stone-700 hover:bg-stone-50 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300",
    )}>
      <button onClick={onClick} className="flex items-center gap-1.5">
        <Users className="h-3 w-3" />
        <span>{label}</span>
        <span className="text-stone-500 dark:text-stone-500">· {count}</span>
      </button>
      {onDelete && (
        <button
          onClick={onDelete}
          className="ml-0.5 rounded-full p-0.5 text-stone-500 transition hover:bg-rose-100 hover:text-rose-700 dark:hover:bg-rose-950/40"
          aria-label="Delete family"
          title="Delete this family"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function LabelDialog({
  fileName, value, onChange, onCancel, onConfirm, pending,
}: {
  fileName: string; value: string;
  onChange: (v: string) => void;
  onCancel: () => void; onConfirm: () => void;
  pending: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-lift dark:border-stone-800 dark:bg-stone-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-serif text-xl font-semibold tracking-tight">{t("family.labelDialogTitle")}</h3>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t("family.labelDialogLead")}</p>
          </div>
          <button onClick={onCancel} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800" aria-label="Cancel">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5">
          <label className="label">{t("family.labelField")}</label>
          <input
            autoFocus
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={t("family.labelPlaceholder")}
            className="input"
            maxLength={120}
            onKeyDown={(e) => {
              if (e.key === "Enter") onConfirm();
              if (e.key === "Escape") onCancel();
            }}
          />
          <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-500">{t("family.labelHint")}</p>
        </div>

        <p className="mt-4 truncate rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-600 dark:bg-stone-800 dark:text-stone-400">
          📄 {fileName}
        </p>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onCancel} className="btn btn-ghost">{t("common.cancel")}</button>
          <button onClick={onConfirm} disabled={pending} className="btn btn-primary">
            {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
            <span>{t("family.importGedcom")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
