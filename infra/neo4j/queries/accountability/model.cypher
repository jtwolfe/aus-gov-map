// Stage 2 duty-map MERGE templates.
// Source every edge. Do not create nodes without a sourced id.
// See docs/accountability-map.md.

// Role catalog + occupancy
MERGE (r:Role {id: $role_id})
SET r.slug = $role_slug, r.title = $title, r.role_type = $role_type,
    r.portfolio = $portfolio;

MERGE (a:Agency {id: $agency_id})
SET a.slug = $agency_slug, a.name = $agency_name, a.portfolio = $portfolio;

MERGE (r)-[:OF_AGENCY]->(a);

MATCH (p:Person {id: $person_id})
MATCH (r:Role {id: $role_id})
MERGE (p)-[h:HELD_ROLE_DURING]->(r)
SET h.start_date = $start_date, h.end_date = $end_date, h.source = $source;

// Instrument + agency ownership
MERGE (i:Instrument {id: $instrument_id})
SET i.slug = $instrument_slug, i.title = $instrument_title,
    i.instrument_type = $instrument_type;

MERGE (i)-[:OWNED_BY]->(a);

// Duty edges (minister vs public service)
MATCH (minister:Person {id: $minister_id})
MATCH (i:Instrument {id: $instrument_id})
MERGE (minister)-[af:ACCOUNTABLE_FOR]->(i)
SET af.source = $source;

MATCH (official:Person {id: $official_id})
MATCH (i:Instrument {id: $instrument_id})
MERGE (official)-[ro:RESPONSIBLE_OFFICIAL]->(i)
SET ro.source = $source;

// Promise → instrument → later scrutiny
MERGE (c:Claim {id: $claim_id})
SET c.claim_type = $claim_type, c.made_on = $made_on;
MERGE (c)-[:PROMISED_IN]->(i);

MERGE (s:ScrutinyItem {id: $scrutiny_id})
SET s.slug = $scrutiny_slug, s.title = $scrutiny_title, s.item_type = $item_type;
MERGE (i)-[:TESTED_IN]->(s);

// Hearing as scrutiny (Stage 1 plug-in)
MATCH (h:Hearing {id: $hearing_id})
MERGE (h)-[:SCRUTINISES]->(i);

// Division
MATCH (voter:Person {id: $voter_id})
MERGE (voter)-[v:VOTED_ON]->(i)
SET v.vote = $vote, v.source = $source;

// Funding chain
MATCH (child:Instrument {id: $funded_id})
MATCH (parent:Instrument {id: $funder_id})
MERGE (child)-[:FUNDED_BY]->(parent);
