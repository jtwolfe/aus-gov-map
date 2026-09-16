-- Stage 3a precedent layer: judgments as sourced scrutiny on Acts.
-- Additive on top of 012_laws.sql. No guilt labels.
-- Fresh volumes: Docker applies this after 012.
-- Existing volumes: make db-apply.
-- See docs/laws-and-precedent.md.

-- ---------------------------------------------------------------------------
-- Scrutiny: allow type `judgment`.
-- ---------------------------------------------------------------------------
ALTER TABLE scrutiny_items DROP CONSTRAINT IF EXISTS scrutiny_items_type_chk;
ALTER TABLE scrutiny_items ADD CONSTRAINT scrutiny_items_type_chk CHECK (
    item_type IN (
        'qon', 'anao', 'inquiry_report', 'division', 'hearing_segment',
        'judgment', 'other'
    )
);

CREATE INDEX IF NOT EXISTS scrutiny_items_judgment_idx
    ON scrutiny_items (published_on DESC)
    WHERE item_type = 'judgment';

-- ---------------------------------------------------------------------------
-- Instrument links: construes / invalidates / upholds (judgment → Act).
-- voted_on / funded_by / tested_in already exist (007).
-- ---------------------------------------------------------------------------
ALTER TABLE instrument_links DROP CONSTRAINT IF EXISTS instrument_links_kind_chk;
ALTER TABLE instrument_links ADD CONSTRAINT instrument_links_kind_chk CHECK (
    link_kind IN (
        'accountable_for', 'responsible_official', 'promised_in', 'tested_in',
        'voted_on', 'funded_by', 'mentioned', 'other',
        'construes', 'invalidates', 'upholds'
    )
);

-- Precedent edges for law dossiers (sourced verbs only).
CREATE OR REPLACE VIEW v_precedent_links AS
SELECT
    il.id AS link_id,
    il.link_kind,
    il.source,
    il.notes,
    i.id AS instrument_id,
    i.slug AS instrument_slug,
    i.title AS instrument_title,
    i.instrument_type,
    s.id AS scrutiny_id,
    s.slug AS scrutiny_slug,
    s.title AS judgment_title,
    s.published_on,
    s.source AS judgment_source,
    s.source_url AS judgment_url,
    s.identifiers AS judgment_identifiers,
    o.id AS outcome_id,
    o.outcome_type,
    o.signal,
    o.notes AS outcome_notes
FROM instrument_links il
JOIN instruments i ON i.id = il.instrument_id
JOIN scrutiny_items s ON s.id = il.scrutiny_item_id
LEFT JOIN outcomes o ON o.scrutiny_item_id = s.id AND o.instrument_id = i.id
WHERE il.link_kind IN ('construes', 'invalidates', 'upholds')
  AND s.item_type = 'judgment';

INSERT INTO schema_meta (key, value) VALUES
    ('precedent', '013_precedent'),
    ('judgments_adapter', 'fixture_mvp'),
    ('graph_model_stage3a',
     'Instrument(bill|act); Person-VOTED_ON->Instrument; ScrutinyItem(judgment)-CONSTRUES|UPHOLDS|INVALIDATES->Instrument')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
