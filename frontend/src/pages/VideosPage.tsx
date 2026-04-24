import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, Film, Play, X } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useVideos, videoUrl } from "../lib/hooks";
import type { Video } from "../lib/types";

export default function VideosPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useVideos();
  const [playing, setPlaying] = useState<Video | null>(null);

  const videos = data ?? [];

  return (
    <>
      <PageHeader title={t("videos.title")} subtitle={t("videos.subtitle")} />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-48 rounded-2xl" />
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          <Film className="mx-auto mb-3 h-8 w-8 text-stone-400" />
          {t("videos.empty")}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} onPlay={() => setPlaying(v)} />
          ))}
        </div>
      )}

      {playing && playing.filename && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/90 backdrop-blur animate-fade-in p-4">
          <button
            onClick={() => setPlaying(null)}
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
          <video
            key={playing.id}
            src={videoUrl(playing.filename)}
            controls
            autoPlay
            className="max-h-[85vh] max-w-[95vw] rounded-xl shadow-lift animate-scale-in"
          />
        </div>
      )}
    </>
  );
}

function VideoCard({ video, onPlay }: { video: Video; onPlay: () => void }) {
  const { t } = useTranslation();
  const ready = video.status === "ready" && video.filename;

  return (
    <article className="card overflow-hidden">
      <div className="relative aspect-video bg-gradient-to-br from-stone-800 to-stone-900">
        {ready ? (
          <button onClick={onPlay} className="group absolute inset-0 flex items-center justify-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/90 text-stone-900 shadow-lift transition group-hover:scale-105">
              <Play className="h-6 w-6 translate-x-0.5" fill="currentColor" />
            </span>
          </button>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-white/60">
            {video.status === "failed" ? t("common.error") : t("videos.processing")}
          </div>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-500">
          <span className="chip">{video.status}</span>
          {video.photos_used !== null && video.photos_used !== undefined && (
            <span>{t("videos.photos", { count: video.photos_used })}</span>
          )}
          {video.size_mb !== null && video.size_mb !== undefined && (
            <span>· {t("videos.size", { size: video.size_mb.toFixed(1) })}</span>
          )}
        </div>
        <p className="mt-1 truncate font-medium">{video.filename ?? `#${video.id}`}</p>
        {ready && (
          <a
            href={videoUrl(video.filename!)}
            download
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
          >
            <Download className="h-3.5 w-3.5" />
            {t("videos.download")}
          </a>
        )}
        {video.error_message && (
          <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{video.error_message}</p>
        )}
      </div>
    </article>
  );
}
