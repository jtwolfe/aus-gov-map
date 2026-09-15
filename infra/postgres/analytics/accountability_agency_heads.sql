-- Current APS secretaries / agency heads / deputies (coverage, not a verdict).
-- Safe to re-run: CREATE OR REPLACE VIEW.

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
