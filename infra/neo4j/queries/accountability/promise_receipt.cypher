// PROMISED_IN → TESTED_IN (and optional outcome).
// Hansard claims are citations, not verdicts.

MATCH (c:Claim)-[:PROMISED_IN]->(i:Instrument)
OPTIONAL MATCH (i)-[:TESTED_IN]->(s:ScrutinyItem)
OPTIONAL MATCH (o:Outcome)-[:OF_INSTRUMENT]->(i)
OPTIONAL MATCH (p:Person)-[:STATED]->(c)
RETURN c.claim_type AS claim_type, c.made_on AS made_on,
       i.slug AS instrument_slug, i.title AS instrument_title,
       s.item_type AS scrutiny_type, s.title AS scrutiny_title,
       o.signal AS outcome_signal, o.occurred_on AS outcome_on
ORDER BY c.made_on DESC;
