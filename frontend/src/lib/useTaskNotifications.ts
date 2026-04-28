import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useTasks } from "./hooks";
import type { TaskState } from "./types";

/**
 * Watches the global task list and surfaces a toast every time a task
 * transitions from active (``pending``/``running``) to a terminal state
 * (``done``/``failed``). Prevents the user from having to keep
 * ``/tasks`` open to know if their generation finished.
 */
export function useTaskNotifications(): void {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data } = useTasks();
  const seenRef = useRef<Map<number, TaskState>>(new Map());
  const bootRef = useRef(true);

  useEffect(() => {
    if (!data) return;

    // First poll after mount: just record current states without toasting.
    // Otherwise the user gets spammed with notifications for tasks that
    // already finished long before they opened the app.
    if (bootRef.current) {
      for (const task of data) seenRef.current.set(task.id, task.state);
      bootRef.current = false;
      return;
    }

    for (const task of data) {
      const previous = seenRef.current.get(task.id);
      seenRef.current.set(task.id, task.state);

      const finishedNow =
        previous &&
        previous !== task.state &&
        (task.state === "done" || task.state === "failed");
      if (!finishedNow) continue;

      const label = t(`tasks.kind.${task.kind}`);

      if (task.state === "done") {
        toast.success(`${label} concluída`, {
          description: typeof task.payload?.title === "string"
            ? (task.payload.title as string)
            : `Tarefa #${task.id}`,
          action: task.story_id
            ? { label: "Abrir", onClick: () => navigate(`/stories/${task.story_id}`) }
            : task.video_id
              ? { label: "Abrir", onClick: () => navigate("/videos") }
              : undefined,
        });
      } else {
        toast.error(`${label} falhou`, {
          description: task.error ?? `Tarefa #${task.id}`,
        });
      }
    }
  }, [data, t, navigate]);
}
