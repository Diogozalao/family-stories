-- =============================================================
-- Migration 0007 — People tagged in a photo
-- =============================================================
-- Links each photo to the persons that appear in it, so the narrative
-- (M3) and the video captions (M4) can say WHO is in each image — the
-- bridge between the family tree and the storytelling.
--
-- Stored as a JSON array of person ids (mirrors stories.person_ids and
-- timeline_events.person_ids). Stale ids (after a person is deleted) are
-- simply ignored when read.
-- =============================================================

ALTER TABLE media_files ADD COLUMN IF NOT EXISTS person_ids JSONB DEFAULT '[]'::jsonb;
UPDATE media_files SET person_ids = '[]'::jsonb WHERE person_ids IS NULL;
