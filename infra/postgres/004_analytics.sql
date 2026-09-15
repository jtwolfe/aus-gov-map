-- Incremental Stage 1.1: pin uniqueness + analytics views.
-- Idempotent. Existing Docker volumes will not re-run 001–003; apply this file
-- with `make db-apply` or `ingest apply-schema`.
-- Readable copies of the views also live in analytics/001_views.sql.

CREATE UNIQUE INDEX IF NOT EXISTS pins_board_target_uidx
    ON pins (board_id, pin_type, target_id);

CREATE OR REPLACE VIEW v_people_across_estimates AS
SELECT
    p.id,
    p.slug,
    p.name,
    p.role_title,
    p.organisation,
    COUNT(DISTINCT h.id) AS estimates_hearings,
    MIN(h.held_on) AS first_seen,
    MAX(h.held_on) AS last_seen
FROM people p
JOIN hearing_people hp ON hp.person_id = p.id
JOIN hearings h ON h.id = hp.hearing_id
WHERE h.hearing_type = 'estimates'
GROUP BY p.id;

CREATE OR REPLACE VIEW v_committee_recent_activity AS
SELECT
    c.id,
    c.slug,
    c.name,
    c.chamber,
    COUNT(h.id) AS hearing_count,
    COUNT(h.id) FILTER (WHERE h.held_on >= CURRENT_DATE - INTERVAL '18 months') AS recent_hearings,
    COUNT(h.id) FILTER (WHERE h.hearing_type = 'estimates') AS estimates_count,
    MAX(h.held_on) AS last_hearing
FROM committees c
LEFT JOIN hearings h ON h.committee_id = c.id
GROUP BY c.id;

CREATE OR REPLACE VIEW v_repeated_topic_mentions AS
SELECT
    t.id,
    t.slug,
    t.name,
    COUNT(DISTINCT ht.hearing_id) AS hearing_count,
    MAX(h.held_on) AS last_seen
FROM topics t
JOIN hearing_topics ht ON ht.topic_id = t.id
JOIN hearings h ON h.id = ht.hearing_id
GROUP BY t.id;

CREATE OR REPLACE VIEW v_repeated_text_mentions AS
WITH needles AS (
    SELECT unnest(ARRAY[
        'FOI',
        'freedom of information',
        'procurement',
        'integrity',
        'question on notice',
        'consultancy',
        'grants'
    ]) AS needle
)
SELECT
    n.needle,
    COUNT(DISTINCT ch.hearing_id) AS hearing_count,
    COUNT(*) AS chunk_hits,
    MAX(h.held_on) AS last_seen
FROM needles n
JOIN chunks ch ON ch.content ILIKE '%' || n.needle || '%'
JOIN hearings h ON h.id = ch.hearing_id
GROUP BY n.needle;
