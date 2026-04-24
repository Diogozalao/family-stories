import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { FileUp, Loader2, Search, User as UserIcon } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { usePersons, useUploadGedcom } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { initials } from "../lib/utils";

export default function FamilyPage() {
  const { t } = useTranslation();
  const { data: persons, isLoading } = usePersons();
  const upload = useUploadGedcom();
  const [query, setQuery] = useState("");

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    try {
      const r = await upload.mutateAsync(files[0]);
      toast.success(`${r.message ?? t("common.success")}`);
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  }, [upload, t]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "application/octet-stream": [".ged", ".gedcom"], "text/plain": [".ged", ".gedcom"] },
    maxFiles: 1,
    noClick: true,
    noKeyboard: true,
  });

  const items = persons ?? [];
  const filtered = query
    ? items.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
    : items;

  return (
    <>
      <PageHeader
        title={t("family.title")}
        subtitle={t("family.subtitle")}
        actions={
          <>
            <span className="chip">{t("family.persons")}: {items.length}</span>
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
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <div key={p.id} className="card-soft p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold text-white">
                  {initials(p.name) || <UserIcon className="h-4 w-4" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.name}</p>
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
            </div>
          ))}
        </div>
      )}
    </>
  );
}
