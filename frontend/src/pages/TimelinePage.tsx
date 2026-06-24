import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Loader2, RefreshCw } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import TimelineList from "../components/timeline/TimelineList";
import { useBuildTimeline, useTimeline } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";

export default function TimelinePage() {
  const { t } = useTranslation();
  const { data, isLoading } = useTimeline();
  const build = useBuildTimeline();

  const rebuild = () => build.mutate(undefined, {
    onSuccess: (r: { total_events?: number }) => toast.success(
      (r?.total_events ?? 0) > 0
        ? `Linha temporal atualizada: ${r.total_events} evento(s).`
        : "Ainda sem eventos — as fotos não estão analisadas. Usa 'Re-analisar IA' na Biblioteca primeiro.",
    ),
    onError: (err) => toast.error(extractErrorMessage(err)),
  });

  return (
    <>
      <PageHeader
        title={t("timeline.title")}
        subtitle={t("timeline.subtitle")}
        actions={
          <button className="btn btn-ghost" onClick={rebuild} disabled={build.isPending}>
            {build.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span>Atualizar</span>
          </button>
        }
      />

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
        <TimelineList events={data ?? []} />
      )}
    </>
  );
}
