import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Download, Film, Loader2, Play, Plus, Sparkles, X } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useGenerateVideo, useStories, useVideos, videoUrl } from "../lib/hooks";
import { extractErrorMessage, isLostResponse } from "../lib/api";
import { cn } from "../lib/utils";
import type { Video } from "../lib/types";

export default function VideosPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useVideos();
  const [playing, setPlaying] = useState<Video | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const videos = data ?? [];

  return (
    <>
      <PageHeader
        title={t("videos.title")}
        subtitle={t("videos.subtitle")}
        actions={
          <button onClick={() => setPickerOpen(true)} className="btn btn-accent">
            <Plus className="h-4 w-4" />
            <span>{t("videos.generate")}</span>
          </button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-48 rounded-2xl" />
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          <Film className="mx-auto mb-3 h-8 w-8 text-stone-400" />
          <p>{t("videos.empty")}</p>
          <button onClick={() => setPickerOpen(true)} className="btn btn-accent mt-5">
            <Sparkles className="h-4 w-4" />
            <span>{t("videos.generate")}</span>
          </button>
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

      {pickerOpen && <StoryPicker onClose={() => setPickerOpen(false)} />}
    </>
  );
}

function VideoCard({ video, onPlay }: { video: Video; onPlay: () => void }) {
  const { t } = useTranslation();
  const ready = video.status === "completed" && !!video.filename;

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
          <StatusChip status={video.status} />
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

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    processing: { label: "A processar", cls: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300" },
    completed:  { label: "Pronto",      cls: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
    failed:     { label: "Falhou",      cls: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300" },
  };
  const m = map[status] ?? { label: status, cls: "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300" };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${m.cls}`}>{m.label}</span>;
}

function StoryPicker({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { data: stories, isLoading } = useStories();
  const gen = useGenerateVideo();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const handleGenerate = () => {
    if (selectedId === null) return;
    // Synchronous render: keeps the free-tier instance awake instead of
    // handing the job to a background worker that gets killed when the
    // instance sleeps (the old "Tarefa abandonada" failure). It can take
    // 1–2 min; the videos list polls so the result appears even if the
    // request itself times out at the proxy.
    toast.info(t("videos.generating"));
    gen.mutate(
      { story_id: selectedId, mode: "sync" },
      {
        onSuccess: () => {
          toast.success(t("videos.done"));
          onClose();
        },
        onError: (err) => {
          if (isLostResponse(err)) {
            toast.info(t("videos.stillRendering"));
            onClose();
          } else {
            toast.error(extractErrorMessage(err));
          }
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/70 backdrop-blur p-4 animate-fade-in" onClick={onClose}>
      <div
        className="card w-full max-w-2xl shadow-lift animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-4 border-b border-stone-100 p-6 dark:border-stone-800">
          <div>
            <h2 className="font-serif text-xl font-semibold tracking-tight">
              {t("videos.generate")}
            </h2>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              Escolhe a história a transformar em vídeo documental.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
            aria-label={t("common.close")}
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="max-h-[60vh] overflow-y-auto p-6">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton h-16 rounded-xl" />
              ))}
            </div>
          ) : (stories ?? []).length === 0 ? (
            <p className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-6 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
              Ainda não tens histórias. Cria uma primeiro em Gerar.
            </p>
          ) : (
            <div className="space-y-2">
              {(stories ?? []).map((s) => {
                const active = selectedId === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedId(s.id)}
                    className={cn(
                      "w-full rounded-xl border p-4 text-left transition",
                      active
                        ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
                        : "border-stone-200 bg-white hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-700",
                    )}
                  >
                    <div className="flex items-center gap-2 text-xs">
                      <span className="chip chip-accent">{s.event_type}</span>
                      <span className="text-stone-500 dark:text-stone-500">
                        {new Date(s.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="mt-2 font-medium leading-snug line-clamp-1">{s.title}</p>
                    <p className="mt-1 text-xs text-stone-500 line-clamp-2 dark:text-stone-500">
                      {(s.narrative ?? "").slice(0, 160)}…
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-stone-100 p-4 dark:border-stone-800">
          <button onClick={onClose} className="btn btn-ghost">
            {t("common.cancel")}
          </button>
          <button
            onClick={handleGenerate}
            disabled={selectedId === null || gen.isPending}
            className="btn btn-accent"
          >
            {gen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            <span>{t("videos.generate")}</span>
          </button>
        </footer>
      </div>
    </div>
  );
}
