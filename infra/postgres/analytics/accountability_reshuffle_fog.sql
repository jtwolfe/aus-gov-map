-- Distinct occupants of the same seat / portfolio (coverage fog, not motive).
-- Safe to re-run: CREATE OR REPLACE VIEW.

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
            COALESCE(pr.end_date, CURRENT_DATE)
            - COALESCE(pr.start_date, COALESCE(pr.end_date, CURRENT_DATE))
        )) / 86400.0
    ) AS avg_tenure_days
FROM person_roles pr
LEFT JOIN roles r ON r.id = pr.role_id
GROUP BY
    COALESCE(pr.role_id::text, pr.portfolio, pr.organisation, pr.role_type),
    pr.role_type, pr.portfolio, pr.organisation, r.slug, r.title
HAVING COUNT(DISTINCT pr.person_id) >= 2;
