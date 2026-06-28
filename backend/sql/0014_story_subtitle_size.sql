-- ── Subtitle size preference ────────────────────────────────────────────────
-- Remember the subtitle size the user picked for the documentary's caption
-- track ("small" / "medium" / "large"). The web player applies it via ::cue.
-- NULL → "medium" (the default).

ALTER TABLE stories ADD COLUMN IF NOT EXISTS subtitle_size VARCHAR(10);
