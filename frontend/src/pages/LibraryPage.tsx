import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  ChevronLeft, ChevronRight, Loader2, Sparkles, Trash2, UploadCloud, X,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import Photo from "../components/media/Photo";
import { useBuildTimeline, useDeletePhoto, useMedia, usePersons, useReanalyzePhotos, useSetMediaPersons, useUpdateMedia, useUploadPhoto } from "../lib/hooks";
import { photoUrl } from "../lib/photo";
import { extractErrorMessage } from "../lib/api";
import { cn, formatBytes } from "../lib/utils";
import type { MediaFile } from "../lib/types";

export default function LibraryPage() {
  const { t } = useTranslation();
  const { data: media, isLoading } = useMedia();
  const upload = useUploadPhoto();
  const buildTimeline = useBuildTimeline();
  const del = useDeletePhoto();
  const reanalyze = useReanalyzePhotos();

  const [uploadingIdx, setUploadingIdx] = useState<number | null>(null);
  const [uploadingTotal, setUploadingTotal] = useState(0);
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploadingTotal(files.length);
    let okCount = 0;
    for (let i = 0; i < files.length; i++) {
      setUploadingIdx(i + 1);
      try {
        await upload.mutateAsync(files[i]);
        okCount++;
      } catch (err) {
        toast.error(`${files[i].name}: ${extractErrorMessage(err)}`);
      }
    }
    setUploadingIdx(null);
    setUploadingTotal(0);
    if (okCount > 0) {
      toast.success(t("common.success"));
      try {
        await buildTimeline.mutateAsync();
      } catch {
        // The build is best-effort — silent failure here keeps the upload UX clean.
      }
    }
  }, [upload, buildTimeline, t]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp", ".heic"] },
    noClick: true,
    noKeyboard: true,
  });

  const items = media ?? [];
  // Photos still missing an AI description = exactly the ones a re-analysis
  // would touch, i.e. how many Gemini Vision calls it would spend. Shown on
  // the button so the (limited, ~20/day free-tier) quota is never burned by
  // surprise.
  const pendingAnalysis = items.filter(
    (m) => m.media_type === "photo" && !m.ai_description,
  ).length;

  const handleDelete = (m: MediaFile) => {
    if (!window.confirm(t("library.confirmDelete"))) return;
    del.mutate(m.id, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <>
      <PageHeader
        title={t("library.title")}
        subtitle={t("library.subtitle")}
        actions={
          <>
            <span className="chip">
              {items.length === 1
                ? t("library.photoCount", { count: 1 })
                : t("library.photoCount_plural", { count: items.length })}
            </span>
            <button
              className="btn btn-ghost"
              onClick={() => {
                if (pendingAnalysis === 0) return;
                if (!window.confirm(
                  `Vais analisar ${pendingAnalysis} foto(s) com a IA — gasta ${pendingAnalysis} pedido(s) do Gemini Vision (limite ~20/dia). Continuar?`,
                )) return;
                reanalyze.mutate(undefined, {
                  onSuccess: async (r) => {
                    toast.success(
                      r.described > 0
                        ? `${r.described} foto(s) descrita(s) pela IA. Já podes gerar vídeos.`
                        : "Nenhuma foto precisava de análise.",
                    );
                    // As fotos passam a COMPLETED — reconstrói a linha temporal
                    // para os eventos aparecerem (antes ficava vazia).
                    try { await buildTimeline.mutateAsync(); } catch { /* best-effort */ }
                  },
                  onError: (err) => toast.error(extractErrorMessage(err)),
                });
              }}
              disabled={reanalyze.isPending || pendingAnalysis === 0}
              title={pendingAnalysis === 0
                ? "Todas as fotos já estão analisadas."
                : `Analisar ${pendingAnalysis} foto(s) sem descrição (gasta ${pendingAnalysis} pedido(s) Gemini).`}
            >
              {reanalyze.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              <span>Re-analisar IA{pendingAnalysis > 0 ? ` (${pendingAnalysis})` : ""}</span>
            </button>
            <button className="btn btn-primary" onClick={open}>
              <UploadCloud className="h-4 w-4" />
              <span>{t("common.upload")}</span>
            </button>
          </>
        }
      />

      <div
        {...getRootProps()}
        className={
          "relative rounded-2xl border-2 border-dashed p-8 text-center transition " +
          (isDragActive
            ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
            : "border-stone-300 bg-white/60 dark:border-stone-700 dark:bg-stone-900/40")
        }
      >
        <input {...getInputProps()} />
        <UploadCloud className="mx-auto h-8 w-8 text-stone-400" />
        <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
          {t("library.dropzone")}{" "}
          <button type="button" onClick={open} className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("library.browseFiles")}
          </button>
        </p>
        {uploadingIdx !== null && (
          <p className="mt-3 inline-flex items-center gap-2 text-xs text-stone-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            {t("library.uploading", { current: uploadingIdx, total: uploadingTotal })}
          </p>
        )}
      </div>

      {/* Gallery */}
      <section className="mt-6">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="skeleton aspect-square rounded-xl" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
            {t("library.empty")}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {items.map((m, idx) => (
              <div key={m.id} className="group relative aspect-square overflow-hidden rounded-xl border border-stone-200 bg-stone-100 dark:border-stone-800 dark:bg-stone-900">
                <Photo
                  mediaId={m.id}
                  alt={m.original_filename}
                  onClick={() => setViewerIndex(idx)}
                  className="h-full w-full cursor-zoom-in object-cover transition duration-500 group-hover:scale-105"
                />
                {(m.status === "processing" || m.status === "pending") && (
                  <span className="pointer-events-none absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {t("library.analyzing")}
                  </span>
                )}
                <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/40 to-transparent p-3">
                  <p className="truncate text-xs font-medium text-white/95">{m.original_filename}</p>
                  <div className="flex items-center gap-2 text-[10px] text-white/60">
                    {m.file_size !== undefined && <span>{formatBytes(m.file_size)}</span>}
                    {m.date_taken && (
                      <>
                        <span>·</span>
                        <span>{new Date(m.date_taken).toLocaleDateString()}</span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(m)}
                  className="absolute right-2 top-2 rounded-full bg-black/50 p-1.5 text-white opacity-0 backdrop-blur transition hover:bg-black/70 group-hover:opacity-100"
                  aria-label={t("library.delete")}
                  title={t("library.delete")}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {viewerIndex !== null && items[viewerIndex] && (
        <Viewer
          items={items}
          index={viewerIndex}
          onChange={setViewerIndex}
          onClose={() => setViewerIndex(null)}
        />
      )}
    </>
  );
}

function Viewer({
  items,
  index,
  onChange,
  onClose,
}: {
  items: MediaFile[];
  index: number;
  onChange: (i: number) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const cur = items[index];
  const prev = () => onChange((index - 1 + items.length) % items.length);
  const next = () => onChange((index + 1) % items.length);

  const updateMedia = useUpdateMedia();
  const buildTimeline = useBuildTimeline();
  const [dateInput, setDateInput] = useState<string>(cur.date_taken?.slice(0, 10) ?? "");

  // Reset the date field whenever the viewer moves to another photo.
  useEffect(() => {
    setDateInput(cur.date_taken?.slice(0, 10) ?? "");
  }, [cur.id, cur.date_taken]);

  const saveDate = async () => {
    try {
      await updateMedia.mutateAsync({ id: cur.id, date_taken: dateInput || "" });
      // Re-sync the timeline so the new date shows up there too (best-effort).
      await buildTimeline.mutateAsync().catch(() => {});
      toast.success(t("common.success"));
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };
  const dateChanged = (cur.date_taken?.slice(0, 10) ?? "") !== dateInput;

  // Tag which family members appear in this photo.
  const { data: persons } = usePersons();
  const setPersons = useSetMediaPersons();
  const [tagged, setTagged] = useState<number[]>(cur.person_ids ?? []);
  useEffect(() => { setTagged(cur.person_ids ?? []); }, [cur.id, cur.person_ids]);
  const togglePerson = (pid: number) => {
    const updated = tagged.includes(pid) ? tagged.filter((x) => x !== pid) : [...tagged, pid];
    setTagged(updated);
    setPersons.mutate(
      { id: cur.id, person_ids: updated },
      { onError: (err) => toast.error(extractErrorMessage(err)) },
    );
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/90 backdrop-blur animate-fade-in">
      <button
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        aria-label="Close"
      >
        <X className="h-5 w-5" />
      </button>

      {items.length > 1 && (
        <>
          <button
            onClick={prev}
            className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2.5 text-white hover:bg-white/20"
            aria-label="Previous"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={next}
            className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2.5 text-white hover:bg-white/20"
            aria-label="Next"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </>
      )}

      <div className="flex max-h-[92vh] max-w-[95vw] flex-col">
        <img
          src={photoUrl(cur.id)}
          alt={cur.original_filename}
          className="max-h-[78vh] max-w-[95vw] rounded-xl object-contain animate-scale-in"
        />
        <div className="mt-3 flex items-center justify-between gap-4 text-xs text-white/80">
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-white/95">{cur.original_filename}</p>
            <div className="mt-0.5 flex flex-wrap gap-x-2 text-white/60">
              {cur.date_taken && <span>{new Date(cur.date_taken).toLocaleString()}</span>}
              {cur.ai_setting && <span>· {cur.ai_setting}</span>}
            </div>
            {cur.ai_description && (
              <p className="mt-2 line-clamp-2 max-w-3xl text-[11px] italic text-white/70">
                {cur.ai_description}
              </p>
            )}
            <div className="mt-3 flex items-center gap-2">
              <label className="text-[11px] text-white/60">{t("library.dateLabel")}</label>
              <input
                type="date"
                value={dateInput}
                onChange={(e) => setDateInput(e.target.value)}
                onKeyDown={(e) => e.stopPropagation()}
                className="rounded-md border border-white/20 bg-white/10 px-2 py-1 text-xs text-white [color-scheme:dark]"
              />
              {dateChanged && (
                <button
                  onClick={saveDate}
                  disabled={updateMedia.isPending || buildTimeline.isPending}
                  className="inline-flex items-center gap-1 rounded-md bg-white/15 px-2 py-1 text-xs text-white hover:bg-white/25"
                >
                  {(updateMedia.isPending || buildTimeline.isPending)
                    ? <Loader2 className="h-3 w-3 animate-spin" />
                    : null}
                  {t("library.saveDate")}
                </button>
              )}
            </div>
            {(persons ?? []).length > 0 && (
              <div className="mt-3">
                <p className="mb-1 text-[11px] text-white/60">{t("library.peopleInPhoto")}</p>
                <div className="flex max-h-24 flex-wrap gap-1.5 overflow-y-auto">
                  {(persons ?? []).map((p) => (
                    <button
                      key={p.id}
                      onClick={() => togglePerson(p.id)}
                      className={cn(
                        "rounded-full border px-2 py-0.5 text-[11px] transition",
                        tagged.includes(p.id)
                          ? "border-brand-400 bg-brand-500/30 text-white"
                          : "border-white/20 bg-white/5 text-white/70 hover:bg-white/10",
                      )}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <span className="shrink-0 rounded-full bg-white/10 px-2.5 py-1">{index + 1} / {items.length}</span>
        </div>
      </div>
    </div>
  );
}
