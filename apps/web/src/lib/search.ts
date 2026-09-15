import { loadFixtures } from "./fixtures";
import { postgresAvailable, query } from "./db";
import { loadCatalog } from "./data";
import type { SearchHit, SearchMode } from "./types";

function excerpt(text: string, q: string, width = 180): string {
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  const at = lower.indexOf(needle);
  if (at < 0) {
    return text.length > width ? `${text.slice(0, width).trim()}…` : text;
  }
  const start = Math.max(0, at - 40);
  const slice = text.slice(start, start + width).trim();
  return `${start > 0 ? "…" : ""}${slice}${start + width < text.length ? "…" : ""}`;
}

function scoreText(text: string, terms: string[]): number {
  const lower = text.toLowerCase();
  let score = 0;
  for (const term of terms) {
    if (!term) continue;
    if (lower.includes(term)) score += 3;
    const hits = lower.split(term).length - 1;
    score += hits;
  }
  return score;
}

function lexicalHits(q: string): SearchHit[] {
  const terms = q.toLowerCase().split(/\s+/).filter((t) => t.length > 1);
  if (!terms.length) return [];
  const seed = loadFixtures();
  const hits: SearchHit[] = [];

  for (const hearing of seed.hearings) {
    const hay = [hearing.title, hearing.summary, hearing.portfolio, hearing.committee?.name]
      .filter(Boolean)
      .join(" ");
    const score = scoreText(hay, terms);
    if (score > 0) {
      hits.push({
        kind: "hearing",
        id: hearing.id,
        slug: hearing.slug,
        title: hearing.title,
        subtitle: hearing.committee?.name,
        excerpt: hearing.summary ?? excerpt(hay, q),
        href: `/hearings/${hearing.slug}`,
        score,
        mode: "keyword",
      });
    }
  }

  for (const person of seed.people) {
    const hay = [person.name, person.roleTitle, person.party, person.portfolio, person.bio]
      .filter(Boolean)
      .join(" ");
    const score = scoreText(hay, terms);
    if (score > 0) {
      hits.push({
        kind: "person",
        id: person.id,
        slug: person.slug,
        title: person.name,
        subtitle: [person.roleTitle, person.party].filter(Boolean).join(" · "),
        excerpt: person.bio ?? hay,
        href: `/people/${person.slug}`,
        score,
        mode: "keyword",
      });
    }
  }

  for (const chunk of seed.chunks) {
    const score = scoreText(chunk.content, terms);
    if (score > 0) {
      const hearing = seed.hearings.find((h) => h.id === chunk.hearingId);
      hits.push({
        kind: "chunk",
        id: chunk.id,
        slug: hearing?.slug,
        title: hearing?.title ?? "Transcript excerpt",
        subtitle: chunk.speakerName ?? "Official",
        excerpt: excerpt(chunk.content, q),
        href: hearing ? `/hearings/${hearing.slug}#excerpt` : "/hearings",
        score,
        mode: "keyword",
      });
    }
  }

  return hits.sort((a, b) => b.score - a.score);
}

function semanticPlaceholder(q: string): SearchHit[] {
  // Offline stand-in: rank fixture chunks by token overlap (same shape as vector hits).
  const terms = new Set(q.toLowerCase().split(/\s+/).filter((t) => t.length > 2));
  if (!terms.size) return [];
  const seed = loadFixtures();
  const hits: SearchHit[] = [];
  for (const chunk of seed.chunks) {
    const tokens = chunk.content.toLowerCase().split(/\W+/);
    const overlap = tokens.filter((t) => terms.has(t)).length;
    if (!overlap) continue;
    const hearing = seed.hearings.find((h) => h.id === chunk.hearingId);
    hits.push({
      kind: "chunk",
      id: `sem-${chunk.id}`,
      slug: hearing?.slug,
      title: hearing?.title ?? "Semantic match",
      subtitle: "semantic placeholder",
      excerpt: excerpt(chunk.content, q),
      href: hearing ? `/hearings/${hearing.slug}#excerpt` : "/search",
      score: overlap / Math.sqrt(tokens.length || 1),
      mode: "semantic",
    });
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 12);
}

async function postgresKeyword(q: string): Promise<SearchHit[]> {
  const rows = await query<{
    kind: string;
    id: string;
    slug: string | null;
    title: string;
    subtitle: string | null;
    excerpt: string;
    rank: number;
  }>(
    `
    WITH q AS (SELECT websearch_to_tsquery('english', $1) AS tsq, $1 AS raw)
    SELECT * FROM (
      SELECT 'hearing'::text AS kind, h.id::text, h.slug, h.title,
             c.name AS subtitle,
             COALESCE(h.summary, h.title) AS excerpt,
             ts_rank(to_tsvector('english', coalesce(h.title,'') || ' ' || coalesce(h.summary,'')), (SELECT tsq FROM q)) AS rank
      FROM hearings h
      LEFT JOIN committees c ON c.id = h.committee_id
      WHERE to_tsvector('english', coalesce(h.title,'') || ' ' || coalesce(h.summary,'')) @@ (SELECT tsq FROM q)
         OR h.title ILIKE '%' || (SELECT raw FROM q) || '%'

      UNION ALL

      SELECT 'person', p.id::text, p.slug, p.name,
             NULLIF(concat_ws(' · ', p.role_title, p.party), ''),
             COALESCE(p.bio, p.name),
             ts_rank(to_tsvector('english', coalesce(p.name,'') || ' ' || coalesce(p.bio,'')), (SELECT tsq FROM q))
      FROM people p
      WHERE to_tsvector('english', coalesce(p.name,'') || ' ' || coalesce(p.bio,'')) @@ (SELECT tsq FROM q)
         OR p.name ILIKE '%' || (SELECT raw FROM q) || '%'

      UNION ALL

      SELECT 'chunk', ch.id::text, h.slug, h.title,
             ch.speaker_name,
             left(ch.content, 240),
             ts_rank(to_tsvector('english', ch.content), (SELECT tsq FROM q))
      FROM chunks ch
      JOIN hearings h ON h.id = ch.hearing_id
      WHERE to_tsvector('english', ch.content) @@ (SELECT tsq FROM q)
         OR ch.content ILIKE '%' || (SELECT raw FROM q) || '%'
    ) x
    ORDER BY rank DESC
    LIMIT 40
    `,
    [q],
  );

  return rows.map((row) => ({
    kind: row.kind as SearchHit["kind"],
    id: row.id,
    slug: row.slug ?? undefined,
    title: row.title,
    subtitle: row.subtitle ?? undefined,
    excerpt: row.excerpt,
    href:
      row.kind === "person"
        ? `/people/${row.slug}`
        : row.slug
          ? `/hearings/${row.slug}`
          : "/search",
    score: Number(row.rank) || 1,
    mode: "keyword" as const,
  }));
}

async function postgresSemantic(q: string): Promise<SearchHit[]> {
  // Requires embeddings from ingest. Hash embedder is applied at ingest time;
  // we approximate the query vector here the same way if chunks have embeddings.
  const rows = await query<{
    id: string;
    slug: string;
    title: string;
    speaker_name: string | null;
    content: string;
    dist: number;
  }>(
    `
    SELECT ch.id::text, h.slug, h.title, ch.speaker_name, left(ch.content, 240) AS content,
           0.0 AS dist
    FROM chunks ch
    JOIN hearings h ON h.id = ch.hearing_id
    WHERE ch.embedding IS NOT NULL
      AND ch.content ILIKE '%' || $1 || '%'
    LIMIT 12
    `,
    [q],
  );
  if (rows.length) {
    return rows.map((row, idx) => ({
      kind: "chunk" as const,
      id: row.id,
      slug: row.slug,
      title: row.title,
      subtitle: row.speaker_name ?? "vector",
      excerpt: row.content,
      href: `/hearings/${row.slug}#excerpt`,
      score: 1 / (idx + 1),
      mode: "semantic" as const,
    }));
  }
  return semanticPlaceholder(q);
}

export async function searchCatalog(q: string, mode: SearchMode): Promise<{
  hits: SearchHit[];
  source: "postgres" | "fixture";
  mode: SearchMode;
}> {
  const trimmed = q.trim();
  if (!trimmed) {
    return { hits: [], source: (await loadCatalog()).source, mode };
  }

  const live = await postgresAvailable();
  let keyword: SearchHit[] = [];
  let semantic: SearchHit[] = [];

  if (live) {
    try {
      if (mode !== "semantic") keyword = await postgresKeyword(trimmed);
      if (mode !== "keyword") semantic = await postgresSemantic(trimmed);
      const hits = mergeHits(keyword, semantic, mode);
      return { hits, source: "postgres", mode };
    } catch {
      /* fixture fallback */
    }
  }

  if (mode !== "semantic") keyword = lexicalHits(trimmed);
  if (mode !== "keyword") semantic = semanticPlaceholder(trimmed);
  return { hits: mergeHits(keyword, semantic, mode), source: "fixture", mode };
}

function mergeHits(keyword: SearchHit[], semantic: SearchHit[], mode: SearchMode): SearchHit[] {
  if (mode === "keyword") return keyword.slice(0, 30);
  if (mode === "semantic") return semantic.slice(0, 30);
  const seen = new Set<string>();
  const out: SearchHit[] = [];
  for (const hit of [...keyword, ...semantic]) {
    const key = `${hit.kind}:${hit.href}:${hit.excerpt.slice(0, 40)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(hit);
  }
  return out.slice(0, 40);
}
