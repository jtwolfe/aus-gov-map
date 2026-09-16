import { loadFixtures } from "./fixtures";
import { postgresAvailable, query } from "./db";
import { loadCatalog } from "./data";
import { hashEmbed, vectorLiteral } from "./hash-embed";
import type { SearchFilters, SearchHit, SearchMode } from "./types";

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

function matchesFilters(
  hearing: {
    hearingType?: string;
    heldOn?: string | null;
    committee?: { slug: string; name: string } | null;
    people?: Array<{ person: { name: string; slug: string } }>;
  },
  filters: SearchFilters,
): boolean {
  if (filters.hearingType === "estimates" && hearing.hearingType !== "estimates") return false;
  if (filters.hearingType === "other" && hearing.hearingType === "estimates") return false;
  if (filters.from && (hearing.heldOn ?? "") < filters.from) return false;
  if (filters.to && (hearing.heldOn ?? "") > filters.to) return false;
  if (filters.committee) {
    const needle = filters.committee.toLowerCase();
    const slug = hearing.committee?.slug ?? "";
    const name = hearing.committee?.name ?? "";
    if (!slug.includes(needle) && !name.toLowerCase().includes(needle)) return false;
  }
  if (filters.person) {
    const needle = filters.person.toLowerCase();
    const hit = (hearing.people ?? []).some(
      (a) => a.person.name.toLowerCase().includes(needle) || a.person.slug.includes(needle),
    );
    if (!hit) return false;
  }
  return true;
}

function lexicalHits(q: string, filters: SearchFilters): SearchHit[] {
  const terms = q.toLowerCase().split(/\s+/).filter((t) => t.length > 1);
  if (!terms.length) return [];
  const seed = loadFixtures();
  const hits: SearchHit[] = [];

  for (const hearing of seed.hearings) {
    if (!matchesFilters(hearing, filters)) continue;
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
        sourceKey: hearing.sourceKey,
        hearingType: hearing.hearingType,
      });
    }
  }

  for (const person of seed.people) {
    if (filters.person && !person.name.toLowerCase().includes(filters.person.toLowerCase())) {
      continue;
    }
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
    const hearing = seed.hearings.find((h) => h.id === chunk.hearingId);
    if (hearing && !matchesFilters(hearing, filters)) continue;
    const score = scoreText(chunk.content, terms);
    if (score > 0) {
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
        sourceKey: hearing?.sourceKey,
        hearingType: hearing?.hearingType,
      });
    }
  }

  return hits.sort((a, b) => b.score - a.score);
}

function semanticPlaceholder(q: string, filters: SearchFilters): SearchHit[] {
  const terms = new Set(q.toLowerCase().split(/\s+/).filter((t) => t.length > 2));
  if (!terms.size) return [];
  const seed = loadFixtures();
  const hits: SearchHit[] = [];
  for (const chunk of seed.chunks) {
    const hearing = seed.hearings.find((h) => h.id === chunk.hearingId);
    if (hearing && !matchesFilters(hearing, filters)) continue;
    const tokens = chunk.content.toLowerCase().split(/\W+/);
    const overlap = tokens.filter((t) => terms.has(t)).length;
    if (!overlap) continue;
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
      sourceKey: hearing?.sourceKey,
    });
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 12);
}

export function normalizeFilters(raw: SearchFilters): SearchFilters {
  const hearingType =
    raw.hearingType === "estimates" || raw.hearingType === "other" || raw.hearingType === "all"
      ? raw.hearingType
      : "all";
  return {
    committee: raw.committee?.trim() || undefined,
    person: raw.person?.trim() || undefined,
    hearingType,
    from: raw.from?.trim() || undefined,
    to: raw.to?.trim() || undefined,
  };
}

function hearingFilterSql(
  filters: SearchFilters,
  alias: string,
  startIndex: number,
): { sql: string; params: unknown[]; next: number } {
  const parts: string[] = [];
  const params: unknown[] = [];
  let i = startIndex;
  if (filters.hearingType === "estimates") {
    parts.push(`AND ${alias}.hearing_type = 'estimates'`);
  } else if (filters.hearingType === "other") {
    parts.push(`AND ${alias}.hearing_type <> 'estimates'`);
  }
  if (filters.from) {
    parts.push(`AND ${alias}.held_on >= $${i}::date`);
    params.push(filters.from);
    i += 1;
  }
  if (filters.to) {
    parts.push(`AND ${alias}.held_on <= $${i}::date`);
    params.push(filters.to);
    i += 1;
  }
  if (filters.committee) {
    parts.push(
      `AND EXISTS (
         SELECT 1 FROM committees cf
         WHERE cf.id = ${alias}.committee_id
           AND (cf.slug = $${i} OR cf.name ILIKE '%' || $${i} || '%')
       )`,
    );
    params.push(filters.committee);
    i += 1;
  }
  if (filters.person) {
    parts.push(
      `AND EXISTS (
         SELECT 1 FROM hearing_people hpf
         JOIN people pf ON pf.id = hpf.person_id
         WHERE hpf.hearing_id = ${alias}.id
           AND (pf.name ILIKE '%' || $${i} || '%' OR pf.slug ILIKE '%' || $${i} || '%')
       )`,
    );
    params.push(filters.person);
    i += 1;
  }
  return { sql: parts.join("\n"), params, next: i };
}

async function postgresKeyword(q: string, filters: SearchFilters): Promise<SearchHit[]> {
  const { sql: filterSql, params: filterParams, next } = hearingFilterSql(filters, "h", 2);
  const personParam = next;
  const hasInstruments = await query<{ n: number }>(
    `SELECT COUNT(*)::int AS n FROM information_schema.tables
     WHERE table_schema = 'public' AND table_name = 'instruments'`,
  ).then((rows) => (rows[0]?.n ?? 0) === 1).catch(() => false);
  const instrumentUnion = hasInstruments
    ? `
      UNION ALL

      SELECT 'instrument', i.id::text, i.slug, i.title,
             i.instrument_type,
             COALESCE(i.summary, i.title),
             ts_rank(
               to_tsvector('english', coalesce(i.title,'') || ' ' || coalesce(i.summary,'')),
               (SELECT tsq FROM q)
             ),
             i.source_key, NULL
      FROM instruments i
      WHERE (
        to_tsvector('english', coalesce(i.title,'') || ' ' || coalesce(i.summary,''))
          @@ (SELECT tsq FROM q)
        OR i.title ILIKE '%' || (SELECT raw FROM q) || '%'
        OR i.identifiers::text ILIKE '%' || (SELECT raw FROM q) || '%'
      )
    `
    : "";
  const rows = await query<{
    kind: string;
    id: string;
    slug: string | null;
    title: string;
    subtitle: string | null;
    excerpt: string;
    rank: number;
    source_key: string | null;
    hearing_type: string | null;
  }>(
    `
    WITH q AS (SELECT websearch_to_tsquery('english', $1) AS tsq, $1 AS raw)
    SELECT * FROM (
      SELECT 'hearing'::text AS kind, h.id::text, h.slug, h.title,
             c.name AS subtitle,
             COALESCE(h.summary, h.title) AS excerpt,
             ts_rank(
               to_tsvector('english', coalesce(h.title,'') || ' ' || coalesce(h.summary,'') || ' ' || coalesce(h.portfolio,'')),
               (SELECT tsq FROM q)
             ) AS rank,
             h.source_key, h.hearing_type
      FROM hearings h
      LEFT JOIN committees c ON c.id = h.committee_id
      WHERE (
        to_tsvector('english', coalesce(h.title,'') || ' ' || coalesce(h.summary,'') || ' ' || coalesce(h.portfolio,''))
          @@ (SELECT tsq FROM q)
        OR h.title ILIKE '%' || (SELECT raw FROM q) || '%'
        OR coalesce(h.summary,'') ILIKE '%' || (SELECT raw FROM q) || '%'
      )
      ${filterSql}

      UNION ALL

      SELECT 'person', p.id::text, p.slug, p.name,
             NULLIF(concat_ws(' · ', p.role_title, p.party), ''),
             COALESCE(p.bio, p.name),
             ts_rank(to_tsvector('english', coalesce(p.name,'') || ' ' || coalesce(p.bio,'') || ' ' || coalesce(p.organisation,'')), (SELECT tsq FROM q)),
             NULL, NULL
      FROM people p
      WHERE (
        to_tsvector('english', coalesce(p.name,'') || ' ' || coalesce(p.bio,'') || ' ' || coalesce(p.organisation,''))
          @@ (SELECT tsq FROM q)
        OR p.name ILIKE '%' || (SELECT raw FROM q) || '%'
      )
      ${
        filters.person
          ? `AND (p.name ILIKE '%' || $${personParam} || '%' OR p.slug ILIKE '%' || $${personParam} || '%')`
          : ""
      }

      UNION ALL

      SELECT 'document', d.id::text, h.slug, d.title,
             h.title,
             left(coalesce(d.content_text, d.title), 240),
             ts_rank(to_tsvector('english', coalesce(d.title,'') || ' ' || coalesce(d.content_text,'')), (SELECT tsq FROM q)),
             d.source_key, h.hearing_type
      FROM documents d
      JOIN hearings h ON h.id = d.hearing_id
      WHERE (
        to_tsvector('english', coalesce(d.title,'') || ' ' || coalesce(d.content_text,'')) @@ (SELECT tsq FROM q)
        OR d.title ILIKE '%' || (SELECT raw FROM q) || '%'
        OR coalesce(d.content_text,'') ILIKE '%' || (SELECT raw FROM q) || '%'
      )
      ${filterSql}

      ${instrumentUnion}

      UNION ALL

      SELECT 'chunk', ch.id::text, h.slug, h.title,
             ch.speaker_name,
             left(ch.content, 240),
             ts_rank(to_tsvector('english', ch.content), (SELECT tsq FROM q)),
             h.source_key, h.hearing_type
      FROM chunks ch
      JOIN hearings h ON h.id = ch.hearing_id
      WHERE (
        to_tsvector('english', ch.content) @@ (SELECT tsq FROM q)
        OR ch.content ILIKE '%' || (SELECT raw FROM q) || '%'
      )
      ${filterSql}
    ) x
    ORDER BY rank DESC
    LIMIT 50
    `,
    filters.person ? [q, ...filterParams, filters.person] : [q, ...filterParams],
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
        : row.kind === "instrument" && row.slug
          ? row.subtitle === "bill" || row.subtitle === "act"
            ? `/laws/${row.slug}`
            : `/accountability/instruments/${row.slug}`
        : row.kind === "chunk" && row.slug
          ? `/hearings/${row.slug}#chunk-${row.id}`
          : row.slug
            ? `/hearings/${row.slug}`
            : "/search",
    score: Number(row.rank) || 1,
    mode: "keyword" as const,
    sourceKey: row.source_key ?? undefined,
    hearingType: row.hearing_type ?? undefined,
  }));
}

async function postgresSemantic(q: string, filters: SearchFilters): Promise<SearchHit[]> {
  const { sql: filterSql, params: filterParams } = hearingFilterSql(filters, "h", 2);
  const embedded = await query<{ n: number }>(
    `SELECT COUNT(*)::int AS n FROM chunks WHERE embedding IS NOT NULL`,
  );
  if ((embedded[0]?.n ?? 0) > 0) {
    const vec = vectorLiteral(hashEmbed(q));
    const rows = await query<{
      id: string;
      slug: string;
      title: string;
      speaker_name: string | null;
      content: string;
      dist: number;
      source_key: string | null;
      hearing_type: string | null;
    }>(
      `
      SELECT ch.id::text, h.slug, h.title, ch.speaker_name, left(ch.content, 240) AS content,
             (ch.embedding <=> $1::vector) AS dist,
             h.source_key, h.hearing_type
      FROM chunks ch
      JOIN hearings h ON h.id = ch.hearing_id
      WHERE ch.embedding IS NOT NULL
      ${filterSql}
      ORDER BY ch.embedding <=> $1::vector
      LIMIT 16
      `,
      [vec, ...filterParams],
    );
    return rows.map((row) => ({
      kind: "chunk" as const,
      id: row.id,
      slug: row.slug,
      title: row.title,
      subtitle: row.speaker_name ?? "vector",
      excerpt: row.content,
      href: `/hearings/${row.slug}#chunk-${row.id}`,
      score: 1 / (1 + Number(row.dist || 0)),
      mode: "semantic" as const,
      sourceKey: row.source_key ?? undefined,
      hearingType: row.hearing_type ?? undefined,
    }));
  }

  const rows = await query<{
    id: string;
    slug: string;
    title: string;
    speaker_name: string | null;
    content: string;
    source_key: string | null;
    hearing_type: string | null;
  }>(
    `
    SELECT ch.id::text, h.slug, h.title, ch.speaker_name, left(ch.content, 240) AS content,
           h.source_key, h.hearing_type
    FROM chunks ch
    JOIN hearings h ON h.id = ch.hearing_id
    WHERE ch.content ILIKE '%' || $1 || '%'
    ${filterSql}
    LIMIT 16
    `,
    [q, ...filterParams],
  );
  return rows.map((row, idx) => ({
    kind: "chunk" as const,
    id: row.id,
    slug: row.slug,
    title: row.title,
    subtitle: row.speaker_name ?? "lexical-semantic",
    excerpt: row.content,
    href: `/hearings/${row.slug}#chunk-${row.id}`,
    score: 1 / (idx + 1),
    mode: "semantic" as const,
    sourceKey: row.source_key ?? undefined,
    hearingType: row.hearing_type ?? undefined,
  }));
}

export async function searchCatalog(
  q: string,
  mode: SearchMode,
  rawFilters: SearchFilters = {},
): Promise<{
  hits: SearchHit[];
  source: "postgres" | "fixture";
  mode: SearchMode;
  filters: SearchFilters;
}> {
  const trimmed = q.trim();
  const filters = normalizeFilters(rawFilters);
  if (!trimmed) {
    return { hits: [], source: (await loadCatalog()).source, mode, filters };
  }

  const live = await postgresAvailable();
  let keyword: SearchHit[] = [];
  let semantic: SearchHit[] = [];

  if (live) {
    try {
      if (mode !== "semantic") keyword = await postgresKeyword(trimmed, filters);
      if (mode !== "keyword") semantic = await postgresSemantic(trimmed, filters);
      return { hits: mergeHits(keyword, semantic, mode), source: "postgres", mode, filters };
    } catch {
      /* fixture fallback */
    }
  }

  if (mode !== "semantic") keyword = lexicalHits(trimmed, filters);
  if (mode !== "keyword") semantic = semanticPlaceholder(trimmed, filters);
  return { hits: mergeHits(keyword, semantic, mode), source: "fixture", mode, filters };
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

export function filtersFromSearchParams(params: URLSearchParams | Record<string, string | undefined>): SearchFilters {
  const get = (key: string) =>
    params instanceof URLSearchParams ? (params.get(key) ?? undefined) : params[key];
  return normalizeFilters({
    committee: get("committee"),
    person: get("person"),
    hearingType: get("type") as SearchFilters["hearingType"],
    from: get("from"),
    to: get("to"),
  });
}
