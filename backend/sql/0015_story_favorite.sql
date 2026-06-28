-- ── Favourite stories ───────────────────────────────────────────────────────
-- Let the user pin/star stories; favourites sort to the top of the list.
-- NULL/false → not a favourite (the default for existing stories).

ALTER TABLE stories ADD COLUMN IF NOT EXISTS favorite BOOLEAN DEFAULT FALSE;
