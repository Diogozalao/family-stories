import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, ChevronLeft, ChevronRight, Loader2, Search, X } from "lucide-react";

import { photoUrl } from "../../lib/photo";
import { extractErrorMessage } from "../../lib/api";
import {
  useBuildTimeline, usePersons, useSetMediaPersons, useUpdateMedia,
} from "../../lib/hooks";
import { cn } from "../../lib/utils";
import type { MediaFile } from "../../lib/types";

/**
 * Full-screen photo viewer + editor, shared by the Library and the Project
 * photos tab so both have the *same* detail experience: large image on one
 * side, a readable panel on the other to set the date and tag who appears in
 * the photo. The people list wraps and is searchable, so names are easy to
 * read and select even with a big family.
 */
export default function PhotoViewer({
  items, index, onChange, onClose, projectId = null,
}: {
  items: MediaFile[];
  index: number;
  onChange: (i: number) => void;
  onClose: () => void;
  /** When set (inside a project), only this project's people are taggable. */
  projectId?: number | null;
}) {
  const { t } = useTranslation();
  const cur = items[index];
  const prev = () => onChange((index - 1 + items.length) % items.length);
  const next = () => onChange((index + 1) % items.length);

  const updateMedia   = useUpdateMedia();
  const buildTimeline = useBuildTimeline();
  const [dateInput, setDateInput] = useState<string>(cur.date_taken?.slice(0, 10) ?? "");
  useEffect(() => { setDateInput(cur.date_taken?.slice(0, 10) ?? ""); }, [cur.id, cur.date_taken]);

  const saveDate = async () => {
    try {
      await updateMedia.mutateAsync({ id: cur.id, date_taken: dateInput || "" });
      await buildTimeline.mutateAsync().catch(() => {});
      toast.success(t("common.success"));
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };
  const dateChanged = (cur.date_taken?.slice(0, 10) ?? "") !== dateInput;

  // Tag which family members appear in this photo. Scoped to the project's
  // people when ``projectId`` is set, so a project never lists everyone.
  const { data: persons } = usePersons(projectId);
  const setPersons = useSetMediaPersons();
  const [tagged, setTagged] = useState<number[]>(cur.person_ids ?? []);
  useEffect(() => { setTagged(cur.person_ids ?? []); }, [cur.id, cur.person_ids]);
  const [peopleQuery, setPeopleQuery] = useState("");

  const togglePerson = (pid: number) => {
    const updated = tagged.includes(pid) ? tagged.filter((x) => x !== pid) : [...tagged, pid];
    setTagged(updated);
    setPersons.mutate(
      { id: cur.id, person_ids: updated },
      { onError: (err) => toast.error(extractErrorMessage(err)) },
    );
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  const q = peopleQuery.trim().toLowerCase();
  const allPeople = persons ?? [];
  // Tagged first, then filtered by the search box — easy to scan and select.
  const visiblePeople = allPeople
    .filter((p) => !q || p.name.toLowerCase().includes(q))
    .sort((a, b) => Number(tagged.includes(b.id)) - Number(tagged.includes(a.id)));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/90 p-3 backdrop-blur animate-fade-in sm:p-6">
      <button
        onClick={onClose}
        className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        aria-label={t("common.close")}
      >
        <X className="h-5 w-5" />
      </button>

      <div className="flex h-full max-h-[92vh] w-full max-w-6xl flex-col gap-4 lg:flex-row">
        {/* ── Image ─────────────────────────────────────────── */}
        <div className="relative flex min-h-0 flex-1 items-center justify-center">
          {items.length > 1 && (
            <>
              <button
                onClick={prev}
                className="absolute left-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/10 p-2.5 text-white hover:bg-white/20"
                aria-label="Previous"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                onClick={next}
                className="absolute right-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/10 p-2.5 text-white hover:bg-white/20"
                aria-label="Next"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </>
          )}
          <img
            src={photoUrl(cur.id)}
            alt={cur.original_filename}
            className="max-h-[50vh] max-w-full rounded-xl object-contain animate-scale-in lg:max-h-[88vh]"
          />
        </div>

        {/* ── Detail / editor panel ─────────────────────────── */}
        <aside className="flex w-full shrink-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-stone-900/80 lg:w-96">
          <div className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
            <p className="min-w-0 truncate text-sm font-medium text-white/95">{cur.original_filename}</p>
            <span className="shrink-0 rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-white/70">
              {index + 1} / {items.length}
            </span>
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-white/85">
            {(cur.date_taken || cur.ai_setting) && (
              <div className="text-xs text-white/60">
                {cur.date_taken && <span>{new Date(cur.date_taken).toLocaleString()}</span>}
                {cur.ai_setting && <span>{cur.date_taken ? " · " : ""}{cur.ai_setting}</span>}
              </div>
            )}

            {cur.ai_description && (
              <p className="text-[13px] leading-relaxed text-white/75">{cur.ai_description}</p>
            )}

            {/* Date editor */}
            <div>
              <label className="mb-1 block text-[11px] uppercase tracking-wider text-white/50">
                {t("library.dateLabel")}
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={dateInput}
                  onChange={(e) => setDateInput(e.target.value)}
                  onKeyDown={(e) => e.stopPropagation()}
                  className="flex-1 rounded-md border border-white/20 bg-white/10 px-2 py-1.5 text-sm text-white [color-scheme:dark]"
                />
                {dateChanged && (
                  <button
                    onClick={saveDate}
                    disabled={updateMedia.isPending || buildTimeline.isPending}
                    className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-60"
                  >
                    {(updateMedia.isPending || buildTimeline.isPending) && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    {t("library.saveDate")}
                  </button>
                )}
              </div>
            </div>

            {/* People tagging */}
            <div>
              <p className="mb-1.5 text-[11px] uppercase tracking-wider text-white/50">
                {t("library.peopleInPhoto")}
                {tagged.length > 0 && <span className="ml-1 text-brand-300">· {tagged.length}</span>}
              </p>
              {allPeople.length === 0 ? (
                <p className="text-xs text-white/50">{t("family.noTree")}</p>
              ) : (
                <>
                  <div className="relative mb-2">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-white/40" />
                    <input
                      value={peopleQuery}
                      onChange={(e) => setPeopleQuery(e.target.value)}
                      onKeyDown={(e) => e.stopPropagation()}
                      placeholder={t("common.search")}
                      className="w-full rounded-md border border-white/15 bg-white/5 py-1.5 pl-8 pr-2 text-sm text-white placeholder:text-white/40"
                    />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {visiblePeople.map((p) => {
                      const on = tagged.includes(p.id);
                      return (
                        <button
                          key={p.id}
                          onClick={() => togglePerson(p.id)}
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[13px] transition",
                            on
                              ? "border-brand-400 bg-brand-500/30 text-white"
                              : "border-white/20 bg-white/5 text-white/70 hover:bg-white/10",
                          )}
                        >
                          {on && <Check className="h-3 w-3" />}
                          {p.name}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
