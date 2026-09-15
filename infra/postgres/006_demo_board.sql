-- Demo pinboard from FOI / procurement-ish chunk hits.
-- Prefers live hansard: hearings; falls back to any matching chunks (including fixture).
-- Re-runnable. Documented in README ("Current coverage" / boards).

INSERT INTO boards (slug, title, description)
VALUES (
    'foi-procurement',
    'FOI & procurement',
    'Seeded from chunk hits mentioning FOI, freedom of information, or procurement. Prefer live Hansard Officials when present.'
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    description = COALESCE(EXCLUDED.description, boards.description);

-- Unique target constraint is created in 004_analytics.sql; if it is missing,
-- this still avoids obvious duplicates via NOT EXISTS.

INSERT INTO pins (board_id, pin_type, target_id, note)
SELECT
    b.id,
    'chunk',
    ch.id,
    left(regexp_replace(ch.content, '\s+', ' ', 'g'), 160)
FROM boards b
JOIN chunks ch ON (
    ch.content ~* '(freedom of information|\bFOI\b|procurement)'
)
JOIN hearings h ON h.id = ch.hearing_id
WHERE b.slug = 'foi-procurement'
  AND NOT EXISTS (
      SELECT 1 FROM pins p
      WHERE p.board_id = b.id AND p.pin_type = 'chunk' AND p.target_id = ch.id
  )
ORDER BY (h.source_key LIKE 'hansard:%') DESC, h.held_on DESC NULLS LAST, ch.chunk_index
LIMIT 12;

INSERT INTO pins (board_id, pin_type, target_id, note)
SELECT
    b.id,
    'hearing',
    h.id,
    'Hearing with FOI/procurement chunk hits'
FROM boards b
JOIN hearings h ON h.id IN (
    SELECT DISTINCT ch.hearing_id
    FROM chunks ch
    WHERE ch.content ~* '(freedom of information|\bFOI\b|procurement)'
)
WHERE b.slug = 'foi-procurement'
  AND NOT EXISTS (
      SELECT 1 FROM pins p
      WHERE p.board_id = b.id AND p.pin_type = 'hearing' AND p.target_id = h.id
  )
LIMIT 6;
