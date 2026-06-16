-- 0008_task_project.sql
-- Liga cada tarefa em segundo plano (task_records) ao projeto a que pertence,
-- para que as tarefas de um projeto não se misturem com as dos outros.
--
-- Correr no SQL Editor da Supabase. Idempotente.

ALTER TABLE task_records
    ADD COLUMN IF NOT EXISTS project_id BIGINT
        REFERENCES projects(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_task_records_project_id
    ON task_records (project_id);
