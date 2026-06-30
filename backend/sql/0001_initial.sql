-- =============================================================
-- Family Stories — Supabase initial schema (migration 0001)
-- =============================================================
-- Cria todas as tabelas do domínio com isolamento multi-tenant
-- via user_id (UUID FK -> auth.users) e Row Level Security.
--
-- IMPORTANTE: este ficheiro é DESTRUTIVO. As linhas DROP no topo
-- limpam tudo antes de recriar — corre só em projetos novos ou
-- em desenvolvimento. NUNCA em produção com dados a sério.
-- =============================================================

-- !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
-- !!  STOP — NÃO CORRAS ESTE FICHEIRO NUMA BD COM DADOS.       !!
-- !!  Os DROP abaixo estão DESATIVADOS (comentados) de propósito,
-- !!  porque já apagaram dados uma vez. Só os descomentes se     !!
-- !!  quiseres mesmo destruir TUDO e começar do zero.            !!
-- !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

-- ── 0. Limpar (DEV apenas — DESTRÓI DADOS! DESATIVADO) ─────────
-- DROP TABLE IF EXISTS task_records      CASCADE;
-- DROP TABLE IF EXISTS video_outputs     CASCADE;
-- DROP TABLE IF EXISTS project_media     CASCADE;
-- DROP TABLE IF EXISTS stories           CASCADE;
-- DROP TABLE IF EXISTS projects          CASCADE;
-- DROP TABLE IF EXISTS timeline_events   CASCADE;
-- DROP TABLE IF EXISTS persons           CASCADE;
-- DROP TABLE IF EXISTS media_files       CASCADE;

-- DROP TYPE IF EXISTS task_state;
-- DROP TYPE IF EXISTS task_kind;
-- DROP TYPE IF EXISTS video_status;
-- DROP TYPE IF EXISTS story_status;
-- DROP TYPE IF EXISTS confidence_level;
-- DROP TYPE IF EXISTS processing_status;
-- DROP TYPE IF EXISTS media_type;

-- ── 1. Enums ──────────────────────────────────────────────────
CREATE TYPE media_type        AS ENUM ('photo', 'video', 'document', 'gedcom');
CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE confidence_level  AS ENUM ('high', 'medium', 'low');
CREATE TYPE story_status      AS ENUM ('draft', 'completed', 'failed');
CREATE TYPE video_status      AS ENUM ('processing', 'completed', 'failed');
CREATE TYPE task_kind         AS ENUM ('narrative', 'video', 'ingest');
CREATE TYPE task_state        AS ENUM ('pending', 'running', 'done', 'failed');

-- ── 2. Tabelas ────────────────────────────────────────────────

-- 2.1 Fotografias / vídeos / documentos / GEDCOM
CREATE TABLE media_files (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    original_filename   VARCHAR(255) NOT NULL,
    stored_filename     VARCHAR(255) NOT NULL,
    file_path           VARCHAR(500) NOT NULL,        -- objeto na bucket Supabase Storage
    file_size           INTEGER,
    mime_type           VARCHAR(100),
    media_type          media_type   NOT NULL,

    date_taken          TIMESTAMPTZ,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    location_name       VARCHAR(255),
    camera_make         VARCHAR(100),
    camera_model        VARCHAR(100),

    ai_description      TEXT,
    ai_people_count     INTEGER,
    ai_setting          VARCHAR(255),
    ai_emotion          VARCHAR(100),
    ai_tags             JSONB,
    ai_narrative_hint   TEXT,

    ocr_text            TEXT,

    is_safe             BOOLEAN DEFAULT TRUE,
    checksum_md5        VARCHAR(32),
    raw_exif            JSONB,

    status              processing_status DEFAULT 'pending',
    error_message       TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- O nome de ficheiro guardado é único POR utilizador (não global)
    -- para não bloquear que dois users tenham "IMG_1234.jpg" cada um.
    CONSTRAINT uq_media_user_stored UNIQUE (user_id, stored_filename)
);

CREATE INDEX idx_media_user        ON media_files (user_id);
CREATE INDEX idx_media_user_status ON media_files (user_id, status);
CREATE INDEX idx_media_user_date   ON media_files (user_id, date_taken);

-- 2.2 Pessoas (GEDCOM + manuais)
CREATE TABLE persons (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID         NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    birth_date   TIMESTAMPTZ,
    death_date   TIMESTAMPTZ,
    birth_place  VARCHAR(255),
    notes        TEXT,
    gedcom_id    VARCHAR(100),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- O gedcom_id é único por user (vem do ficheiro importado).
    CONSTRAINT uq_persons_user_gedcom UNIQUE (user_id, gedcom_id)
);

CREATE INDEX idx_persons_user ON persons (user_id);

-- 2.3 Eventos da timeline
CREATE TABLE timeline_events (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    event_date       TIMESTAMPTZ,
    date_confidence  confidence_level DEFAULT 'low',
    date_label       VARCHAR(100),

    event_type       VARCHAR(50),
    title            VARCHAR(255),
    description      TEXT,
    location         VARCHAR(255),
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,

    media_file_id    BIGINT REFERENCES media_files(id) ON DELETE SET NULL,
    person_ids       JSONB DEFAULT '[]'::jsonb,
    sort_order       INTEGER DEFAULT 0,

    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_user       ON timeline_events (user_id);
CREATE INDEX idx_events_user_order ON timeline_events (user_id, sort_order);

-- 2.4 Projetos (workspaces)
CREATE TABLE projects (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID         NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            VARCHAR(120) NOT NULL,
    description     TEXT,
    cover_media_id  BIGINT       REFERENCES media_files(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_user ON projects (user_id);

-- 2.5 Junção Projeto ↔ Media
CREATE TABLE project_media (
    id          BIGSERIAL PRIMARY KEY,
    project_id  BIGINT      NOT NULL REFERENCES projects(id)    ON DELETE CASCADE,
    media_id    BIGINT      NOT NULL REFERENCES media_files(id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_project_media UNIQUE (project_id, media_id)
);

CREATE INDEX idx_pm_project ON project_media (project_id);
CREATE INDEX idx_pm_media   ON project_media (media_id);

-- 2.6 Narrativas
CREATE TABLE stories (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID         NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id    BIGINT       REFERENCES projects(id) ON DELETE SET NULL,

    title         VARCHAR(255) NOT NULL,
    event_type    VARCHAR(50)  DEFAULT 'default',
    narrative     TEXT         NOT NULL,
    template_used VARCHAR(100),
    llm_backend   VARCHAR(50),
    facts_used    INTEGER      DEFAULT 0,
    prompt_used   TEXT,
    status        story_status DEFAULT 'draft',
    person_ids    JSONB        DEFAULT '[]'::jsonb,

    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stories_user      ON stories (user_id);
CREATE INDEX idx_stories_user_proj ON stories (user_id, project_id);

-- 2.7 Vídeos gerados
CREATE TABLE video_outputs (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID   NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    story_id      BIGINT NOT NULL REFERENCES stories(id)    ON DELETE CASCADE,
    project_id    BIGINT REFERENCES projects(id) ON DELETE SET NULL,

    filename      VARCHAR(255),
    file_path     VARCHAR(500),                              -- objeto na bucket Storage
    file_size_mb  DOUBLE PRECISION,
    photos_used   INTEGER,
    status        video_status DEFAULT 'processing',
    error_message TEXT,

    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_videos_user  ON video_outputs (user_id);
CREATE INDEX idx_videos_story ON video_outputs (story_id);

-- 2.8 Tarefas em background
CREATE TABLE task_records (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    celery_id  VARCHAR(64) UNIQUE,
    kind       task_kind   NOT NULL,
    state      task_state  NOT NULL DEFAULT 'pending',

    story_id   BIGINT REFERENCES stories(id)       ON DELETE CASCADE,
    video_id   BIGINT REFERENCES video_outputs(id) ON DELETE CASCADE,

    payload    JSONB,
    result     JSONB,
    error      TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_user        ON task_records (user_id);
CREATE INDEX idx_tasks_user_state  ON task_records (user_id, state);
CREATE INDEX idx_tasks_celery_id   ON task_records (celery_id);

-- ── 3. updated_at trigger ─────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_media_updated_at    BEFORE UPDATE ON media_files    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects       FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_stories_updated_at  BEFORE UPDATE ON stories        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_tasks_updated_at    BEFORE UPDATE ON task_records   FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── 4. Row Level Security ─────────────────────────────────────
-- Cada user só vê / escreve linhas onde user_id = auth.uid().
-- O backend usa o JWT do utilizador → auth.uid() resolve para o sub.
-- O service_role bypassa RLS automaticamente (usar com cuidado).

ALTER TABLE media_files     ENABLE ROW LEVEL SECURITY;
ALTER TABLE persons         ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects        ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_media   ENABLE ROW LEVEL SECURITY;
ALTER TABLE stories         ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_outputs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_records    ENABLE ROW LEVEL SECURITY;

-- Helper macro: policy "all-CRUD por owner" — repete por tabela.
CREATE POLICY media_owner_all      ON media_files     FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY persons_owner_all    ON persons         FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY events_owner_all     ON timeline_events FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY projects_owner_all   ON projects        FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY stories_owner_all    ON stories         FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY videos_owner_all     ON video_outputs   FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY tasks_owner_all      ON task_records    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- project_media não tem user_id direta — herda a posse do projeto.
CREATE POLICY pm_owner_all ON project_media
FOR ALL TO authenticated
USING (
    EXISTS (SELECT 1 FROM projects p WHERE p.id = project_media.project_id AND p.user_id = auth.uid())
)
WITH CHECK (
    EXISTS (SELECT 1 FROM projects p WHERE p.id = project_media.project_id AND p.user_id = auth.uid())
);

-- ── 5. Supabase Storage: bucket "photos" + policies ───────────
-- Convenção de path: photos/{user_id}/{stored_filename}
-- A primeira pasta no path identifica o dono → RLS via foldername.

INSERT INTO storage.buckets (id, name, public)
VALUES ('photos', 'photos', false)
ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public;

-- Limpar policies anteriores (se re-correres este script).
DROP POLICY IF EXISTS "photos owner select" ON storage.objects;
DROP POLICY IF EXISTS "photos owner insert" ON storage.objects;
DROP POLICY IF EXISTS "photos owner update" ON storage.objects;
DROP POLICY IF EXISTS "photos owner delete" ON storage.objects;

CREATE POLICY "photos owner select" ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "photos owner insert" ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "photos owner update" ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text)
WITH CHECK (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "photos owner delete" ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);

-- ── Fim. ──────────────────────────────────────────────────────
