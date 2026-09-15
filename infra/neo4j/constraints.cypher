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
// Stage 2/3 stubs (do not create yet): Agency, Portfolio, Bill, QON.

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
