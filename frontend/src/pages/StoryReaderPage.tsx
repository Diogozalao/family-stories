import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ArrowLeft, Film, Loader2 } from "lucide-react";
import { useGenerateVideo, useStory } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";

export default function StoryReaderPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const storyId = id ? Number(id) : null;
  const { data: story, isLoading, error } = useStory(storyId);
  const genVideo = useGenerateVideo();

  if (isLoading) {
    return <div className="skeleton h-96 rounded-2xl" />;
  }
  if (error || !story) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300">
        {extractErrorMessage(error, t("common.error"))}
      </div>
    );
  }

  const paragraphs = (story.narrative ?? "").split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);

  const handleGenerateVideo = () => {
    genVideo.mutate(
      { story_id: story.id, mode: "background" },
      {
        onSuccess: () => {
          toast.success(t("videos.processing"));
          navigate("/tasks");
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <article className="mx-auto max-w-3xl">
      <Link to="/stories" className="mb-6 inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
        <ArrowLeft className="h-4 w-4" />
        {t("common.back")}
      </Link>

      <header className="mb-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip chip-accent">{story.event_type}</span>
          <span className="text-xs text-stone-500 dark:text-stone-500">
            {t("stories.generatedOn", { date: new Date(story.created_at).toLocaleDateString() })}
          </span>
          {story.narrative && (
            <span className="text-xs text-stone-500 dark:text-stone-500">
              · {t("stories.readTime", { min: Math.max(1, Math.round(story.narrative.split(/\s+/).length / 220)) })}
            </span>
          )}
        </div>
        <h1 className="mt-3 font-serif text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          {story.title}
        </h1>
      </header>

      <div className="prose-reader">
        {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
      </div>

      <div className="mt-10 border-t border-stone-200 pt-6 dark:border-stone-800">
        <button
          onClick={handleGenerateVideo}
          disabled={genVideo.isPending}
          className="btn btn-accent"
        >
          {genVideo.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Film className="h-4 w-4" />}
          <span>{t("videos.generate")}</span>
        </button>
      </div>
    </article>
  );
}
