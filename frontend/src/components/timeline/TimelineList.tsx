import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Calendar, MapPin, Users } from "lucide-react";

import Photo from "../media/Photo";
import type { TimelineEvent } from "../../lib/types";

/**
 * Year-grouped timeline rendering, shared by the global Timeline page and the
 * project Timeline tab so both look and behave identically. Callers just pass
 * the events (the global page builds them from DB ``TimelineEvent``s; a
 * project builds them from its own photos) — the layout lives here once.
 */
const UNDATED = "—";

export default function TimelineList({ events }: { events: TimelineEvent[] }) {
  const { t } = useTranslation();
  const grouped = useMemo(() => groupByYear(events), [events]);
  // Most recent year first; the undated bucket always sinks to the bottom.
  const years = Object.keys(grouped).sort((a, b) => {
    if (a === UNDATED) return 1;
    if (b === UNDATED) return -1;
    return b.localeCompare(a);
  });

  return (
    <div className="relative">
      <div aria-hidden className="absolute left-[11px] top-2 bottom-2 w-px bg-stone-200 dark:bg-stone-800 md:left-[91px]" />
      <div className="space-y-10">
        {years.map((y) => (
          <div key={y}>
            <div className="mb-4 flex items-center gap-3">
              <span className="relative z-10 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-500 text-[11px] font-semibold text-white md:ml-[78px]">
                •
              </span>
              <h3 className="font-serif text-2xl font-semibold tracking-tight">
                {y === UNDATED ? t("timeline.undated") : y}
              </h3>
              <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-500 dark:bg-stone-800 dark:text-stone-400">
                {grouped[y].length}
              </span>
            </div>
            <div className="space-y-3">
              {grouped[y].map((ev) => (
                <EventRow key={ev.id} ev={ev} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EventRow({ ev }: { ev: TimelineEvent }) {
  const { t } = useTranslation();
  const d = ev.event_date ? new Date(ev.event_date) : null;
  const dateLabel = d
    ? d.toLocaleDateString(undefined, { day: "2-digit", month: "short" })
    : t("timeline.undated");

  return (
    <div className="flex gap-4 md:gap-6">
      <div className="hidden md:block w-20 pt-4 text-right text-xs font-medium text-stone-500 dark:text-stone-500">
        {dateLabel}
      </div>
      <div className="relative flex pt-3 md:pt-4">
        <span className="mt-1.5 inline-flex h-2.5 w-2.5 rounded-full border-2 border-white bg-brand-400 shadow-soft dark:border-stone-950" />
      </div>
      <div className="flex-1 card-soft p-4">
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-500 md:hidden">
          <Calendar className="h-3.5 w-3.5" />
          <span>{dateLabel}</span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {ev.type && <span className="chip chip-accent capitalize">{ev.type}</span>}
          {ev.family && (
            <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-600 dark:bg-stone-800 dark:text-stone-300">
              <Users className="h-3 w-3" /> {ev.family}
            </span>
          )}
        </div>

        <p className="mt-1.5 font-medium">{ev.title ?? t("timeline.undated")}</p>

        {ev.people && ev.people.length > 0 && (
          <p className="mt-0.5 text-sm text-stone-600 dark:text-stone-400">
            <span className="text-stone-400">{t("timeline.who")} </span>
            {ev.people.join(", ")}
          </p>
        )}
        {ev.location && (
          <p className="mt-0.5 flex items-center gap-1 text-xs text-stone-500 dark:text-stone-500">
            <MapPin className="h-3 w-3" /> {ev.location}
          </p>
        )}
        {ev.description && (
          <p className="mt-1.5 text-sm text-stone-600 line-clamp-3 dark:text-stone-400">
            {ev.description}
          </p>
        )}
        {ev.media_file_id && (
          <div className="relative mt-3 h-32 w-44 overflow-hidden rounded-lg border border-stone-200 dark:border-stone-800">
            <Photo mediaId={ev.media_file_id} className="h-full w-full object-cover" />
          </div>
        )}
      </div>
    </div>
  );
}

function groupByYear(events: TimelineEvent[]): Record<string, TimelineEvent[]> {
  const out: Record<string, TimelineEvent[]> = {};
  for (const ev of events) {
    const y = ev.event_date ? new Date(ev.event_date).getFullYear().toString() : "—";
    (out[y] ??= []).push(ev);
  }
  for (const y of Object.keys(out)) {
    out[y].sort((a, b) => {
      const da = a.event_date ? +new Date(a.event_date) : 0;
      const db = b.event_date ? +new Date(b.event_date) : 0;
      return db - da;
    });
  }
  return out;
}
