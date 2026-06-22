import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { BookOpen, FolderKanban, Sparkles, Trash2 } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
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
            <article key={s.id} className="card group relative flex flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-lift">
              <button
                onClick={() => handleDelete(s)}
                className="absolute right-3 top-3 rounded-lg p-1.5 text-stone-400 opacity-0 transition hover:bg-stone-100 hover:text-rose-600 group-hover:opacity-100 dark:hover:bg-stone-800"
                aria-label={t("common.delete")}
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="chip chip-accent">{s.event_type}</span>
                {s.project_id != null && projectById.get(s.project_id) && (
                  <Link
                    to={`/projects/${s.project_id}`}
                    className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 font-medium text-stone-700 transition hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
                  >
                    <FolderKanban className="h-3 w-3" />
                    {projectById.get(s.project_id)!.name}
                  </Link>
                )}
                <span className="text-stone-500 dark:text-stone-500">
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
              </div>
              <h3 className="mt-3 font-serif text-xl font-semibold leading-snug tracking-tight line-clamp-2">
                {s.title}
              </h3>
              <p className="mt-2 flex-1 text-sm text-stone-600 line-clamp-4 dark:text-stone-400">
                {(s.narrative ?? "").slice(0, 220)}…
              </p>
              <div className="mt-4 flex items-center justify-between border-t border-stone-100 pt-3 dark:border-stone-800">
                <span className="text-xs text-stone-500 dark:text-stone-500">
                  {s.facts_used ? `${s.facts_used} factos usados` : ""}
                </span>
                <Link to={`/stories/${s.id}`} className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
                  {t("common.open")} →
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
