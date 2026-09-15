// People appearing across many Estimates hearings.
// Browser: http://localhost:7474  (neo4j / ausgovmap)

MATCH (p:Person)-[:APPEARED_AT]->(h:Hearing)
WHERE h.hearing_type = 'estimates'
RETURN p.slug AS slug,
       p.name AS name,
       count(DISTINCT h) AS estimates_hearings,
       max(h.held_on) AS last_seen
ORDER BY estimates_hearings DESC, last_seen DESC
LIMIT 25;
