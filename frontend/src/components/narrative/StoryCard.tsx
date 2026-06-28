import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FolderKanban, Image as ImageIcon, Star, Trash2, Users } from "lucide-react";

import { useUpdateStory } from "../../lib/hooks";
import { cn } from "../../lib/utils";
import type { Story } from "../../lib/types";

/**
 * Story card shared by the global Stories page and the project Stories tab.
 *
 * ``projectName`` shows a chip linking back to the owning project (used on the
 * global page); inside a project it's omitted as redundant. ``onDelete``, when
 * given, renders the delete affordance — so both places can remove stories.
 */
export default function StoryCard({
  story, projectId = null, projectName = null, onDelete,
}: {
  story: Story;
  projectId?: number | null;
  projectName?: string | null;
  onDelete?: () => void;
}) {
  const { t } = useTranslation();
  const update = useUpdateStory();
  const fav = !!story.favorite;

  return (
    <article className="card group relative flex flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-lift">
      <div className="absolute right-3 top-3 flex items-center gap-1">
        <button
          onClick={() => update.mutate({ id: story.id, favorite: !fav })}
          className={cn(
            "rounded-lg p-1.5 transition hover:bg-stone-100 dark:hover:bg-stone-800",
            fav ? "text-amber-500" : "text-stone-400 opacity-0 group-hover:opacity-100",
          )}
          aria-label={t("stories.favorite")}
          title={t("stories.favorite")}
        >
          <Star className="h-4 w-4" fill={fav ? "currentColor" : "none"} />
        </button>
        {onDelete && (
          <button
            onClick={onDelete}
            className="rounded-lg p-1.5 text-stone-400 opacity-0 transition hover:bg-stone-100 hover:text-rose-600 group-hover:opacity-100 dark:hover:bg-stone-800"
            aria-label={t("common.delete")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="chip chip-accent">{story.event_type}</span>
        {projectId != null && projectName && (
          <Link
            to={`/projects/${projectId}`}
            className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 font-medium text-stone-700 transition hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
          >
            <FolderKanban className="h-3 w-3" />
            {projectName}
          </Link>
        )}
        <span className="text-stone-500 dark:text-stone-500">
          {new Date(story.created_at).toLocaleDateString()}
        </span>
      </div>
      <h3 className="mt-3 font-serif text-xl font-semibold leading-snug tracking-tight line-clamp-2">
        {story.title}
      </h3>
      <p className="mt-2 flex-1 text-sm text-stone-600 line-clamp-4 dark:text-stone-400">
        {(story.narrative ?? "").slice(0, 220)}…
      </p>
      <div className="mt-4 flex items-center justify-between border-t border-stone-100 pt-3 dark:border-stone-800">
        <span className="flex items-center gap-3 text-xs text-stone-500 dark:text-stone-500">
          <span className="inline-flex items-center gap-1" title={t("stories.photosUsed")}>
            <ImageIcon className="h-3.5 w-3.5" /> {story.media_ids?.length ?? 0}
          </span>
          <span className="inline-flex items-center gap-1" title={t("stories.peopleUsed")}>
            <Users className="h-3.5 w-3.5" /> {story.person_ids?.length ?? 0}
          </span>
        </span>
        <Link to={`/stories/${story.id}`} className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
          {t("common.open")} →
        </Link>
      </div>
    </article>
  );
}
