-- Additive APS occupancy + QoN claim glue on top of 007/008.
-- Fresh volumes: Docker applies this after 008.
-- Existing volumes: make db-apply.

-- Occupancy natural key for directory / executive-page ingest.
ALTER TABLE person_roles
    ADD COLUMN IF NOT EXISTS source_key TEXT;
ALTER TABLE person_roles
    ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS person_roles_source_key_uidx
    ON person_roles (source_key)
    WHERE source_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS person_roles_source_idx ON person_roles (source);

-- Taken-on-notice claims that cite a QoN number.
ALTER TABLE claims
    ADD COLUMN IF NOT EXISTS qon_id UUID REFERENCES qons(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS claims_qon_idx ON claims (qon_id);

-- Current secretary / agency head per agency (coverage, not a verdict).
CREATE OR REPLACE VIEW v_accountability_agency_heads AS
SELECT
    a.id AS agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    a.portfolio,
    a.source_url AS agency_source_url,
    p.id AS person_id,
    p.slug AS person_slug,
    p.name AS person_name,
    pr.role_type,
    COALESCE(r.title, pr.organisation, pr.role_type) AS role_title,
    pr.start_date,
    pr.end_date,
    pr.source,
    pr.source_url
FROM person_roles pr
JOIN people p ON p.id = pr.person_id
LEFT JOIN roles r ON r.id = pr.role_id
LEFT JOIN agencies a ON a.id = COALESCE(pr.agency_id, r.agency_id)
WHERE pr.role_type IN ('secretary', 'agency_head', 'deputy')
  AND (pr.end_date IS NULL OR pr.end_date >= CURRENT_DATE);

-- QoN debt plus the current responsible official when occupancy exists.
CREATE OR REPLACE VIEW v_accountability_qon_debt AS
SELECT
    COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
    a.id AS agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    head.person_slug AS responsible_official_slug,
    head.person_name AS responsible_official_name,
    head.role_type AS responsible_official_role,
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
LEFT JOIN LATERAL (
    SELECT p.slug AS person_slug, p.name AS person_name, pr.role_type
    FROM person_roles pr
    JOIN people p ON p.id = pr.person_id
    WHERE a.id IS NOT NULL
      AND pr.agency_id = a.id
      AND pr.role_type IN ('secretary', 'agency_head')
      AND (pr.end_date IS NULL OR pr.end_date >= CURRENT_DATE)
    ORDER BY CASE pr.role_type WHEN 'secretary' THEN 0 ELSE 1 END,
             pr.start_date DESC NULLS LAST
    LIMIT 1
) head ON TRUE
GROUP BY q.portfolio, a.id, a.slug, a.name,
         head.person_slug, head.person_name, head.role_type;

INSERT INTO schema_meta (key, value) VALUES
    ('aps_leaders', '010_aps_leaders'),
    ('qon_claim_link', 'claims.qon_id')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
