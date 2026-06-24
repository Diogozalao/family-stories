import { useTranslation } from "react-i18next";
import { Check, Images } from "lucide-react";

import Photo from "../media/Photo";
import { useGenerateDraft } from "../../store/generateDraft";
import { cn } from "../../lib/utils";
import type { MediaFile, Person } from "../../lib/types";

/**
 * Photo picker for the generation wizard. When people are selected the photos
 * are grouped by person (the photos they're tagged in) so you choose exactly
 * which of each person's photos go into the story/video; otherwise a flat
 * grid. Reads/writes the selection straight from the persisted draft store, so
 * the parent doesn't have to drill any props.
 */
export default function PhotoSelector({
  photos, selectedPeople,
}: { photos: MediaFile[]; selectedPeople: Person[] }) {
  const { t } = useTranslation();
  const { selectedMediaIds, patch } = useGenerateDraft();

  const toggle = (id: number) =>
    patch({
      selectedMediaIds: selectedMediaIds.includes(id)
        ? selectedMediaIds.filter((x) => x !== id)
        : [...selectedMediaIds, id],
    });
  const toggleMany = (ids: number[], on: boolean) => {
    const set = new Set(selectedMediaIds);
    for (const id of ids) { if (on) set.add(id); else set.delete(id); }
    patch({ selectedMediaIds: [...set] });
  };

  const groups = selectedPeople.map((p) => ({
    person: p,
    photos: photos.filter((m) => (m.person_ids ?? []).includes(p.id)),
  }));
  const grouped = new Set(groups.flatMap((g) => g.photos.map((m) => m.id)));
  const others = photos.filter((m) => !grouped.has(m.id));

  return (
    <div className="mt-8 border-t border-stone-100 pt-6 dark:border-stone-800">
      <h3 className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
        <Images className="h-4 w-4" /> {t("generate.selectPhotos")}
        {selectedMediaIds.length > 0 && (
          <span className="text-sm font-normal text-brand-600 dark:text-brand-400">· {selectedMediaIds.length}</span>
        )}
      </h3>
      <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t("generate.selectPhotosHint")}</p>

      {photos.length === 0 ? (
        <p className="mt-4 text-sm text-stone-500">{t("generate.noPhotos")}</p>
      ) : selectedPeople.length === 0 ? (
        <div className="mt-4"><Grid photos={photos} selected={selectedMediaIds} onToggle={toggle} /></div>
      ) : (
        <div className="mt-4 space-y-5">
          {groups.map((g) => {
            const ids = g.photos.map((m) => m.id);
            const allOn = ids.length > 0 && ids.every((id) => selectedMediaIds.includes(id));
            return (
              <div key={g.person.id}>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">
                    {g.person.name}
                    <span className="ml-1 text-stone-500 dark:text-stone-500">· {g.photos.length}</span>
                  </p>
                  {ids.length > 0 && (
                    <button type="button" onClick={() => toggleMany(ids, !allOn)}
                            className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
                      {allOn ? t("generate.deselectAll") : t("generate.selectAll")}
                    </button>
                  )}
                </div>
                {g.photos.length === 0
                  ? <p className="text-xs text-stone-500">{t("generate.personNoPhotos")}</p>
                  : <Grid photos={g.photos} selected={selectedMediaIds} onToggle={toggle} />}
              </div>
            );
          })}
          {others.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium">
                {t("generate.otherPhotos")}
                <span className="ml-1 text-stone-500 dark:text-stone-500">· {others.length}</span>
              </p>
              <Grid photos={others} selected={selectedMediaIds} onToggle={toggle} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Grid({
  photos, selected, onToggle,
}: { photos: MediaFile[]; selected: number[]; onToggle: (id: number) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
      {photos.map((m) => {
        const active = selected.includes(m.id);
        return (
          <button
            key={m.id}
            type="button"
            onClick={() => onToggle(m.id)}
            className={cn(
              "group relative aspect-square overflow-hidden rounded-lg border-2 transition",
              active
                ? "border-brand-500 ring-2 ring-brand-200 dark:ring-brand-900/40"
                : "border-transparent hover:border-stone-300 dark:hover:border-stone-700",
            )}
            title={m.ai_description || m.original_filename}
          >
            <Photo mediaId={m.id} alt={m.original_filename} className="h-full w-full object-cover" />
            {active && (
              <span className="absolute right-1 top-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white shadow">
                <Check className="h-3 w-3" />
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
