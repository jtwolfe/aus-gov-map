-- aus-gov-map Stage 1 schema
-- Hearings, documents, chunks (+ vector), people, ingest runs, boards/pins stubs.

CREATE TABLE committees (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    chamber       TEXT NOT NULL DEFAULT 'Senate',
    kind          TEXT NOT NULL DEFAULT 'legislation',
    aph_url       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hearings (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    committee_id  UUID REFERENCES committees(id) ON DELETE SET NULL,
    title         TEXT NOT NULL,
    hearing_type  TEXT NOT NULL DEFAULT 'estimates',
    portfolio     TEXT,
    held_on       DATE,
    location      TEXT DEFAULT 'Parliament House, Canberra',
    source        TEXT NOT NULL,
    source_url    TEXT,
    source_key    TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'published',
    summary       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX hearings_held_on_idx ON hearings (held_on DESC);
CREATE INDEX hearings_type_idx ON hearings (hearing_type);
CREATE INDEX hearings_source_idx ON hearings (source);

CREATE TABLE people (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    role_title    TEXT,
    party         TEXT,
    portfolio     TEXT,
    organisation  TEXT,
    aph_url       TEXT,
    bio           TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hearing_people (
    hearing_id    UUID NOT NULL REFERENCES hearings(id) ON DELETE CASCADE,
    person_id     UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role          TEXT NOT NULL DEFAULT 'appeared',
    PRIMARY KEY (hearing_id, person_id, role)
);

CREATE INDEX hearing_people_person_idx ON hearing_people (person_id);

CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hearing_id    UUID REFERENCES hearings(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    doc_type      TEXT NOT NULL DEFAULT 'hansard',
    source_url    TEXT,
    source_key    TEXT NOT NULL UNIQUE,
    content_text  TEXT,
    published_at  DATE,
    license_note  TEXT DEFAULT '© Commonwealth of Australia — typically CC BY-NC-ND; attribute. Research / non-commercial framing.',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX documents_hearing_idx ON documents (hearing_id);

CREATE TABLE chunks (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id   UUID REFERENCES documents(id) ON DELETE CASCADE,
    hearing_id    UUID REFERENCES hearings(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    token_count   INT,
    speaker_name  TEXT,
    embedding     vector(384),
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_key    TEXT NOT NULL UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX chunks_document_idx ON chunks (document_id);
CREATE INDEX chunks_hearing_idx ON chunks (hearing_id);
CREATE INDEX chunks_fts_idx ON chunks USING gin (to_tsvector('english', content));
CREATE INDEX chunks_trgm_idx ON chunks USING gin (content gin_trgm_ops);

-- IVFFlat needs some rows before it is useful; HNSW is fine for a scaffold.
CREATE INDEX chunks_embedding_hnsw_idx ON chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE topics (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hearing_topics (
    hearing_id    UUID NOT NULL REFERENCES hearings(id) ON DELETE CASCADE,
    topic_id      UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (hearing_id, topic_id)
);

CREATE TABLE ingest_runs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source           TEXT NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at      TIMESTAMPTZ,
    status           TEXT NOT NULL DEFAULT 'running',
    records_fetched  INT NOT NULL DEFAULT 0,
    records_upserted INT NOT NULL DEFAULT 0,
    error            TEXT,
    meta             JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX ingest_runs_started_idx ON ingest_runs (started_at DESC);

-- Stage 1 stubs for researcher pinboards (Stage 2 expands sharing / auth).
CREATE TABLE boards (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pins (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id      UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    pin_type      TEXT NOT NULL,
    target_id     UUID NOT NULL,
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX pins_board_idx ON pins (board_id);
CREATE INDEX pins_target_idx ON pins (pin_type, target_id);

CREATE TABLE schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO schema_meta (key, value) VALUES
    ('stage', '1'),
    ('embedding_dim', '384'),
    ('graph_model', 'Person-APPEARED_AT->Hearing-HELD_BY->Committee; Hearing-DISCUSSES->Topic');
