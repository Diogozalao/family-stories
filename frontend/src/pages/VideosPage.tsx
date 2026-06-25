import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Film, Loader2, Plus, Sparkles, X } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import VideoCard from "../components/media/VideoCard";
import { useGenerateVideo, useStories, useVideos } from "../lib/hooks";
import { extractErrorMessage, isLostResponse } from "../lib/api";
import { cn } from "../lib/utils";

export default function VideosPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useVideos();
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
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      )}

      {pickerOpen && <StoryPicker onClose={() => setPickerOpen(false)} />}
    </>
  );
}

function StoryPicker({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { data: stories, isLoading } = useStories();
  const gen = useGenerateVideo();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const handleGenerate = () => {
    if (selectedId === null) return;
    // Background render: a 720p video takes several minutes, so we don't block
    // the browser on a long request. The server marks the video "processing"
    // right away and this list polls until the MP4 lands (videos are produced
    // by running the backend locally — the free cloud tier OOMs at 720p).
    toast.info(t("videos.generating"));
    gen.mutate(
      { story_id: selectedId, mode: "background" },
      {
        onSuccess: () => {
          toast.success(t("videos.processing"));
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
              {t("videos.pickLead")}
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
              {t("videos.noStories")}
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
