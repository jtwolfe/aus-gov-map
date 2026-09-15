-- Stage 2 stub: Parliamentary Handbook officials.
-- Source (not ingested here): https://handbook.aph.gov.au
-- No fake data. The `handbook` ingest adapter returns an empty batch.

CREATE TABLE IF NOT EXISTS handbook_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID REFERENCES people(id) ON DELETE SET NULL,
    handbook_key    TEXT UNIQUE,
    display_name    TEXT,
    chamber         TEXT,
    electorate      TEXT,
    party           TEXT,
    aph_url         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS handbook_entries_person_idx
    ON handbook_entries (person_id);

CREATE TABLE IF NOT EXISTS handbook_roles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    handbook_entry_id   UUID NOT NULL REFERENCES handbook_entries(id) ON DELETE CASCADE,
    role_title          TEXT NOT NULL,
    role_kind           TEXT,
    started_on          DATE,
    ended_on            DATE,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS handbook_roles_entry_idx
    ON handbook_roles (handbook_entry_id);

CREATE TABLE IF NOT EXISTS handbook_tenure (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    handbook_entry_id   UUID NOT NULL REFERENCES handbook_entries(id) ON DELETE CASCADE,
    chamber             TEXT,
    electorate          TEXT,
    parliament_number   INT,
    started_on          DATE,
    ended_on            DATE
);

CREATE INDEX IF NOT EXISTS handbook_tenure_entry_idx
    ON handbook_tenure (handbook_entry_id);

INSERT INTO schema_meta (key, value) VALUES
    ('handbook_stub', 'stage2-empty')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
