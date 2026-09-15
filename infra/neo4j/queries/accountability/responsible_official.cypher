// Public-service responsible officer edges (sourced).

MATCH (p:Person)-[e:RESPONSIBLE_OFFICIAL]->(i:Instrument)
OPTIONAL MATCH (i)-[:OWNED_BY]->(a:Agency)
RETURN p.slug AS person_slug, p.name AS person_name,
       i.slug AS instrument_slug, i.title AS instrument_title,
       i.instrument_type AS instrument_type, a.name AS agency, e.source AS source
ORDER BY p.name, i.title;
