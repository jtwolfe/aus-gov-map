// aus-gov-map graph model (Stage 1)
//
//   (:Person {id, slug, name, party, role_title})
//   (:Hearing {id, slug, title, held_on, hearing_type, source_key})
//   (:Committee {id, slug, name, chamber})
//   (:Topic {id, slug, name})
//   (:Document {id, title, doc_type})
//
//   (Person)-[:APPEARED_AT {role}]->(Hearing)
//   (Hearing)-[:HELD_BY]->(Committee)
//   (Person)-[:MEMBER_OF {role}]->(Committee)
//   (Hearing)-[:DISCUSSES]->(Topic)
//   (Document)-[:TRANSCRIPT_OF]->(Hearing)
//
// Stage 2 Accountability Foundation (see docs/accountability-map.md)
//
//   (:Role {id, slug, title, role_type, portfolio})
//   (:Agency {id, slug, name, portfolio})
//   (:Instrument {id, slug, title, instrument_type})
//   (:ScrutinyItem {id, slug, title, item_type})
//   (:Claim {id, claim_type})
//   (:Outcome {id, outcome_type, signal})
//
//   (Person)-[:HELD_ROLE_DURING {start_date, end_date, source}]->(Role)
//   (Role)-[:OF_AGENCY]->(Agency)
//   (Person)-[:ACCOUNTABLE_FOR {source}]->(Instrument)
//   (Person)-[:RESPONSIBLE_OFFICIAL {source}]->(Instrument)
//   (Claim)-[:PROMISED_IN]->(Instrument)
//   (Instrument)-[:TESTED_IN]->(ScrutinyItem)
//   (Person)-[:VOTED_ON {vote, source}]->(Instrument)
//   (Instrument)-[:FUNDED_BY]->(Instrument)
//   (Hearing)-[:SCRUTINISES]->(Instrument)
//   (Instrument)-[:OWNED_BY]->(Agency)

CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT person_slug IF NOT EXISTS
FOR (p:Person) REQUIRE p.slug IS UNIQUE;

CREATE CONSTRAINT hearing_id IF NOT EXISTS
FOR (h:Hearing) REQUIRE h.id IS UNIQUE;

CREATE CONSTRAINT hearing_slug IF NOT EXISTS
FOR (h:Hearing) REQUIRE h.slug IS UNIQUE;

CREATE CONSTRAINT committee_id IF NOT EXISTS
FOR (c:Committee) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT committee_slug IF NOT EXISTS
FOR (c:Committee) REQUIRE c.slug IS UNIQUE;

CREATE CONSTRAINT topic_id IF NOT EXISTS
FOR (t:Topic) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT topic_slug IF NOT EXISTS
FOR (t:Topic) REQUIRE t.slug IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX hearing_held_on IF NOT EXISTS FOR (h:Hearing) ON (h.held_on);
CREATE INDEX hearing_type IF NOT EXISTS FOR (h:Hearing) ON (h.hearing_type);

CREATE CONSTRAINT role_id IF NOT EXISTS
FOR (r:Role) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT role_slug IF NOT EXISTS
FOR (r:Role) REQUIRE r.slug IS UNIQUE;

CREATE CONSTRAINT agency_id IF NOT EXISTS
FOR (a:Agency) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT agency_slug IF NOT EXISTS
FOR (a:Agency) REQUIRE a.slug IS UNIQUE;

CREATE CONSTRAINT instrument_id IF NOT EXISTS
FOR (i:Instrument) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT instrument_slug IF NOT EXISTS
FOR (i:Instrument) REQUIRE i.slug IS UNIQUE;

CREATE CONSTRAINT scrutiny_id IF NOT EXISTS
FOR (s:ScrutinyItem) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT claim_id IF NOT EXISTS
FOR (c:Claim) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT outcome_id IF NOT EXISTS
FOR (o:Outcome) REQUIRE o.id IS UNIQUE;

CREATE INDEX role_type IF NOT EXISTS FOR (r:Role) ON (r.role_type);
CREATE INDEX instrument_type IF NOT EXISTS FOR (i:Instrument) ON (i.instrument_type);
CREATE INDEX scrutiny_type IF NOT EXISTS FOR (s:ScrutinyItem) ON (s.item_type);
