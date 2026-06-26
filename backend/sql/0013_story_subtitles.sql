-- ── Documentary subtitles toggle ────────────────────────────────────────────
-- Remember whether the user wants narration subtitles burned into the video.
-- The video pipeline (M4) reads this: TRUE/NULL → subtitles on (default),
-- FALSE → a clean video with no on-screen text. Existing stories keep the
-- previous behaviour (subtitles on).

ALTER TABLE stories ADD COLUMN IF NOT EXISTS subtitles BOOLEAN DEFAULT TRUE;
