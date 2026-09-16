-- Responsibility Atlas helpers. Additive; safe if 007–010 already applied.
-- Hearing segments must never be plotted as 10k nodes — roll up to hearing level.
-- Lane evidence: hearings.portfolio, else MODE of sourced segment portfolios /
-- agencies (prefer agency_header), else the committee name. Do not invent names.
-- Person-shaped agency strings are excluded from segment_agency.
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
    c.name AS committee_name,
    COUNT(hs.id)::int AS segment_count,
    COUNT(DISTINCT hs.portfolio) FILTER (WHERE NULLIF(btrim(hs.portfolio), '') IS NOT NULL)::int
        AS portfolio_chip_count,
    COUNT(DISTINCT hs.agency) FILTER (WHERE NULLIF(btrim(hs.agency), '') IS NOT NULL)::int
        AS agency_chip_count,
    COUNT(*) FILTER (WHERE hs.kind = 'portfolio_header')::int AS portfolio_header_count,
    COUNT(*) FILTER (WHERE hs.kind = 'agency_header')::int AS agency_header_count,
    COUNT(*) FILTER (WHERE hs.kind = 'taken_on_notice')::int AS taken_on_notice_count,
    (
        SELECT NULLIF(btrim(s.portfolio), '')
        FROM hearing_segments s
        WHERE s.hearing_id = h.id
          AND NULLIF(btrim(s.portfolio), '') IS NOT NULL
          AND s.portfolio !~* '^(Senator|Ms |Mr |Mrs |Dr |Hon |Chair)\b'
        GROUP BY NULLIF(btrim(s.portfolio), '')
        ORDER BY COUNT(*) DESC, NULLIF(btrim(s.portfolio), '')
        LIMIT 1
    ) AS segment_portfolio,
    (
        SELECT NULLIF(btrim(s.agency), '')
        FROM hearing_segments s
        WHERE s.hearing_id = h.id
          AND NULLIF(btrim(s.agency), '') IS NOT NULL
          AND s.agency !~* '^(Senator|Ms |Mr |Mrs |Dr |Hon |Chair)\b'
          AND (
            s.kind = 'agency_header'
            OR s.agency ~* '^(Department |Australian |National |Parliamentary |Office |Services )'
            OR s.agency ~* '(Department|Agency|Commission|Authority|Office|Corporation)$'
          )
        GROUP BY NULLIF(btrim(s.agency), '')
        ORDER BY COUNT(*) FILTER (WHERE s.kind = 'agency_header') DESC,
                 COUNT(*) DESC,
                 NULLIF(btrim(s.agency), '')
        LIMIT 1
    ) AS segment_agency,
    COALESCE(
        NULLIF(btrim(h.portfolio), ''),
        (
            SELECT NULLIF(btrim(s.portfolio), '')
            FROM hearing_segments s
            WHERE s.hearing_id = h.id
              AND NULLIF(btrim(s.portfolio), '') IS NOT NULL
              AND s.portfolio !~* '^(Senator|Ms |Mr |Mrs |Dr |Hon |Chair)\b'
            GROUP BY NULLIF(btrim(s.portfolio), '')
            ORDER BY COUNT(*) DESC, NULLIF(btrim(s.portfolio), '')
            LIMIT 1
        ),
        NULLIF(btrim(regexp_replace(c.name, '\s+(Legislation|References) Committee$', '', 'i')), '')
    ) AS lane_portfolio
FROM hearings h
LEFT JOIN committees c ON c.id = h.committee_id
LEFT JOIN hearing_segments hs ON hs.hearing_id = h.id
GROUP BY h.id, c.name;

CREATE INDEX IF NOT EXISTS hearings_portfolio_idx ON hearings (portfolio);

INSERT INTO schema_meta (key, value) VALUES
    ('responsibility_atlas', '011_atlas'),
    ('atlas_hearing_rollup', 'v_atlas_hearing_moments'),
    ('atlas_hearing_lane_evidence', 'segment_portfolio')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
