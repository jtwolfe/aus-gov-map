// Funding chain: contract/grant → measure/program (or appropriation).

MATCH (child:Instrument)-[:FUNDED_BY]->(parent:Instrument)
OPTIONAL MATCH (child)-[:OWNED_BY]->(a:Agency)
RETURN child.slug AS funded_slug, child.title AS funded_title,
       child.instrument_type AS funded_type,
       parent.slug AS funder_slug, parent.title AS funder_title,
       parent.instrument_type AS funder_type, a.name AS agency
ORDER BY parent.title, child.title;
