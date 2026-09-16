-- Stage 3a: Bills / Acts as first-class instruments + sourced divisions.
-- Additive on top of 007–011. Do not drop foundation tables.
-- Fresh volumes: Docker applies this after 011.
-- Existing volumes: make db-apply.
-- See docs/laws-and-precedent.md.

-- ---------------------------------------------------------------------------
-- Instruments: allow type `act`. Status stays free text (law catalog +
-- proposed / sourced / unknown). Documented in docs/laws-and-precedent.md.
-- ---------------------------------------------------------------------------
ALTER TABLE instruments DROP CONSTRAINT IF EXISTS instruments_type_chk;
ALTER TABLE instruments ADD CONSTRAINT instruments_type_chk CHECK (
    instrument_type IN (
        'program', 'measure', 'bill', 'act', 'contract', 'grant', 'policy', 'other'
    )
);

CREATE INDEX IF NOT EXISTS instruments_law_type_idx
    ON instruments (instrument_type)
    WHERE instrument_type IN ('bill', 'act');

-- ---------------------------------------------------------------------------
-- Divisions (They Vote For You / Hansard recorded votes)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS divisions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug                TEXT UNIQUE,
    source_key          TEXT NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    house               TEXT,
    divided_on          DATE,
    number              INT,
    instrument_id       UUID REFERENCES instruments(id) ON DELETE SET NULL,
    scrutiny_item_id    UUID REFERENCES scrutiny_items(id) ON DELETE SET NULL,
    ayes                INT,
    noes                INT,
    abstentions         INT,
    possible_turnout    INT,
    source              TEXT NOT NULL DEFAULT 'theyvoteforyou',
    source_url          TEXT,
    identifiers         JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT divisions_house_chk CHECK (
        house IS NULL OR house IN ('representatives', 'senate', 'other')
    )
);

CREATE INDEX IF NOT EXISTS divisions_instrument_idx ON divisions (instrument_id);
CREATE INDEX IF NOT EXISTS divisions_date_idx ON divisions (divided_on DESC);
CREATE INDEX IF NOT EXISTS divisions_house_idx ON divisions (house);

-- ---------------------------------------------------------------------------
-- Division votes — published name always stored; person_id only when resolved.
-- Never invent people from this table.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS division_votes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    division_id     UUID NOT NULL REFERENCES divisions(id) ON DELETE CASCADE,
    person_id       UUID REFERENCES people(id) ON DELETE SET NULL,
    person_name     TEXT NOT NULL,
    vote            TEXT NOT NULL,
    party           TEXT,
    electorate      TEXT,
    source          TEXT,
    identifiers     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT division_votes_vote_chk CHECK (
        vote IN ('aye', 'no', 'abstain', 'absent')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS division_votes_resolved_uidx
    ON division_votes (division_id, person_id)
    WHERE person_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS division_votes_name_uidx
    ON division_votes (division_id, lower(person_name), vote);

CREATE INDEX IF NOT EXISTS division_votes_person_idx ON division_votes (person_id);
CREATE INDEX IF NOT EXISTS division_votes_division_idx ON division_votes (division_id);

-- Vote summary for law dossiers (coverage, not a score).
CREATE OR REPLACE VIEW v_law_vote_summary AS
SELECT
    d.id AS division_id,
    d.slug AS division_slug,
    d.title,
    d.house,
    d.divided_on,
    d.number,
    d.instrument_id,
    i.slug AS instrument_slug,
    i.title AS instrument_title,
    i.instrument_type,
    d.ayes,
    d.noes,
    d.abstentions,
    d.source,
    d.source_url,
    COUNT(dv.id)::int AS named_votes,
    COUNT(dv.person_id)::int AS resolved_votes
FROM divisions d
LEFT JOIN instruments i ON i.id = d.instrument_id
LEFT JOIN division_votes dv ON dv.division_id = d.id
GROUP BY d.id, i.slug, i.title, i.instrument_type;

-- Atlas helper: bill / act threads (votes stay on dossiers).
CREATE OR REPLACE VIEW v_atlas_law_threads AS
SELECT
    i.id,
    i.slug,
    i.title,
    i.instrument_type,
    i.status,
    i.announced_on,
    i.commenced_on,
    i.ended_on,
    i.source,
    i.source_url,
    i.identifiers,
    a.slug AS agency_slug,
    a.name AS agency_name,
    a.portfolio
FROM instruments i
LEFT JOIN agencies a ON a.id = i.agency_id
WHERE i.instrument_type IN ('bill', 'act');

INSERT INTO schema_meta (key, value) VALUES
    ('laws', '012_laws'),
    ('divisions_adapter', 'theyvoteforyou'),
    ('legislation_adapter', 'frl')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
