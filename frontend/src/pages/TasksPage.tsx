import { useTranslation } from "react-i18next";
import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useTasks } from "../lib/hooks";
import type { TaskRecord, TaskState } from "../lib/types";

export default function TasksPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useTasks();
  const tasks = data ?? [];

  return (
    <>
      <PageHeader title={t("tasks.title")} subtitle={t("tasks.subtitle")} />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-2xl" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          {t("tasks.empty")}
        </div>
      ) : (
        <ul className="space-y-3">
          {tasks.map((task) => <TaskRow key={task.id} task={task} />)}
        </ul>
      )}
    </>
  );
}

function TaskRow({ task }: { task: TaskRecord }) {
  const { t } = useTranslation();
  return (
    <li className="card-soft flex items-start gap-4 p-4">
      <StateIcon state={task.state} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{t(`tasks.kind.${task.kind}`)}</p>
          <span className="chip">#{task.id}</span>
          <StateChip state={task.state} />
        </div>
        <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-500">
          {new Date(task.created_at).toLocaleString()}
        </p>
        {task.error && (
          <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{task.error}</p>
        )}
      </div>
    </li>
  );
}

function StateIcon({ state }: { state: TaskState }) {
  const box = "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg";
  if (state === "done") return <span className={`${box} bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300`}><CheckCircle2 className="h-4 w-4" /></span>;
  if (state === "failed") return <span className={`${box} bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300`}><XCircle className="h-4 w-4" /></span>;
  if (state === "running") return <span className={`${box} bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300`}><Loader2 className="h-4 w-4 animate-spin" /></span>;
  return <span className={`${box} bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300`}><Clock className="h-4 w-4" /></span>;
}

function StateChip({ state }: { state: TaskState }) {
  const { t } = useTranslation();
  const label = t(`tasks.state.${state}`);
  const map: Record<TaskState, string> = {
    pending: "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
    running: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
    done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    failed: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${map[state]}`}>{label}</span>;
}
