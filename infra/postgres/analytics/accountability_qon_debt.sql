-- QoN debt by portfolio and answering agency.
-- Safe to re-run: CREATE OR REPLACE VIEW.
-- Apply with: make db-apply   or   ingest apply-schema

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
