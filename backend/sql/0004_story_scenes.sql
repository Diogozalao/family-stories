-- =============================================================
-- Migration 0004 — Story scenes (scene-based narrative)
-- =============================================================
-- Stores the structured, scene-segmented form of a narrative so M4 can
-- synchronise each photo with the exact stretch of narration that talks
-- about it. Each element of the JSON array is:
--   { "text": "<prose>", "photo_ids": [<media id>, ...], "caption": "<date . place>" }
--
-- Nullable on purpose: stories generated before this migration keep
-- ``scenes = NULL`` and M4 falls back to the legacy even-split slideshow.
-- =============================================================

ALTER TABLE stories
    ADD COLUMN IF NOT EXISTS scenes JSONB;
