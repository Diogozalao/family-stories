-- =============================================================
-- Family Stories — migration 0009: profile photo per person
-- =============================================================
-- Adds an optional "profile photo" pointer to each person so the
-- Family tree can show a face and M3 can anchor the person to a real
-- image. Soft pointer (no FK): if the referenced media is deleted the
-- column simply dangles and the UI falls back to initials.
-- Idempotent — safe to re-run.

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS photo_media_id BIGINT;

COMMENT ON COLUMN persons.photo_media_id IS
    'Optional MediaFile id chosen as this person''s profile photo (soft pointer, no FK).';
