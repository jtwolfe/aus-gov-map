// QoN-shaped scrutiny still open or overdue.
// Prefer Postgres v_accountability_qon_debt when counts are needed.

MATCH (s:ScrutinyItem)
WHERE s.item_type = 'qon'
  AND coalesce(s.status, 'unknown') IN ['open', 'overdue', 'unknown']
OPTIONAL MATCH (s)-[:ANSWERED_BY_AGENCY]->(a:Agency)
RETURN coalesce(s.portfolio, '(unspecified)') AS portfolio,
       a.name AS agency,
       count(s) AS openish_count,
       count(s) FILTER (WHERE s.status = 'overdue') AS overdue_count
ORDER BY openish_count DESC;
