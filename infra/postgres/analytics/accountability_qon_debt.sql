-- QoN debt by portfolio and answering agency, plus current responsible official.
-- Safe to re-run: CREATE OR REPLACE VIEW.
-- Apply with: make db-apply   or   ingest apply-schema

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
