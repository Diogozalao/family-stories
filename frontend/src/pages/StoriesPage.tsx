import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { BookOpen, Sparkles } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import StoryCard from "../components/narrative/StoryCard";
import { useDeleteStory, useProjects, useStories } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import type { Story } from "../lib/types";

export default function StoriesPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useStories();
  const { data: projects } = useProjects();
  const del = useDeleteStory();

  const stories = data ?? [];
  // Map project id -> project so each story card can show which project it
  // belongs to (the "organisation" the user was missing).
  const projectById = new Map((projects ?? []).map((p) => [p.id, p]));

  const handleDelete = (s: Story) => {
    if (!window.confirm(`${t("common.confirm")}?`)) return;
    del.mutate(s.id, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <>
      <PageHeader
        title={t("stories.title")}
        subtitle={t("stories.subtitle")}
        actions={
          <Link to="/generate" className="btn btn-accent">
            <Sparkles className="h-4 w-4" />
            <span>{t("stories.newStory")}</span>
          </Link>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-40 rounded-2xl" />
          ))}
        </div>
      ) : stories.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          <BookOpen className="mx-auto mb-3 h-8 w-8 text-stone-400" />
          {t("stories.empty")}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stories.map((s) => (
            <StoryCard
              key={s.id}
              story={s}
              projectId={s.project_id ?? null}
              projectName={s.project_id != null ? projectById.get(s.project_id)?.name ?? null : null}
              onDelete={() => handleDelete(s)}
            />
          ))}
        </div>
      )}
    </>
  );
}
