-- Stage 2 Accountability Foundation — additive. Do not drop Stage 1 tables.
-- Fresh Docker volumes run this file after 001–006.
-- Existing volumes: make db-apply  (ingest apply-schema).
-- See docs/accountability-map.md.

-- ---------------------------------------------------------------------------
-- Agencies (public service organisations). People stay on existing `people`.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agencies (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    short_name    TEXT,
    portfolio     TEXT,
    parent_id     UUID REFERENCES agencies(id) ON DELETE SET NULL,
    aao_ref       TEXT,
    source        TEXT,
    source_url    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agencies_portfolio_idx ON agencies (portfolio);
CREATE INDEX IF NOT EXISTS agencies_parent_idx ON agencies (parent_id);

-- ---------------------------------------------------------------------------
-- Role catalog + time-bounded occupancy (shared people.id).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    role_type     TEXT NOT NULL,
    portfolio     TEXT,
    organisation  TEXT,
    agency_id     UUID REFERENCES agencies(id) ON DELETE SET NULL,
    source        TEXT,
    source_url    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT roles_type_chk CHECK (role_type IN (
        'minister', 'shadow', 'secretary', 'deputy',
        'committee', 'mp', 'senator', 'agency_head', 'other'
    ))
);

CREATE INDEX IF NOT EXISTS roles_type_idx ON roles (role_type);
CREATE INDEX IF NOT EXISTS roles_agency_idx ON roles (agency_id);
CREATE INDEX IF NOT EXISTS roles_portfolio_idx ON roles (portfolio);

CREATE TABLE IF NOT EXISTS person_roles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id           UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role_id             UUID REFERENCES roles(id) ON DELETE SET NULL,
    role_type           TEXT NOT NULL,
    portfolio           TEXT,
    organisation        TEXT,
    agency_id           UUID REFERENCES agencies(id) ON DELETE SET NULL,
    start_date          DATE,
    end_date            DATE,
    source              TEXT NOT NULL,
    source_url          TEXT,
    handbook_role_id    UUID REFERENCES handbook_roles(id) ON DELETE SET NULL,
    handbook_tenure_id  UUID REFERENCES handbook_tenure(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT person_roles_type_chk CHECK (role_type IN (
        'minister', 'shadow', 'secretary', 'deputy',
        'committee', 'mp', 'senator', 'agency_head', 'other'
    )),
    CONSTRAINT person_roles_dates_chk CHECK (
        end_date IS NULL OR start_date IS NULL OR end_date >= start_date
    )
);

CREATE INDEX IF NOT EXISTS person_roles_person_idx ON person_roles (person_id);
CREATE INDEX IF NOT EXISTS person_roles_role_idx ON person_roles (role_id);
CREATE INDEX IF NOT EXISTS person_roles_agency_idx ON person_roles (agency_id);
CREATE INDEX IF NOT EXISTS person_roles_dates_idx ON person_roles (start_date, end_date);
CREATE INDEX IF NOT EXISTS person_roles_type_idx ON person_roles (role_type);

-- Handbook extract stays the provenance store; extra columns help promote
-- tenures into person_roles without a second people table.
ALTER TABLE handbook_roles
    ADD COLUMN IF NOT EXISTS role_type TEXT;
ALTER TABLE handbook_roles
    ADD COLUMN IF NOT EXISTS portfolio TEXT;
ALTER TABLE handbook_roles
    ADD COLUMN IF NOT EXISTS organisation TEXT;
ALTER TABLE handbook_roles
    ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE handbook_tenure
    ADD COLUMN IF NOT EXISTS source TEXT;

-- ---------------------------------------------------------------------------
-- Instruments (program / measure / bill / contract / grant / policy).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS instruments (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug              TEXT NOT NULL UNIQUE,
    instrument_type   TEXT NOT NULL,
    title             TEXT NOT NULL,
    identifiers       JSONB NOT NULL DEFAULT '{}'::jsonb,
    agency_id         UUID REFERENCES agencies(id) ON DELETE SET NULL,
    announced_on      DATE,
    commenced_on      DATE,
    ended_on          DATE,
    amount_aud        NUMERIC,
    currency          TEXT DEFAULT 'AUD',
    source            TEXT,
    source_url        TEXT,
    source_key        TEXT UNIQUE,
    summary           TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT instruments_type_chk CHECK (instrument_type IN (
        'program', 'measure', 'bill', 'contract', 'grant', 'policy', 'other'
    ))
);

CREATE INDEX IF NOT EXISTS instruments_type_idx ON instruments (instrument_type);
CREATE INDEX IF NOT EXISTS instruments_agency_idx ON instruments (agency_id);
CREATE INDEX IF NOT EXISTS instruments_title_trgm_idx ON instruments USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS instruments_identifiers_idx ON instruments USING gin (identifiers);

-- ---------------------------------------------------------------------------
-- Scrutiny + QoNs + claims + outcomes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrutiny_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug            TEXT UNIQUE,
    item_type       TEXT NOT NULL,
    title           TEXT NOT NULL,
    identifiers     JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_on    DATE,
    hearing_id      UUID REFERENCES hearings(id) ON DELETE SET NULL,
    source          TEXT,
    source_url      TEXT,
    source_key      TEXT UNIQUE,
    summary         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT scrutiny_items_type_chk CHECK (item_type IN (
        'qon', 'anao', 'inquiry_report', 'division', 'hearing_segment', 'other'
    ))
);

CREATE INDEX IF NOT EXISTS scrutiny_items_type_idx ON scrutiny_items (item_type);
CREATE INDEX IF NOT EXISTS scrutiny_items_hearing_idx ON scrutiny_items (hearing_id);
CREATE INDEX IF NOT EXISTS scrutiny_items_published_idx ON scrutiny_items (published_on DESC);

CREATE TABLE IF NOT EXISTS qons (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    number                  TEXT,
    house                   TEXT,
    portfolio               TEXT,
    asking_member           TEXT,
    asking_person_id        UUID REFERENCES people(id) ON DELETE SET NULL,
    answering_minister_id   UUID REFERENCES people(id) ON DELETE SET NULL,
    answering_agency_id     UUID REFERENCES agencies(id) ON DELETE SET NULL,
    asked_on                DATE,
    due_on                  DATE,
    answered_on             DATE,
    status                  TEXT NOT NULL DEFAULT 'unknown',
    question_ref            TEXT,
    answer_ref              TEXT,
    hearing_id              UUID REFERENCES hearings(id) ON DELETE SET NULL,
    scrutiny_item_id        UUID REFERENCES scrutiny_items(id) ON DELETE SET NULL,
    source                  TEXT,
    source_url              TEXT,
    source_key              TEXT UNIQUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT qons_status_chk CHECK (status IN (
        'open', 'answered', 'overdue', 'refused', 'unknown'
    ))
);

CREATE INDEX IF NOT EXISTS qons_status_idx ON qons (status);
CREATE INDEX IF NOT EXISTS qons_portfolio_idx ON qons (portfolio);
CREATE INDEX IF NOT EXISTS qons_agency_idx ON qons (answering_agency_id);
CREATE INDEX IF NOT EXISTS qons_hearing_idx ON qons (hearing_id);
CREATE INDEX IF NOT EXISTS qons_due_idx ON qons (due_on);

CREATE TABLE IF NOT EXISTS claims (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id       UUID REFERENCES people(id) ON DELETE SET NULL,
    speaker_name    TEXT,
    hearing_id      UUID REFERENCES hearings(id) ON DELETE SET NULL,
    chunk_id        UUID REFERENCES chunks(id) ON DELETE SET NULL,
    instrument_id   UUID REFERENCES instruments(id) ON DELETE SET NULL,
    claim_type      TEXT NOT NULL,
    text_span       TEXT NOT NULL,
    span_start      INT,
    span_end        INT,
    made_on         DATE,
    source          TEXT,
    source_key      TEXT UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT claims_type_chk CHECK (claim_type IN (
        'promise', 'assurance', 'taken_on_notice', 'denial'
    ))
);

CREATE INDEX IF NOT EXISTS claims_person_idx ON claims (person_id);
CREATE INDEX IF NOT EXISTS claims_hearing_idx ON claims (hearing_id);
CREATE INDEX IF NOT EXISTS claims_instrument_idx ON claims (instrument_id);
CREATE INDEX IF NOT EXISTS claims_type_idx ON claims (claim_type);

CREATE TABLE IF NOT EXISTS outcomes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outcome_type    TEXT NOT NULL,
    instrument_id   UUID REFERENCES instruments(id) ON DELETE SET NULL,
    signal          TEXT,
    occurred_on     DATE,
    source          TEXT,
    source_url      TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS outcomes_instrument_idx ON outcomes (instrument_id);
CREATE INDEX IF NOT EXISTS outcomes_type_idx ON outcomes (outcome_type);

-- ---------------------------------------------------------------------------
-- Instrument ↔ hearing / chunk / person / agency / scrutiny (sourced edges).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS instrument_links (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    target_kind         TEXT NOT NULL,
    target_id           UUID NOT NULL,
    hearing_id          UUID REFERENCES hearings(id) ON DELETE CASCADE,
    chunk_id            UUID REFERENCES chunks(id) ON DELETE CASCADE,
    person_id           UUID REFERENCES people(id) ON DELETE CASCADE,
    agency_id           UUID REFERENCES agencies(id) ON DELETE CASCADE,
    scrutiny_item_id    UUID REFERENCES scrutiny_items(id) ON DELETE CASCADE,
    role_id             UUID REFERENCES roles(id) ON DELETE SET NULL,
    other_instrument_id UUID REFERENCES instruments(id) ON DELETE CASCADE,
    link_kind           TEXT NOT NULL,
    source              TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT instrument_links_target_chk CHECK (target_kind IN (
        'hearing', 'chunk', 'person', 'agency', 'scrutiny', 'role', 'instrument'
    )),
    CONSTRAINT instrument_links_kind_chk CHECK (link_kind IN (
        'accountable_for', 'responsible_official', 'promised_in', 'tested_in',
        'voted_on', 'funded_by', 'mentioned', 'other'
    )),
    CONSTRAINT instrument_links_unique UNIQUE (
        instrument_id, target_kind, target_id, link_kind
    )
);

CREATE INDEX IF NOT EXISTS instrument_links_instrument_idx ON instrument_links (instrument_id);
CREATE INDEX IF NOT EXISTS instrument_links_kind_idx ON instrument_links (link_kind);
CREATE INDEX IF NOT EXISTS instrument_links_person_idx ON instrument_links (person_id);
CREATE INDEX IF NOT EXISTS instrument_links_hearing_idx ON instrument_links (hearing_id);

-- ---------------------------------------------------------------------------
-- Metric views (readable copies also live in analytics/accountability_*.sql)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_accountability_qon_debt AS
SELECT
    COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
    a.id AS agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    COUNT(*) FILTER (WHERE q.status IN ('open', 'overdue', 'unknown')) AS openish_count,
    COUNT(*) FILTER (WHERE q.status = 'overdue'
        OR (q.status = 'open' AND q.due_on IS NOT NULL AND q.due_on < CURRENT_DATE)
    ) AS overdue_count,
    COUNT(*) FILTER (WHERE q.status = 'answered') AS answered_count,
    COUNT(*) FILTER (WHERE q.status = 'refused') AS refused_count,
    COUNT(*) AS qon_count,
    MIN(q.asked_on) AS first_asked,
    MAX(q.due_on) AS latest_due
FROM qons q
LEFT JOIN agencies a ON a.id = q.answering_agency_id
GROUP BY q.portfolio, a.id, a.slug, a.name;

CREATE OR REPLACE VIEW v_accountability_people_estimates AS
SELECT
    p.id,
    p.slug,
    p.name,
    p.role_title,
    p.organisation,
    COUNT(DISTINCT h.id) AS estimates_hearings,
    MIN(h.held_on) AS first_seen,
    MAX(h.held_on) AS last_seen
FROM people p
JOIN hearing_people hp ON hp.person_id = p.id
JOIN hearings h ON h.id = hp.hearing_id
WHERE h.hearing_type = 'estimates'
GROUP BY p.id
HAVING COUNT(DISTINCT h.id) >= 2;

CREATE OR REPLACE VIEW v_accountability_chain_completeness AS
SELECT
    i.id,
    i.slug,
    i.title,
    i.instrument_type,
    i.agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    i.announced_on,
    i.commenced_on,
    i.source,
    i.source_url,
    EXISTS (
        SELECT 1 FROM instrument_links il
        WHERE il.instrument_id = i.id AND il.link_kind = 'accountable_for'
    ) AS has_accountable_minister,
    EXISTS (
        SELECT 1 FROM instrument_links il
        WHERE il.instrument_id = i.id AND il.link_kind = 'responsible_official'
    ) AS has_responsible_official,
    (
        NOT EXISTS (
            SELECT 1 FROM instrument_links il
            WHERE il.instrument_id = i.id AND il.link_kind = 'accountable_for'
        )
        OR NOT EXISTS (
            SELECT 1 FROM instrument_links il
            WHERE il.instrument_id = i.id AND il.link_kind = 'responsible_official'
        )
    ) AS chain_incomplete
FROM instruments i
LEFT JOIN agencies a ON a.id = i.agency_id;

CREATE OR REPLACE VIEW v_accountability_promise_receipt AS
SELECT
    c.id AS claim_id,
    c.claim_type,
    c.text_span,
    c.made_on,
    c.speaker_name,
    p.slug AS person_slug,
    p.name AS person_name,
    h.slug AS hearing_slug,
    h.title AS hearing_title,
    h.held_on AS hearing_held_on,
    i.id AS instrument_id,
    i.slug AS instrument_slug,
    i.title AS instrument_title,
    i.instrument_type,
    o.id AS outcome_id,
    o.outcome_type,
    o.signal,
    o.occurred_on AS outcome_on,
    o.source AS outcome_source
FROM claims c
LEFT JOIN people p ON p.id = c.person_id
LEFT JOIN hearings h ON h.id = c.hearing_id
LEFT JOIN instruments i ON i.id = c.instrument_id
LEFT JOIN outcomes o ON o.instrument_id = i.id
WHERE c.claim_type IN ('promise', 'assurance', 'taken_on_notice');

CREATE OR REPLACE VIEW v_accountability_reshuffle_fog AS
SELECT
    COALESCE(pr.role_id::text, pr.portfolio, pr.organisation, pr.role_type) AS seat_key,
    pr.role_type,
    pr.portfolio,
    pr.organisation,
    r.slug AS role_slug,
    r.title AS role_title,
    COUNT(DISTINCT pr.person_id) AS occupant_count,
    COUNT(*) AS tenure_count,
    MIN(pr.start_date) AS first_start,
    MAX(COALESCE(pr.end_date, CURRENT_DATE)) AS last_end,
    AVG(
        EXTRACT(EPOCH FROM (
            COALESCE(pr.end_date, CURRENT_DATE) - COALESCE(pr.start_date, COALESCE(pr.end_date, CURRENT_DATE))
        )) / 86400.0
    ) AS avg_tenure_days
FROM person_roles pr
LEFT JOIN roles r ON r.id = pr.role_id
GROUP BY
    COALESCE(pr.role_id::text, pr.portfolio, pr.organisation, pr.role_type),
    pr.role_type, pr.portfolio, pr.organisation, r.slug, r.title
HAVING COUNT(DISTINCT pr.person_id) >= 2;

CREATE OR REPLACE VIEW v_accountability_audit_gravity AS
SELECT
    s.id AS scrutiny_id,
    s.slug AS scrutiny_slug,
    s.title AS scrutiny_title,
    s.published_on,
    s.source_url,
    i.id AS instrument_id,
    i.slug AS instrument_slug,
    i.title AS instrument_title,
    a.id AS agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    COUNT(o.id) FILTER (
        WHERE o.signal IN ('adverse', 'unmet', 'partial')
           OR o.outcome_type ILIKE '%audit%'
    ) AS weighted_signals,
    MAX(o.occurred_on) AS last_outcome_on
FROM scrutiny_items s
LEFT JOIN instrument_links il
    ON il.scrutiny_item_id = s.id AND il.link_kind = 'tested_in'
LEFT JOIN instruments i ON i.id = il.instrument_id
LEFT JOIN agencies a ON a.id = i.agency_id
LEFT JOIN outcomes o ON o.instrument_id = i.id
WHERE s.item_type = 'anao'
GROUP BY s.id, i.id, a.id;

INSERT INTO schema_meta (key, value) VALUES
    ('stage', '2'),
    ('accountability_foundation', 'stage2'),
    ('graph_model_stage2',
     'Person-HELD_ROLE_DURING->Role; Person-ACCOUNTABLE_FOR->Instrument; Person-RESPONSIBLE_OFFICIAL->Instrument; Claim-PROMISED_IN->Instrument; Instrument-TESTED_IN->ScrutinyItem; Person-VOTED_ON->Instrument; Instrument-FUNDED_BY->Instrument')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
