import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Loader2, Sparkles, Trash2, UploadCloud } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import Photo from "../components/media/Photo";
import PhotoViewer from "../components/media/PhotoViewer";
import { useBuildTimeline, useDeletePhoto, useMedia, useReanalyzePhotos, useUploadPhoto } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { formatBytes } from "../lib/utils";
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
                if (!window.confirm(t("library.reanalyzeConfirm", { count: pendingAnalysis }))) return;
                reanalyze.mutate(undefined, {
                  onSuccess: async (r) => {
                    toast.success(
                      r.described > 0
                        ? t("library.reanalyzeDone", { count: r.described })
                        : t("library.reanalyzeNone"),
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
                ? t("library.reanalyzeAllDone")
                : t("library.reanalyzeTitle", { count: pendingAnalysis })}
            >
              {reanalyze.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              <span>{t("library.reanalyze")}{pendingAnalysis > 0 ? ` (${pendingAnalysis})` : ""}</span>
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
        <PhotoViewer
          items={items}
          index={viewerIndex}
          onChange={setViewerIndex}
          onClose={() => setViewerIndex(null)}
        />
      )}
    </>
  );
}

