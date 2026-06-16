-- =============================================================
-- Migration 0006 — Saved tree node positions
-- =============================================================
-- Persists the x/y a user dragged each person to in the interactive tree,
-- so the layout they arranged by hand survives reloads. NULL means "use
-- the automatic layout" for that person.
-- =============================================================

ALTER TABLE persons ADD COLUMN IF NOT EXISTS tree_x DOUBLE PRECISION;
ALTER TABLE persons ADD COLUMN IF NOT EXISTS tree_y DOUBLE PRECISION;
