-- Additive columns for first-pass ANAO / Budget / AusTender adapters.
-- Do not recreate 007 foundation tables.
-- Fresh volumes: Docker applies this after 008.
-- Existing volumes: make db-apply.

ALTER TABLE outcomes
    ADD COLUMN IF NOT EXISTS confidence REAL;
ALTER TABLE outcomes
    ADD COLUMN IF NOT EXISTS agency_id UUID REFERENCES agencies(id) ON DELETE SET NULL;
ALTER TABLE outcomes
    ADD COLUMN IF NOT EXISTS scrutiny_item_id UUID REFERENCES scrutiny_items(id) ON DELETE SET NULL;
ALTER TABLE outcomes
    ADD COLUMN IF NOT EXISTS source_key TEXT;
ALTER TABLE outcomes
    ADD COLUMN IF NOT EXISTS identifiers JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS outcomes_source_key_uidx
    ON outcomes (source_key);

CREATE INDEX IF NOT EXISTS outcomes_agency_idx ON outcomes (agency_id);
CREATE INDEX IF NOT EXISTS outcomes_scrutiny_idx ON outcomes (scrutiny_item_id);

INSERT INTO schema_meta (key, value) VALUES
    ('source_adapters', '009_anao_budget_austender'),
    ('anao_adapter', 'work_index'),
    ('budget_measure_adapter', 'pbs_csv_bp2_docx'),
    ('austender_adapter', 'ocds')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
