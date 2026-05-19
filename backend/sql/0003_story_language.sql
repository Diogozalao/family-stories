-- =============================================================
-- Migration 0003 — Story language tag
-- =============================================================
-- Captures the language each ``Story`` was written in so M4's TTS
-- can pick the correct voice — even if the user later flips the UI
-- toggle. Two-letter code (``pt``, ``en``) matching the frontend
-- ``i18n.language``.
-- =============================================================

ALTER TABLE stories
    ADD COLUMN IF NOT EXISTS language VARCHAR(8) NOT NULL DEFAULT 'pt';
