// Occupancy edges for a person (or everyone).

MATCH (p:Person)-[h:HELD_ROLE_DURING]->(r:Role)
OPTIONAL MATCH (r)-[:OF_AGENCY]->(a:Agency)
RETURN p.slug AS person_slug, p.name AS person_name,
       r.title AS role_title, r.role_type AS role_type,
       r.portfolio AS portfolio, a.name AS agency,
       h.start_date AS start_date, h.end_date AS end_date, h.source AS source
ORDER BY p.name, h.start_date;
