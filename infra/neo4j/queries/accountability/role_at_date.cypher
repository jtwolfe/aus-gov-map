// Who held which seat on a date (role-at-decision).
// Parameters: $on  (ISO date string, e.g. a hearing.held_on)

MATCH (p:Person)-[h:HELD_ROLE_DURING]->(r:Role)
OPTIONAL MATCH (r)-[:OF_AGENCY]->(a:Agency)
WHERE ($on IS NULL OR h.start_date IS NULL OR h.start_date <= $on)
  AND ($on IS NULL OR h.end_date IS NULL OR h.end_date >= $on)
RETURN p.slug AS person_slug, p.name AS person_name,
       r.slug AS role_slug, r.title AS role_title, r.role_type AS role_type,
       r.portfolio AS portfolio, a.name AS agency,
       h.start_date AS start_date, h.end_date AS end_date, h.source AS source
ORDER BY r.portfolio, r.title, p.name;
