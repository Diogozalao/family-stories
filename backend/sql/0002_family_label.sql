-- =============================================================
-- Migration 0002 — Family labels on persons
-- =============================================================
-- Adds an optional ``family_label`` column to ``persons`` so a single
-- account can host multiple distinct family trees side-by-side
-- ("Dinis", "Nogueira", …) without merging them into one ambiguous
-- soup. The label is set once at GEDCOM import time and rendered as a
-- group/filter in the Family page.
--
-- Run idempotently with ALTER TABLE IF NOT EXISTS guards.
-- =============================================================

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS family_label VARCHAR(120);

-- Index for the by-label filter in the UI. ``user_id`` is the high-
-- selectivity column so it leads.
CREATE INDEX IF NOT EXISTS idx_persons_user_family
    ON persons (user_id, family_label);
