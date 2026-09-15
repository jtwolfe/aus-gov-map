-- ANAO (and linked outcome) rows per instrument / agency.
-- Signal counts are sourced flags, not a severity score for a person.
-- Safe to re-run: CREATE OR REPLACE VIEW.

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
