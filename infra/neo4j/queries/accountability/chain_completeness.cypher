// Instruments missing ACCOUNTABLE_FOR and/or RESPONSIBLE_OFFICIAL.
// A gap is missing sourced edges — not a finding of fault.

MATCH (i:Instrument)
OPTIONAL MATCH (min:Person)-[:ACCOUNTABLE_FOR]->(i)
OPTIONAL MATCH (off:Person)-[:RESPONSIBLE_OFFICIAL]->(i)
OPTIONAL MATCH (i)-[:OWNED_BY]->(a:Agency)
WITH i, a, count(DISTINCT min) AS ministers, count(DISTINCT off) AS officials
WHERE ministers = 0 OR officials = 0
RETURN i.slug AS slug, i.title AS title, i.instrument_type AS instrument_type,
       a.name AS agency,
       ministers > 0 AS has_accountable_minister,
       officials > 0 AS has_responsible_official
ORDER BY i.title;
