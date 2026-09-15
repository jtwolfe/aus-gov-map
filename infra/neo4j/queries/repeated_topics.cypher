// Topics discussed across more than one hearing.

MATCH (h:Hearing)-[:DISCUSSES]->(t:Topic)
RETURN t.slug AS slug,
       t.name AS name,
       count(DISTINCT h) AS hearing_count,
       max(h.held_on) AS last_seen
ORDER BY hearing_count DESC, last_seen DESC
LIMIT 25;
