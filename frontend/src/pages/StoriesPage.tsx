import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { BookOpen, Search, Sparkles } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import StoryCard from "../components/narrative/StoryCard";
import { useDeleteStory, useProjects, useStories } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import type { Story } from "../lib/types";

type Sort = "recent" | "oldest" | "title";

export default function StoriesPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useStories();
  const { data: projects } = useProjects();
  const del = useDeleteStory();

  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("recent");
  const [projectFilter, setProjectFilter] = useState<number | "all">("all");

  const projectById = new Map((projects ?? []).map((p) => [p.id, p]));

  // Filter (search + project) then sort — favourites always float to the top.
  const stories = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = (data ?? []).filter((s) =>
      (projectFilter === "all" || s.project_id === projectFilter) &&
      (!q || s.title.toLowerCase().includes(q) || (s.narrative ?? "").toLowerCase().includes(q)),
    );
    return [...list].sort((a, b) => {
      if (!!a.favorite !== !!b.favorite) return a.favorite ? -1 : 1;
      if (sort === "title") return a.title.localeCompare(b.title);
      const da = +new Date(a.created_at), db = +new Date(b.created_at);
      return sort === "oldest" ? da - db : db - da;
    });
  }, [data, query, sort, projectFilter]);

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

      {!isLoading && (data ?? []).length > 0 && (
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("stories.search")}
              className="input pl-9"
            />
          </div>
          <select className="input w-auto" value={String(projectFilter)}
                  onChange={(e) => setProjectFilter(e.target.value === "all" ? "all" : Number(e.target.value))}>
            <option value="all">{t("stories.allProjects")}</option>
            {(projects ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className="input w-auto" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            <option value="recent">{t("stories.sortRecent")}</option>
            <option value="oldest">{t("stories.sortOldest")}</option>
            <option value="title">{t("stories.sortTitle")}</option>
          </select>
        </div>
      )}

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
