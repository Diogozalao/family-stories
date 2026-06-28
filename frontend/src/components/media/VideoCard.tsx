import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Download, Loader2, Play, Trash2, X } from "lucide-react";

import Photo from "./Photo";
import { downloadVideoUrl, useDeleteVideo, videoUrl } from "../../lib/hooks";
import { api, extractErrorMessage } from "../../lib/api";
import { cn } from "../../lib/utils";
import type { Video } from "../../lib/types";

const SUBTITLE_SIZE_CLASS: Record<string, string> = {
  small:  "subs-small",
  medium: "subs-medium",
  large:  "subs-large",
};

/**
 * Self-contained documentary-video card, shared by the global Videos page and
 * the project Videos tab. Handles its own play lightbox, download, delete and
 * a poster frame (the story's first photo) so both places look identical.
 */
export default function VideoCard({ video }: { video: Video }) {
  const { t } = useTranslation();
  const del = useDeleteVideo();
  const [playing, setPlaying] = useState(false);
  const [vttUrl, setVttUrl] = useState<string | null>(null);
  const ready = video.status === "completed" && !!video.filename;

  // Fetch the .vtt and hand the player a same-origin blob URL — sidesteps the
  // cross-origin restrictions on <track> without needing crossorigin on the
  // (Storage-redirected) video element.
  useEffect(() => {
    if (!playing || !video.subtitle_url) return;
    let blobUrl: string | null = null;
    let cancelled = false;
    api.get(video.subtitle_url, { responseType: "text" })
      .then((r) => {
        if (cancelled) return;
        blobUrl = URL.createObjectURL(new Blob([r.data], { type: "text/vtt" }));
        setVttUrl(blobUrl);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      setVttUrl(null);
    };
  }, [playing, video.subtitle_url]);

  const handleDelete = () => {
    if (!confirm(t("videos.confirmDelete"))) return;
    setPlaying(false);
    del.mutate(video.id, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <article className="card overflow-hidden">
      <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-stone-800 to-stone-900">
        {/* Poster frame behind the controls. */}
        {video.poster_media_id && (
          <Photo
            mediaId={video.poster_media_id}
            className={`absolute inset-0 h-full w-full object-cover ${ready ? "opacity-60" : "opacity-25"}`}
          />
        )}
        {ready ? (
          <button onClick={() => setPlaying(true)} className="group absolute inset-0 flex items-center justify-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/90 text-stone-900 shadow-lift transition group-hover:scale-105">
              <Play className="h-6 w-6 translate-x-0.5" fill="currentColor" />
            </span>
          </button>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-white/80">
            {video.status === "failed" ? t("common.error") : t("videos.processing")}
          </div>
        )}
        <button
          onClick={handleDelete}
          disabled={del.isPending}
          className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-stone-950/55 text-white/90 transition hover:bg-rose-600 disabled:opacity-50"
          aria-label={t("videos.delete")}
          title={t("videos.delete")}
        >
          {del.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
        </button>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-500">
          <StatusChip status={video.status} t={t} />
          {video.photos_used != null && <span>{t("videos.photos", { count: video.photos_used })}</span>}
          {video.size_mb != null && <span>· {t("videos.size", { size: video.size_mb.toFixed(1) })}</span>}
        </div>
        <p className="mt-1 truncate font-medium">{video.title || video.filename || `#${video.id}`}</p>
        {ready && (
          <a href={downloadVideoUrl(video.filename!)}
             className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
            <Download className="h-3.5 w-3.5" /> {t("videos.download")}
          </a>
        )}
        {video.error_message && (
          <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{video.error_message}</p>
        )}
      </div>

      {playing && video.filename && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/90 p-4 backdrop-blur" onClick={() => setPlaying(false)}>
          <button onClick={() => setPlaying(false)} className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20" aria-label={t("common.close")}>
            <X className="h-5 w-5" />
          </button>
          <video
            key={video.id}
            src={videoUrl(video.filename)}
            controls
            autoPlay
            className={cn(
              "max-h-[85vh] max-w-[95vw] rounded-xl shadow-lift",
              SUBTITLE_SIZE_CLASS[video.subtitle_size ?? "medium"] ?? "subs-medium",
            )}
            onClick={(e) => e.stopPropagation()}
          >
            {vttUrl && (
              <track kind="subtitles" srcLang="pt" label={t("videos.subtitles")} default src={vttUrl} />
            )}
          </video>
        </div>
      )}
    </article>
  );
}

function StatusChip({ status, t }: { status: string; t: (k: string) => string }) {
  const map: Record<string, { key: string; cls: string }> = {
    processing: { key: "tasks.state.running", cls: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300" },
    completed:  { key: "tasks.state.done",    cls: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
    failed:     { key: "tasks.state.failed",  cls: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300" },
  };
  const m = map[status] ?? { key: "", cls: "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300" };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${m.cls}`}>{m.key ? t(m.key) : status}</span>;
}
