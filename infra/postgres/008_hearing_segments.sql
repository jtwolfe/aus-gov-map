-- Additive pipeline extensions on top of 007_accountability.sql.
-- Do not recreate agencies / instruments / qons / roles.
-- Fresh volumes: Docker applies this after 007.
-- Existing volumes: make db-apply.

-- ---------------------------------------------------------------------------
-- Structured Estimates segments (derived from Official TalkText)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hearing_segments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hearing_id      UUID REFERENCES hearings(id) ON DELETE CASCADE,
    document_id     UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_key      TEXT NOT NULL UNIQUE,
    segment_index   INT NOT NULL,
    kind            TEXT NOT NULL,
    speaker_name    TEXT,
    portfolio       TEXT,
    agency          TEXT,
    content         TEXT NOT NULL,
    char_start      INT,
    char_end        INT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS hearing_segments_hearing_idx ON hearing_segments (hearing_id);
CREATE INDEX IF NOT EXISTS hearing_segments_kind_idx ON hearing_segments (kind);
CREATE INDEX IF NOT EXISTS hearing_segments_portfolio_idx ON hearing_segments (portfolio);

-- ---------------------------------------------------------------------------
-- Proposed instruments: status + confidence on the foundation table
-- ---------------------------------------------------------------------------
ALTER TABLE instruments
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'unknown';
ALTER TABLE instruments
    ADD COLUMN IF NOT EXISTS confidence REAL;

CREATE INDEX IF NOT EXISTS instruments_status_idx ON instruments (status);

-- Extra QoN provenance (committee / PQ number / EQON payload)
ALTER TABLE qons
    ADD COLUMN IF NOT EXISTS identifiers JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Natural keys for Handbook upserts (tables created in 005_handbook.sql).
CREATE UNIQUE INDEX IF NOT EXISTS handbook_roles_natural_uidx
    ON handbook_roles (
        handbook_entry_id,
        role_title,
        (COALESCE(started_on, DATE '0001-01-01'))
    );

CREATE UNIQUE INDEX IF NOT EXISTS handbook_tenure_natural_uidx
    ON handbook_tenure (
        handbook_entry_id,
        (COALESCE(chamber, '')),
        (COALESCE(started_on, DATE '0001-01-01'))
    );

-- Compatibility alias for Insights / older dry-run notes.
CREATE OR REPLACE VIEW v_qon_by_portfolio AS
SELECT
    COALESCE(NULLIF(btrim(portfolio), ''), '(unspecified portfolio)') AS portfolio,
    COUNT(*)::INT AS question_count,
    COUNT(*) FILTER (WHERE status = 'open')::INT AS open_count,
    COUNT(*) FILTER (WHERE status = 'answered')::INT AS answered_count,
    COUNT(*) FILTER (WHERE status = 'overdue')::INT AS overdue_count,
    COUNT(*) FILTER (WHERE status = 'unknown')::INT AS unknown_count,
    COUNT(*) FILTER (WHERE status = 'refused')::INT AS refused_count,
    MAX(asked_on) AS last_asked_on
FROM qons
GROUP BY 1;

INSERT INTO schema_meta (key, value) VALUES
    ('accountability_pipelines', '008_hearing_segments'),
    ('qon_adapter', 'eqon')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
