-- People who appear at more than one Estimates hearing (Stage 1 plug-in).
-- Same grain as v_people_across_estimates, restricted to multi-hearing rows.
-- Safe to re-run: CREATE OR REPLACE VIEW.

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
