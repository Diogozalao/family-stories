-- ── Narrator voice per story ───────────────────────────────────────────────
-- Remember which narrator voice the user picked for the documentary
-- ("male" / "female"). M4 resolves it to a neural voice per language
-- (e.g. pt-PT-DuarteNeural vs pt-PT-RaquelNeural). NULL → default (male),
-- matching the previous behaviour for existing stories.

ALTER TABLE stories ADD COLUMN IF NOT EXISTS voice VARCHAR(16);
