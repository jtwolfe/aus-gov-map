// Distinct occupants of the same Role — coverage fog, not motive.

MATCH (p:Person)-[:HELD_ROLE_DURING]->(r:Role)
WITH r, count(DISTINCT p) AS occupant_count
WHERE occupant_count >= 2
OPTIONAL MATCH (r)-[:OF_AGENCY]->(a:Agency)
RETURN r.slug AS role_slug, r.title AS role_title, r.role_type AS role_type,
       r.portfolio AS portfolio, a.name AS agency, occupant_count
ORDER BY occupant_count DESC, r.title;
