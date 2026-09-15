// Committees with densest recent activity.

MATCH (h:Hearing)-[:HELD_BY]->(c:Committee)
RETURN c.slug AS slug,
       c.name AS name,
       count(h) AS hearing_count,
       max(h.held_on) AS last_hearing
ORDER BY hearing_count DESC, last_hearing DESC
LIMIT 20;
