import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ArrowLeft, Check, Film, FileDown, FolderKanban, Loader2, Pencil, RefreshCw, Sparkles, X } from "lucide-react";
import { useGenerateVideo, useProjects, useRegenerateStory, useStory, useUpdateStory } from "../lib/hooks";
import { extractErrorMessage, isLostResponse } from "../lib/api";

export default function StoryReaderPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const storyId = id ? Number(id) : null;
  const { data: story, isLoading, isFetching, error, refetch } = useStory(storyId);
  const genVideo = useGenerateVideo();
  const update = useUpdateStory();
  const regen = useRegenerateStory();
  const { data: projects } = useProjects();

  const [regenOpen, setRegenOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
  // The project this story belongs to (if it was generated inside one) —
  // shown as a badge so the story's "home" is always clear.
  const project = projects?.find((p) => p.id === story?.project_id);

  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftNarrative, setDraftNarrative] = useState("");

  // Reset the draft whenever the source story changes (after a refetch
  // or when the user navigates between stories).
  useEffect(() => {
    if (story) {
      setDraftTitle(story.title);
      setDraftNarrative(story.narrative ?? "");
    }
  }, [story?.id, story?.title, story?.narrative]);

  if (isLoading) {
    return <div className="skeleton h-96 rounded-2xl" />;
  }
  if (error || !story) {
    const lost = isLostResponse(error);
    return (
      <div className="mx-auto max-w-3xl">
        <Link to="/stories" className="mb-6 inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
          <ArrowLeft className="h-4 w-4" />
          {t("common.back")}
        </Link>
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300">
          <p>
            {lost
              ? t("storyReader.loadError")
              : extractErrorMessage(error, t("common.error"))}
          </p>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="btn btn-ghost mt-4"
          >
            {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span>{t("common.retry")}</span>
          </button>
        </div>
      </div>
    );
  }

  const paragraphs = (story.narrative ?? "").split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);

  const handleGenerateVideo = () => {
    // Background render: a 720p video can take several minutes to build, so
    // we don't block the browser on a long request. The server creates the
    // video as "processing" immediately and the Videos page polls until the
    // finished MP4 lands (works great when the backend runs locally, which is
    // how videos are produced — the free cloud tier OOMs at 720p).
    toast.info(t("videos.generating"));
    genVideo.mutate(
      { story_id: story.id, mode: "background" },
      {
        onSuccess: () => {
          toast.success(t("videos.processing"));
          navigate("/videos");
        },
        onError: (err) => {
          if (isLostResponse(err)) {
            toast.info(t("videos.stillRendering"));
            navigate("/videos");
          } else {
            toast.error(extractErrorMessage(err));
          }
        },
      },
    );
  };

  const titleChanged     = draftTitle.trim() !== story.title;
  const narrativeChanged = draftNarrative.trim() !== (story.narrative ?? "").trim();
  const dirty            = titleChanged || narrativeChanged;

  const handleSave = () => {
    if (!dirty) {
      setEditing(false);
      return;
    }
    update.mutate(
      {
        id:        story.id,
        title:     titleChanged     ? draftTitle.trim()     : undefined,
        narrative: narrativeChanged ? draftNarrative.trim() : undefined,
      },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          setEditing(false);
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  const handleCancel = () => {
    setDraftTitle(story.title);
    setDraftNarrative(story.narrative ?? "");
    setEditing(false);
  };

  const handleRegenerate = () => {
    regen.mutate(
      { id: story.id, feedback: feedback.trim() },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          setRegenOpen(false);
          setFeedback("");
          refetch();
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <article className="lm-print-story mx-auto max-w-3xl">
      <Link to="/stories" className="lm-no-print mb-6 inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
        <ArrowLeft className="h-4 w-4" />
        {t("common.back")}
      </Link>

      <header className="mb-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip chip-accent">{story.event_type}</span>
          {project && (
            <Link
              to={`/projects/${project.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-700 transition hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
            >
              <FolderKanban className="h-3 w-3" />
              {project.name}
            </Link>
          )}
          <span className="text-xs text-stone-500 dark:text-stone-500">
            {t("stories.generatedOn", { date: new Date(story.created_at).toLocaleDateString() })}
          </span>
          {story.narrative && (
            <span className="text-xs text-stone-500 dark:text-stone-500">
              · {t("stories.readTime", { min: Math.max(1, Math.round(story.narrative.split(/\s+/).length / 220)) })}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2 lm-no-print">
            {!editing ? (
              <>
                <button onClick={() => window.print()} className="btn btn-ghost">
                  <FileDown className="h-4 w-4" />
                  <span>{t("stories.exportPdf")}</span>
                </button>
                <button onClick={() => setRegenOpen((v) => !v)} className="btn btn-ghost">
                  <Sparkles className="h-4 w-4" />
                  <span>{t("stories.regenerate")}</span>
                </button>
                <button
                  onClick={() => setEditing(true)}
                  className="btn btn-ghost"
                >
                  <Pencil className="h-4 w-4" />
                  <span>{t("storyReader.edit")}</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleCancel}
                  disabled={update.isPending}
                  className="btn btn-ghost"
                >
                  <X className="h-4 w-4" />
                  <span>{t("common.cancel")}</span>
                </button>
                <button
                  onClick={handleSave}
                  disabled={update.isPending || !dirty}
                  className="btn btn-primary"
                >
                  {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span>{t("common.save")}</span>
                </button>
              </>
            )}
          </div>
        </div>

        {editing ? (
          <input
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            className="input mt-3 font-serif text-3xl font-semibold leading-tight tracking-tight sm:text-4xl"
            placeholder={t("storyReader.titlePlaceholder")}
          />
        ) : (
          <h1 className="mt-3 font-serif text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            {story.title}
          </h1>
        )}
      </header>

      {regenOpen && !editing && (
        <div className="lm-no-print mb-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-4 dark:border-brand-900/40 dark:bg-brand-950/30">
          <p className="mb-1 font-medium">{t("stories.regenerateTitle")}</p>
          <p className="mb-3 text-xs text-stone-500 dark:text-stone-400">{t("stories.regenerateHint")}</p>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            className="input min-h-[80px] resize-y"
            placeholder={t("stories.regenerateHint")}
          />
          <div className="mt-3 flex justify-end gap-2">
            <button className="btn btn-ghost" onClick={() => setRegenOpen(false)} disabled={regen.isPending}>
              {t("common.cancel")}
            </button>
            <button className="btn btn-primary" onClick={handleRegenerate} disabled={regen.isPending}>
              {regen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              <span>{regen.isPending ? t("stories.regenerating") : t("stories.regenerate")}</span>
            </button>
          </div>
        </div>
      )}

      {editing ? (
        <>
          <textarea
            value={draftNarrative}
            onChange={(e) => setDraftNarrative(e.target.value)}
            className="input min-h-[60vh] resize-y font-serif text-lg leading-relaxed"
            placeholder={t("storyReader.narrativePlaceholder")}
          />
          <p className="mt-2 text-xs text-stone-500 dark:text-stone-500">
            {t("storyReader.editHint")}
            {dirty && <span className="ml-2 text-amber-600 dark:text-amber-400">· {t("storyReader.unsaved")}</span>}
          </p>
        </>
      ) : (
        <div className="prose-reader">
          {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      )}

      {!editing && (
        <div className="lm-no-print mt-10 border-t border-stone-200 pt-6 dark:border-stone-800">
          <button
            onClick={handleGenerateVideo}
            disabled={genVideo.isPending}
            className="btn btn-accent"
          >
            {genVideo.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Film className="h-4 w-4" />}
            <span>{t("videos.generate")}</span>
          </button>
        </div>
      )}
    </article>
  );
}
