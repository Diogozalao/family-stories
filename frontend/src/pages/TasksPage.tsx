import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  CheckCircle2, Clock, Eraser, ExternalLink, Loader2, Trash2, X, XCircle,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import {
  useCancelTask, useClearFinishedTasks, useDeleteTask, useTasks,
} from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import type { TaskRecord, TaskState } from "../lib/types";

export default function TasksPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useTasks();
  const clearFinished = useClearFinishedTasks();
  const tasks = data ?? [];

  const finishedCount = tasks.filter((x) => x.state === "done" || x.state === "failed").length;

  const handleClearFinished = () => {
    if (!finishedCount) return;
    if (!window.confirm(`Apagar ${finishedCount} tarefa(s) concluídas/falhadas do histórico?`)) return;
    clearFinished.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <>
      <PageHeader
        title={t("tasks.title")}
        subtitle={t("tasks.subtitle")}
        actions={
          finishedCount > 0 ? (
            <button onClick={handleClearFinished} className="btn btn-outline" disabled={clearFinished.isPending}>
              {clearFinished.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eraser className="h-4 w-4" />}
              <span>Limpar histórico ({finishedCount})</span>
            </button>
          ) : null
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
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
  const cancel = useCancelTask();
  const del = useDeleteTask();

  const active = task.state === "pending" || task.state === "running";
  const payload = task.payload as Record<string, unknown> | null;
  const title = typeof payload?.title === "string" ? payload.title : null;
  const eventType = typeof payload?.event_type === "string" ? payload.event_type : null;
  const query = typeof payload?.query === "string" ? payload.query : null;

  const resultStoryId =
    typeof (task.result as { story_id?: unknown } | null)?.story_id === "number"
      ? (task.result as { story_id: number }).story_id
      : task.story_id;
  const resultVideoId =
    typeof (task.result as { video_id?: unknown } | null)?.video_id === "number"
      ? (task.result as { video_id: number }).video_id
      : task.video_id;

  const handleCancel = () => {
    if (!window.confirm("Cancelar esta tarefa em curso?")) return;
    cancel.mutate(task.id, {
      onSuccess: () => toast.success("Tarefa cancelada"),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };
  const handleDelete = () => {
    const msg = active
      ? "Esta tarefa ainda está ativa. Apagar (e cancelar)?"
      : "Apagar esta entrada do histórico?";
    if (!window.confirm(msg)) return;
    del.mutate(task.id, {
      onSuccess: () => toast.success("Apagado"),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <li className="card-soft p-4">
      <div className="flex items-start gap-4">
        <StateIcon state={task.state} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium">{t(`tasks.kind.${task.kind}`)}</p>
            <span className="chip">#{task.id}</span>
            <StateChip state={task.state} />
            {eventType && <span className="chip chip-accent">{eventType}</span>}
          </div>

          {title && (
            <p className="mt-1.5 truncate font-serif text-base text-stone-800 dark:text-stone-200">
              {title}
            </p>
          )}
          {query && (
            <p className="mt-1 text-xs text-stone-600 line-clamp-2 dark:text-stone-400">
              <span className="text-stone-400">"</span>{query}<span className="text-stone-400">"</span>
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-stone-500 dark:text-stone-500">
            <span>{new Date(task.created_at).toLocaleString()}</span>
            {task.updated_at && task.updated_at !== task.created_at && (
              <span>· atualizado {new Date(task.updated_at).toLocaleString()}</span>
            )}
            {task.celery_id && (
              <span className="font-mono">· {task.celery_id.slice(0, 8)}</span>
            )}
          </div>

          {task.state === "done" && (resultStoryId || resultVideoId) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {resultStoryId && (
                <Link
                  to={`/stories/${resultStoryId}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand-100 px-2.5 py-1 text-xs font-medium text-brand-800 hover:bg-brand-200 dark:bg-brand-400/15 dark:text-brand-300 dark:hover:bg-brand-400/25"
                >
                  <ExternalLink className="h-3 w-3" />
                  Abrir história
                </Link>
              )}
              {resultVideoId && (
                <Link
                  to="/videos"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-800 hover:bg-sky-200 dark:bg-sky-400/15 dark:text-sky-300 dark:hover:bg-sky-400/25"
                >
                  <ExternalLink className="h-3 w-3" />
                  Abrir vídeo
                </Link>
              )}
            </div>
          )}

          {task.error && (
            <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-950/30 dark:text-rose-300">
              {task.error}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {active && (
            <button
              onClick={handleCancel}
              disabled={cancel.isPending}
              className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-rose-600 dark:hover:bg-stone-800"
              title="Cancelar tarefa"
              aria-label="Cancelar"
            >
              {cancel.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
            </button>
          )}
          <button
            onClick={handleDelete}
            disabled={del.isPending}
            className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-rose-600 dark:hover:bg-stone-800"
            title="Apagar do histórico"
            aria-label="Apagar"
          >
            {del.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </li>
  );
}

function StateIcon({ state }: { state: TaskState }) {
  const box = "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg";
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
