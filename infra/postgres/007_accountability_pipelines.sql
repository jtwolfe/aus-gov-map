-- Additive accountability-map pipelines (Handbook live, Estimates segments,
-- Questions on Notice, proposed instruments, agency stubs).
-- Names match docs/accountability-map. Idempotent: IF NOT EXISTS / OR REPLACE.
-- Safe beside a parallel foundation PR that uses the same table names.
-- Existing volumes: `make db-apply` or `ingest apply-schema`.

-- ---------------------------------------------------------------------------
-- Agencies (official portfolio departments + parliamentary departments)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agencies (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    short_code    TEXT,
    portfolio     TEXT,
    kind          TEXT NOT NULL DEFAULT 'department',
    source_url    TEXT,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agencies_portfolio_idx ON agencies (portfolio);

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
-- Questions on Notice (EQON + optional transcript markers)
-- status: open | answered | overdue | unknown
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions_on_notice (
    id                         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_key                 TEXT NOT NULL UNIQUE,
    qon_number                 TEXT,
    portfolio_question_number  TEXT,
    portfolio                  TEXT,
    agency_id                  UUID REFERENCES agencies(id) ON DELETE SET NULL,
    agency_name                TEXT,
    asked_by                   TEXT,
    asked_on                   DATE,
    due_on                     DATE,
    answered_on                DATE,
    status                     TEXT NOT NULL DEFAULT 'unknown',
    question_text              TEXT,
    answer_text                TEXT,
    source_url                 TEXT,
    hearing_id                 UUID REFERENCES hearings(id) ON DELETE SET NULL,
    committee_name             TEXT,
    estimates_round            TEXT,
    metadata                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS qon_portfolio_idx ON questions_on_notice (portfolio);
CREATE INDEX IF NOT EXISTS qon_status_idx ON questions_on_notice (status);
CREATE INDEX IF NOT EXISTS qon_asked_on_idx ON questions_on_notice (asked_on DESC);

-- ---------------------------------------------------------------------------
-- Instruments (proposed decision objects — not asserted facts)
-- status: proposed | reviewed | asserted
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS instruments (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_key         TEXT NOT NULL UNIQUE,
    title              TEXT NOT NULL,
    kind               TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'proposed',
    confidence         REAL NOT NULL DEFAULT 0.3,
    source_chunk_id    UUID REFERENCES chunks(id) ON DELETE SET NULL,
    source_chunk_key   TEXT,
    hearing_id         UUID REFERENCES hearings(id) ON DELETE SET NULL,
    evidence_text      TEXT,
    notes              TEXT,
    metadata           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS instruments_status_idx ON instruments (status);
CREATE INDEX IF NOT EXISTS instruments_kind_idx ON instruments (kind);
CREATE INDEX IF NOT EXISTS instruments_chunk_key_idx ON instruments (source_chunk_key);

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

CREATE OR REPLACE VIEW v_qon_by_portfolio AS
SELECT
    COALESCE(NULLIF(btrim(portfolio), ''), '(unspecified)') AS portfolio,
    COUNT(*)::INT AS question_count,
    COUNT(*) FILTER (WHERE status = 'open')::INT AS open_count,
    COUNT(*) FILTER (WHERE status = 'answered')::INT AS answered_count,
    COUNT(*) FILTER (WHERE status = 'overdue')::INT AS overdue_count,
    COUNT(*) FILTER (WHERE status = 'unknown')::INT AS unknown_count,
    MAX(asked_on) AS last_asked_on
FROM questions_on_notice
GROUP BY 1;

-- Major departments. Names follow Directory / AAO portfolios (not invented).
-- Secretaries are not seeded — Parliamentary Handbook does not list APS SES.
INSERT INTO agencies (id, slug, name, short_code, portfolio, kind, source_url, notes)
VALUES
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:ag'),
     'attorney-generals', 'Attorney-General''s Department', 'AG',
     'Attorney-General''s', 'department',
     'https://www.ag.gov.au/',
     'Portfolio department. Secretaries need a separate APS / directory.gov.au source.'),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:daff'),
     'agriculture-fisheries-forestry', 'Department of Agriculture, Fisheries and Forestry', 'DAFF',
     'Agriculture, Fisheries and Forestry', 'department',
     'https://www.agriculture.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dcceew'),
     'climate-change-energy-environment-water',
     'Department of Climate Change, Energy, the Environment and Water', 'DCCEEW',
     'Climate Change, Energy, the Environment and Water', 'department',
     'https://www.dcceew.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:defence'),
     'defence', 'Department of Defence', 'Defence',
     'Defence', 'department',
     'https://www.defence.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:education'),
     'education', 'Department of Education', 'Education',
     'Education', 'department',
     'https://www.education.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dewr'),
     'employment-workplace-relations', 'Department of Employment and Workplace Relations', 'DEWR',
     'Employment and Workplace Relations', 'department',
     'https://www.dewr.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:finance'),
     'finance', 'Department of Finance', 'Finance',
     'Finance', 'department',
     'https://www.finance.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dfat'),
     'foreign-affairs-trade', 'Department of Foreign Affairs and Trade', 'DFAT',
     'Foreign Affairs and Trade', 'department',
     'https://www.dfat.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:health'),
     'health-disability-ageing', 'Department of Health, Disability and Ageing', 'Health',
     'Health, Disability and Ageing', 'department',
     'https://www.health.gov.au/',
     'Portfolio title as used in Senate Estimates EQON (2025–26).'),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:home-affairs'),
     'home-affairs', 'Department of Home Affairs', 'Home Affairs',
     'Home Affairs', 'department',
     'https://www.homeaffairs.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:disr'),
     'industry-science-resources', 'Department of Industry, Science and Resources', 'DISR',
     'Industry, Science and Resources', 'department',
     'https://www.industry.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:infrastructure'),
     'infrastructure-transport-rd-comms-arts',
     'Department of Infrastructure, Transport, Regional Development, Communications and the Arts',
     'DITRDCA',
     'Infrastructure, Transport, Regional Development, Communications, Sport and the Arts',
     'department',
     'https://www.infrastructure.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:pmc'),
     'prime-minister-cabinet', 'Department of the Prime Minister and Cabinet', 'PM&C',
     'Prime Minister and Cabinet', 'department',
     'https://www.pmc.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dss'),
     'social-services', 'Department of Social Services', 'DSS',
     'Social Services', 'department',
     'https://www.dss.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:treasury'),
     'treasury', 'Department of the Treasury', 'Treasury',
     'Treasury', 'department',
     'https://treasury.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dva'),
     'veterans-affairs', 'Department of Veterans'' Affairs', 'DVA',
     'Veterans'' Affairs', 'department',
     'https://www.dva.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:dps'),
     'parliamentary-services', 'Department of Parliamentary Services', 'DPS',
     'Parliamentary Departments', 'parliamentary_department',
     'https://www.aph.gov.au/About_Parliament/Parliamentary_Departments/Department_of_Parliamentary_Services',
     'Parliamentary department examined at FPA Estimates. Not a portfolio department.'),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:senate'),
     'department-of-the-senate', 'Department of the Senate', 'Senate',
     'Parliamentary Departments', 'parliamentary_department',
     'https://www.aph.gov.au/About_Parliament/Parliamentary_Departments/Department_of_the_Senate', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:house'),
     'department-of-the-house', 'Department of the House of Representatives', 'House',
     'Parliamentary Departments', 'parliamentary_department',
     'https://www.aph.gov.au/About_Parliament/Parliamentary_Departments/Department_of_the_House_of_Representatives', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:pbo'),
     'parliamentary-budget-office', 'Parliamentary Budget Office', 'PBO',
     'Parliamentary Departments', 'parliamentary_department',
     'https://www.aph.gov.au/About_Parliament/Parliamentary_Departments/Parliamentary_Budget_Office', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:apsc'),
     'australian-public-service-commission', 'Australian Public Service Commission', 'APSC',
     'Prime Minister and Cabinet', 'agency',
     'https://www.apsc.gov.au/',
     'APS employer. Secretary / Commissioner biographies are not in the Parliamentary Handbook.'),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:anao'),
     'australian-national-audit-office', 'Australian National Audit Office', 'ANAO',
     'Finance', 'agency',
     'https://www.anao.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:ato'),
     'australian-taxation-office', 'Australian Taxation Office', 'ATO',
     'Treasury', 'agency',
     'https://www.ato.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:aec'),
     'australian-electoral-commission', 'Australian Electoral Commission', 'AEC',
     'Finance', 'agency',
     'https://www.aec.gov.au/', NULL),
    (uuid_generate_v5(uuid_ns_url(), 'aus-gov-map:agency:niaa'),
     'national-indigenous-australians-agency', 'National Indigenous Australians Agency', 'NIAA',
     'Prime Minister and Cabinet', 'agency',
     'https://www.niaa.gov.au/', NULL)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    short_code = EXCLUDED.short_code,
    portfolio = EXCLUDED.portfolio,
    kind = EXCLUDED.kind,
    source_url = COALESCE(EXCLUDED.source_url, agencies.source_url),
    notes = COALESCE(EXCLUDED.notes, agencies.notes),
    updated_at = now();

INSERT INTO schema_meta (key, value) VALUES
    ('accountability_pipelines', '007'),
    ('handbook_stub', 'stage2-live')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
