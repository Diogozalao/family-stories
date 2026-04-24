import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Calendar } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useTimeline } from "../lib/hooks";
import { photoUrl } from "../lib/photo";
import type { TimelineEvent } from "../lib/types";

export default function TimelinePage() {
  const { t } = useTranslation();
  const { data, isLoading } = useTimeline();

  const grouped = useMemo(() => groupByYear(data ?? []), [data]);
  const years = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  return (
    <>
      <PageHeader title={t("timeline.title")} subtitle={t("timeline.subtitle")} />

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      ) : (data ?? []).length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          {t("timeline.empty")}
        </div>
      ) : (
        <div className="relative">
          <div aria-hidden className="absolute left-[11px] top-2 bottom-2 w-px bg-stone-200 dark:bg-stone-800 md:left-[91px]" />
          <div className="space-y-10">
            {years.map((y) => (
              <div key={y}>
                <div className="mb-4 flex items-center gap-3">
                  <span className="relative z-10 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-500 text-[11px] font-semibold text-white md:ml-[78px]">
                    •
                  </span>
                  <h3 className="font-serif text-2xl font-semibold tracking-tight">{y}</h3>
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
      )}
    </>
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
        <p className="mt-0.5 font-medium">{ev.title ?? t("timeline.undated")}</p>
        {ev.description && (
          <p className="mt-1 text-sm text-stone-600 line-clamp-3 dark:text-stone-400">
            {ev.description}
          </p>
        )}
        {ev.media_file_id && (
          <img
            src={photoUrl(ev.media_file_id)}
            alt=""
            loading="lazy"
            className="mt-3 max-h-48 rounded-lg border border-stone-200 object-cover dark:border-stone-800"
          />
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
