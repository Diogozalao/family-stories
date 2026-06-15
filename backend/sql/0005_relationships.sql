-- =============================================================
-- Migration 0005 — Family relationships in the database
-- =============================================================
-- Until now, kinship relations lived only in a per-user JSON graph on
-- disk (ephemeral on Render — wiped on every restart). To support a
-- manual tree editor and a reliable interactive tree view, relations now
-- live in the database.
--
-- ``kind`` mirrors the semantics used by the narrative graph:
--   'pai'      — from_person is the father  of to_person
--   'mãe'      — from_person is the mother  of to_person
--   'cônjuge'  — from_person and to_person are spouses (stored once)
--
-- Also adds ``sex`` to persons (M/F/U) so the tree can colour nodes and
-- the narrative can say "pai/mãe" correctly.
-- =============================================================

ALTER TABLE persons
    ADD COLUMN IF NOT EXISTS sex VARCHAR(1);

CREATE TABLE IF NOT EXISTS relationships (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID    NOT NULL,
    from_person_id BIGINT  NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    to_person_id   BIGINT  NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    kind           VARCHAR(16) NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_relationship UNIQUE (user_id, from_person_id, to_person_id, kind)
);

CREATE INDEX IF NOT EXISTS ix_relationships_user ON relationships (user_id);
CREATE INDEX IF NOT EXISTS ix_relationships_from ON relationships (from_person_id);
CREATE INDEX IF NOT EXISTS ix_relationships_to   ON relationships (to_person_id);
