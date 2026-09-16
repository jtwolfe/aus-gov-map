-- Responsibility Atlas helpers. Additive; safe if 007–010 already applied.
-- Hearing segments must never be plotted as 10k nodes — roll up to hearing level.
-- Fresh volumes: Docker applies this after 010.
-- Existing volumes: make db-apply.

CREATE OR REPLACE VIEW v_atlas_hearing_moments AS
SELECT
    h.id AS hearing_id,
    h.slug,
    h.title,
    h.held_on,
    h.portfolio,
    h.hearing_type,
    h.source_key,
    h.source_url,
    COUNT(hs.id)::int AS segment_count,
    COUNT(DISTINCT hs.portfolio) FILTER (WHERE NULLIF(btrim(hs.portfolio), '') IS NOT NULL)::int
        AS portfolio_chip_count,
    COUNT(DISTINCT hs.agency) FILTER (WHERE NULLIF(btrim(hs.agency), '') IS NOT NULL)::int
        AS agency_chip_count,
    COUNT(*) FILTER (WHERE hs.kind = 'portfolio_header')::int AS portfolio_header_count,
    COUNT(*) FILTER (WHERE hs.kind = 'agency_header')::int AS agency_header_count,
    COUNT(*) FILTER (WHERE hs.kind = 'taken_on_notice')::int AS taken_on_notice_count
FROM hearings h
LEFT JOIN hearing_segments hs ON hs.hearing_id = h.id
GROUP BY h.id;

CREATE INDEX IF NOT EXISTS hearings_portfolio_idx ON hearings (portfolio);

INSERT INTO schema_meta (key, value) VALUES
    ('responsibility_atlas', '011_atlas'),
    ('atlas_hearing_rollup', 'v_atlas_hearing_moments')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
