// Sourced divisions (TheyVoteForYou / Hansard). Absence of a vote is not a whip inference.

MATCH (p:Person)-[v:VOTED_ON]->(i:Instrument)
WHERE i.instrument_type = 'bill' OR v.vote IS NOT NULL
RETURN p.slug AS person_slug, p.name AS person_name,
       i.title AS instrument_title, v.vote AS vote, v.source AS source
ORDER BY i.title, p.name;
