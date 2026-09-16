import { postgresAvailable, query } from "./db";
import type { NeededHint } from "./accountability-meta";

export type LawSource = "postgres" | "fixture";

export type LawIdentifiers = {
  frlId?: string | null;
  series?: string | null;
  year?: number | null;
  number?: number | null;
  collection?: string | null;
};

export type LawRow = {
  slug: string;
  title: string;
  instrumentType: "bill" | "act" | string;
  status: string | null;
  announcedOn: string | null;
  commencedOn: string | null;
  endedOn: string | null;
  source: string | null;
  sourceUrl: string | null;
  summary: string | null;
  agencySlug: string | null;
  agencyName: string | null;
  identifiers: LawIdentifiers;
};

export type DivisionRow = {
  slug: string | null;
  title: string;
  house: string | null;
  dividedOn: string | null;
  number: number | null;
  ayes: number | null;
  noes: number | null;
  abstentions: number | null;
  source: string | null;
  sourceUrl: string | null;
  instrumentSlug: string | null;
  instrumentTitle: string | null;
  namedVotes: number;
  resolvedVotes: number;
};

export type DivisionVoteRow = {
  personName: string;
  personSlug: string | null;
  vote: string;
  party: string | null;
  electorate: string | null;
  divisionTitle: string;
  divisionSlug: string | null;
  dividedOn: string | null;
  house: string | null;
  sourceUrl: string | null;
  instrumentSlug: string | null;
  instrumentTitle: string | null;
};

export type JudgmentRow = {
  slug: string | null;
  title: string;
  publishedOn: string | null;
  source: string | null;
  sourceUrl: string | null;
  summary: string | null;
  citation: string | null;
  court: string | null;
  linkKind: string;
  notes: string | null;
};

export type LinkedScrutiny = {
  kind: string;
  title: string;
  href: string | null;
  on: string | null;
  source: string | null;
};

export type LawsPayload<T> = {
  source: LawSource;
  ready: boolean;
  needed: NeededHint;
  rows: T[];
};

function dateOnly(value: unknown): string | null {
  return value ? String(value).slice(0, 10) : null;
}

function needed(note: string, extra: Partial<NeededHint> = {}): NeededHint {
  return {
    note,
    apply: "make db-apply",
    sources: extra.sources ?? ["legislation", "theyvoteforyou", "judgments"],
    tables: extra.tables ?? ["instruments", "divisions", "division_votes", "scrutiny_items"],
  };
}

const EMPTY_HINT = needed(
  "Laws need sourced Bills/Acts from the Federal Register of Legislation. Votes come from They Vote For You. Judgments are a fixture MVP. Fixture mode has hearings only — no invented Acts, votes, or holdings.",
);

async function tableExists(name: string): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = $1
    `,
    [name],
  );
  return (rows[0]?.n ?? 0) === 1;
}

function emptyPayload<T>(source: LawSource, hint: NeededHint): LawsPayload<T> {
  return { source, ready: false, needed: hint, rows: [] };
}

function parseIdentifiers(raw: unknown): LawIdentifiers {
  const obj = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const year = obj.year != null ? Number(obj.year) : null;
  const number = obj.number != null ? Number(obj.number) : null;
  return {
    frlId: (obj.frl_id as string | null) ?? null,
    series: (obj.series as string | null) ?? null,
    year: Number.isFinite(year) ? year : null,
    number: Number.isFinite(number) ? number : null,
    collection: (obj.collection as string | null) ?? null,
  };
}

export function isLawType(type: string | null | undefined): boolean {
  return type === "bill" || type === "act";
}

export function lawHref(slug: string, type?: string | null): string {
  return isLawType(type) ? `/laws/${slug}` : `/accountability/instruments/${slug}`;
}

export async function loadLaws(q: string | null, type: string | null = null): Promise<LawsPayload<LawRow>> {
  if (!(await postgresAvailable())) {
    return emptyPayload("fixture", EMPTY_HINT);
  }
  try {
    if (!(await tableExists("instruments"))) {
      return emptyPayload(
        "postgres",
        needed("Accountability tables are not on this volume yet. Run make db-apply, then ingest --source legislation."),
      );
    }
    const rows = await query<Record<string, unknown>>(
      `
      SELECT i.slug, i.title, i.instrument_type, i.status,
             i.announced_on, i.commenced_on, i.ended_on,
             i.source, i.source_url, i.summary, i.identifiers,
             a.slug AS agency_slug, a.name AS agency_name
      FROM instruments i
      LEFT JOIN agencies a ON a.id = i.agency_id
      WHERE i.instrument_type IN ('bill', 'act')
        AND ($1::text IS NULL OR i.title ILIKE '%' || $1 || '%'
             OR i.slug ILIKE '%' || $1 || '%'
             OR i.identifiers::text ILIKE '%' || $1 || '%')
        AND ($2::text IS NULL OR i.instrument_type = $2)
      ORDER BY COALESCE(i.announced_on, i.commenced_on) DESC NULLS LAST, i.title
      LIMIT 80
      `,
      [q?.trim() || null, type === "bill" || type === "act" ? type : null],
    );
    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      rows: rows.map(mapLaw),
    };
  } catch {
    return emptyPayload(
      "postgres",
      needed("The laws query failed — usually a missing 012_laws.sql apply. No conclusion is inferred."),
    );
  }
}

export async function loadLaw(slug: string): Promise<LawsPayload<LawRow>> {
  if (!(await postgresAvailable())) {
    return emptyPayload("fixture", EMPTY_HINT);
  }
  try {
    if (!(await tableExists("instruments"))) {
      return emptyPayload(
        "postgres",
        needed("Accountability tables are not on this volume yet. Run make db-apply, then ingest --source legislation."),
      );
    }
    const rows = await query<Record<string, unknown>>(
      `
      SELECT i.slug, i.title, i.instrument_type, i.status,
             i.announced_on, i.commenced_on, i.ended_on,
             i.source, i.source_url, i.summary, i.identifiers,
             a.slug AS agency_slug, a.name AS agency_name
      FROM instruments i
      LEFT JOIN agencies a ON a.id = i.agency_id
      WHERE i.slug = $1 AND i.instrument_type IN ('bill', 'act')
      LIMIT 1
      `,
      [slug],
    );
    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      rows: rows.map(mapLaw),
    };
  } catch {
    return emptyPayload(
      "postgres",
      needed("The law dossier query failed — usually a missing 012_laws.sql apply."),
    );
  }
}

function mapLaw(r: Record<string, unknown>): LawRow {
  return {
    slug: String(r.slug),
    title: String(r.title),
    instrumentType: String(r.instrument_type),
    status: (r.status as string | null) ?? null,
    announcedOn: dateOnly(r.announced_on),
    commencedOn: dateOnly(r.commenced_on),
    endedOn: dateOnly(r.ended_on),
    source: (r.source as string | null) ?? null,
    sourceUrl: (r.source_url as string | null) ?? null,
    summary: (r.summary as string | null) ?? null,
    agencySlug: (r.agency_slug as string | null) ?? null,
    agencyName: (r.agency_name as string | null) ?? null,
    identifiers: parseIdentifiers(r.identifiers),
  };
}

export async function loadDivisionsForInstrument(slug: string): Promise<LawsPayload<DivisionRow>> {
  return loadDivisions({ instrument: slug });
}

export async function loadDivisions(opts: {
  instrument?: string | null;
  person?: string | null;
} = {}): Promise<LawsPayload<DivisionRow>> {
  if (!(await postgresAvailable())) {
    return emptyPayload("fixture", EMPTY_HINT);
  }
  try {
    if (!(await tableExists("divisions"))) {
      return emptyPayload(
        "postgres",
        needed(
          "Division tables are not on this volume yet. Run make db-apply (012_laws.sql) then ingest --source theyvoteforyou.",
          { sources: ["theyvoteforyou"], tables: ["divisions", "division_votes"] },
        ),
      );
    }
    const rows = await query<Record<string, unknown>>(
      `
      SELECT d.slug, d.title, d.house, d.divided_on, d.number,
             d.ayes, d.noes, d.abstentions, d.source, d.source_url,
             i.slug AS instrument_slug, i.title AS instrument_title,
             COUNT(dv.id)::int AS named_votes,
             COUNT(dv.person_id)::int AS resolved_votes
      FROM divisions d
      LEFT JOIN instruments i ON i.id = d.instrument_id
      LEFT JOIN division_votes dv ON dv.division_id = d.id
      WHERE ($1::text IS NULL OR i.slug = $1)
        AND ($2::text IS NULL OR EXISTS (
              SELECT 1 FROM division_votes x
              JOIN people p ON p.id = x.person_id
              WHERE x.division_id = d.id AND p.slug = $2
            ))
      GROUP BY d.id, i.slug, i.title
      ORDER BY d.divided_on DESC NULLS LAST
      LIMIT 40
      `,
      [opts.instrument ?? null, opts.person ?? null],
    );
    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      rows: rows.map((r) => ({
        slug: (r.slug as string | null) ?? null,
        title: String(r.title),
        house: (r.house as string | null) ?? null,
        dividedOn: dateOnly(r.divided_on),
        number: r.number != null ? Number(r.number) : null,
        ayes: r.ayes != null ? Number(r.ayes) : null,
        noes: r.noes != null ? Number(r.noes) : null,
        abstentions: r.abstentions != null ? Number(r.abstentions) : null,
        source: (r.source as string | null) ?? null,
        sourceUrl: (r.source_url as string | null) ?? null,
        instrumentSlug: (r.instrument_slug as string | null) ?? null,
        instrumentTitle: (r.instrument_title as string | null) ?? null,
        namedVotes: Number(r.named_votes ?? 0),
        resolvedVotes: Number(r.resolved_votes ?? 0),
      })),
    };
  } catch {
    return emptyPayload(
      "postgres",
      needed("Divisions query failed. Apply 012_laws.sql. No vote is inferred from silence."),
    );
  }
}

export async function loadVotesForDivision(divisionSlug: string): Promise<DivisionVoteRow[]> {
  return (await loadVotes({ division: divisionSlug })).rows;
}

export async function loadVotes(opts: {
  instrument?: string | null;
  person?: string | null;
  division?: string | null;
} = {}): Promise<LawsPayload<DivisionVoteRow>> {
  if (!(await postgresAvailable())) {
    return emptyPayload("fixture", EMPTY_HINT);
  }
  try {
    if (!(await tableExists("division_votes"))) {
      return emptyPayload("postgres", EMPTY_HINT);
    }
    const rows = await query<Record<string, unknown>>(
      `
      SELECT dv.person_name, p.slug AS person_slug, dv.vote, dv.party, dv.electorate,
             d.title AS division_title, d.slug AS division_slug, d.divided_on, d.house,
             d.source_url, i.slug AS instrument_slug, i.title AS instrument_title
      FROM division_votes dv
      JOIN divisions d ON d.id = dv.division_id
      LEFT JOIN people p ON p.id = dv.person_id
      LEFT JOIN instruments i ON i.id = d.instrument_id
      WHERE ($1::text IS NULL OR i.slug = $1)
        AND ($2::text IS NULL OR p.slug = $2)
        AND ($3::text IS NULL OR d.slug = $3)
      ORDER BY d.divided_on DESC NULLS LAST, dv.vote, dv.person_name
      LIMIT 200
      `,
      [opts.instrument ?? null, opts.person ?? null, opts.division ?? null],
    );
    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      rows: rows.map((r) => ({
        personName: String(r.person_name),
        personSlug: (r.person_slug as string | null) ?? null,
        vote: String(r.vote),
        party: (r.party as string | null) ?? null,
        electorate: (r.electorate as string | null) ?? null,
        divisionTitle: String(r.division_title),
        divisionSlug: (r.division_slug as string | null) ?? null,
        dividedOn: dateOnly(r.divided_on),
        house: (r.house as string | null) ?? null,
        sourceUrl: (r.source_url as string | null) ?? null,
        instrumentSlug: (r.instrument_slug as string | null) ?? null,
        instrumentTitle: (r.instrument_title as string | null) ?? null,
      })),
    };
  } catch {
    return emptyPayload("postgres", EMPTY_HINT);
  }
}

export async function loadJudgmentsForInstrument(slug: string): Promise<LawsPayload<JudgmentRow>> {
  if (!(await postgresAvailable())) {
    return emptyPayload("fixture", EMPTY_HINT);
  }
  try {
    if (!(await tableExists("instrument_links"))) {
      return emptyPayload("postgres", EMPTY_HINT);
    }
    const rows = await query<Record<string, unknown>>(
      `
      SELECT s.slug, s.title, s.published_on, s.source, s.source_url, s.summary,
             s.identifiers, il.link_kind, il.notes
      FROM instrument_links il
      JOIN instruments i ON i.id = il.instrument_id
      JOIN scrutiny_items s ON s.id = il.scrutiny_item_id
      WHERE i.slug = $1
        AND il.link_kind IN ('construes', 'invalidates', 'upholds')
        AND s.item_type = 'judgment'
      ORDER BY s.published_on DESC NULLS LAST
      LIMIT 40
      `,
      [slug],
    );
    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      rows: rows.map((r) => {
        const ids = (r.identifiers && typeof r.identifiers === "object"
          ? r.identifiers
          : {}) as Record<string, unknown>;
        return {
          slug: (r.slug as string | null) ?? null,
          title: String(r.title),
          publishedOn: dateOnly(r.published_on),
          source: (r.source as string | null) ?? null,
          sourceUrl: (r.source_url as string | null) ?? null,
          summary: (r.summary as string | null) ?? null,
          citation: (ids.citation as string | null) ?? null,
          court: (ids.court as string | null) ?? null,
          linkKind: String(r.link_kind),
          notes: (r.notes as string | null) ?? null,
        };
      }),
    };
  } catch {
    return emptyPayload(
      "postgres",
      needed("Precedent links need 013_precedent.sql and ingest --source judgments."),
    );
  }
}

export async function loadLinkedScrutiny(slug: string): Promise<LinkedScrutiny[]> {
  if (!(await postgresAvailable())) return [];
  try {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT s.item_type, s.title, s.source_url, s.published_on, s.source,
             h.slug AS hearing_slug
      FROM instrument_links il
      JOIN instruments i ON i.id = il.instrument_id
      LEFT JOIN scrutiny_items s ON s.id = il.scrutiny_item_id
      LEFT JOIN hearings h ON h.id = il.hearing_id
      WHERE i.slug = $1
        AND il.link_kind IN ('tested_in', 'mentioned', 'funded_by')
      ORDER BY COALESCE(s.published_on, h.held_on) DESC NULLS LAST
      LIMIT 20
      `,
      [slug],
    );
    return rows
      .filter((r) => r.title || r.hearing_slug)
      .map((r) => ({
        kind: String(r.item_type || (r.hearing_slug ? "hearing" : "link")),
        title: String(r.title || r.hearing_slug || "linked record"),
        href: (r.source_url as string | null)
          || (r.hearing_slug ? `/hearings/${r.hearing_slug}` : null),
        on: dateOnly(r.published_on),
        source: (r.source as string | null) ?? null,
      }));
  } catch {
    return [];
  }
}

export function statusTimeline(row: LawRow): { label: string; on: string | null }[] {
  const steps = [
    { label: "Introduced / as made", on: row.announcedOn },
    { label: "Commenced / in force", on: row.commencedOn },
    { label: "Ended / repealed", on: row.endedOn },
  ];
  if (row.status) {
    steps.unshift({ label: `Status · ${row.status}`, on: row.commencedOn ?? row.announcedOn });
  }
  return steps;
}
