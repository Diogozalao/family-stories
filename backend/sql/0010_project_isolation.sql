-- ── Project isolation ──────────────────────────────────────────────────────
-- A photo, person or timeline event can belong to ONE project (project_id set)
-- or to the global Library / Family / Timeline (project_id NULL). Global views
-- filter ``project_id IS NULL``; a project's views filter ``project_id = <id>``.
-- This makes projects self-contained areas: what you upload inside a project
-- never shows up in the global Library/Home/Timeline, and vice-versa.
--
-- The column is the source of truth going forward. The old ``project_media``
-- link table stays (so previously-shared photos aren't lost) but new uploads
-- use ``project_id``.

ALTER TABLE media_files     ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE persons         ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_media_files_project     ON media_files(project_id);
CREATE INDEX IF NOT EXISTS ix_persons_project         ON persons(project_id);
CREATE INDEX IF NOT EXISTS ix_timeline_events_project ON timeline_events(project_id);
