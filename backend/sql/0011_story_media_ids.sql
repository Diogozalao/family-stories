-- ── Story photo selection ──────────────────────────────────────────────────
-- Remember WHICH photos each narrative was built from (the selection the user
-- made in the generation wizard). The video pipeline (M4) reads this and builds
-- the documentary from ONLY these photos, so the video shows the same photos as
-- the story — instead of every photo in the library/project.
--
-- Legacy stories have NULL here; M4 falls back to every photo in the story's
-- scope (project or global), matching the previous behaviour.

ALTER TABLE stories ADD COLUMN IF NOT EXISTS media_ids JSONB;
