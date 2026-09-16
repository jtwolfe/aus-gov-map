import { postgresAvailable, query } from "./db";
import type { NeededHint } from "./accountability-meta";

export type { NeededHint } from "./accountability-meta";
export { LENSES } from "./accountability-meta";

export type AccountabilitySource = "postgres" | "fixture";

export type RoleAtDateRow = {
  personSlug: string | null;
  personName: string | null;
  roleTitle: string | null;
  roleType: string;
  portfolio: string | null;
  organisation: string | null;
  agencySlug: string | null;
  agencyName: string | null;
  startDate: string | null;
  endDate: string | null;
  source: string;
  sourceUrl: string | null;
};

export type PromiseReceiptRow = {
  claimType: string;
  textSpan: string;
  madeOn: string | null;
  speakerName: string | null;
  personSlug: string | null;
  personName: string | null;
  hearingSlug: string | null;
  hearingTitle: string | null;
  instrumentTitle: string | null;
  instrumentType: string | null;
  outcomeSignal: string | null;
  outcomeOn: string | null;
};

export type QonDebtRow = {
  portfolio: string;
  agencySlug: string | null;
  agencyName: string | null;
  responsibleOfficialSlug: string | null;
  responsibleOfficialName: string | null;
  responsibleOfficialRole: string | null;
  openishCount: number;
  overdueCount: number;
  answeredCount: number;
  refusedCount: number;
  qonCount: number;
  latestDue: string | null;
};

export type AgencyRow = {
  slug: string;
  name: string;
  portfolio: string | null;
  source: string | null;
  sourceUrl: string | null;
  officialSlug: string | null;
  officialName: string | null;
  officialRole: string | null;
  qonCount: number;
};

export type ChainRow = {
  slug: string;
  title: string;
  instrumentType: string;
  agencyName: string | null;
  hasAccountableMinister: boolean;
  hasResponsibleOfficial: boolean;
  chainIncomplete: boolean;
  sourceUrl: string | null;
};

export type InstrumentRow = {
  slug: string;
  title: string;
  instrumentType: string;
  agencySlug: string | null;
  agencyName: string | null;
  announcedOn: string | null;
  amountAud: string | null;
  source: string | null;
  sourceUrl: string | null;
  status?: string | null;
  commencedOn?: string | null;
  endedOn?: string | null;
  summary?: string | null;
};

export type AccountabilityPayload<T> = {
  source: AccountabilitySource;
  ready: boolean;
  needed: NeededHint;
  rows: T[];
  on?: string | null;
  query?: string | null;
};

const FOUNDATION_TABLES = [
  "agencies",
  "roles",
  "person_roles",
  "instruments",
  "instrument_links",
  "scrutiny_items",
  "qons",
  "claims",
  "outcomes",
] as const;

function dateOnly(value: unknown): string | null {
  return value ? String(value).slice(0, 10) : null;
}

function needed(note: string, extra: Partial<NeededHint> = {}): NeededHint {
  return {
    note,
    apply: "make db-apply",
    sources: extra.sources,
    tables: extra.tables,
  };
}

async function foundationTablesExist(): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name = ANY($1)
    `,
    [FOUNDATION_TABLES],
  );
  return (rows[0]?.n ?? 0) >= FOUNDATION_TABLES.length;
}

async function viewExists(name: string): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.views
    WHERE table_schema = 'public' AND table_name = $1
    `,
    [name],
  );
  return (rows[0]?.n ?? 0) === 1;
}

async function withFoundation<T>(
  emptyNeeded: NeededHint,
  load: () => Promise<T[]>,
  extra: { on?: string | null; query?: string | null } = {},
): Promise<AccountabilityPayload<T>> {
  if (!(await postgresAvailable())) {
    return {
      source: "fixture",
      ready: false,
      needed: needed(
        "Postgres is not reachable. Start it with make db-up, apply 007_accountability.sql via make db-apply, then run the listed ingest sources. The bundled fixture has hearings only — no invented tenures, QoNs, or instruments.",
        emptyNeeded,
      ),
      rows: [],
      ...extra,
    };
  }
  try {
    if (!(await foundationTablesExist())) {
      return {
        source: "postgres",
        ready: false,
        needed: needed(
          "Accountability tables are not on this volume yet. Run make db-apply (007_accountability.sql). Stage 1 hearings stay as they are.",
          emptyNeeded,
        ),
        rows: [],
        ...extra,
      };
    }
    const rows = await load();
    return {
      source: "postgres",
      ready: true,
      needed: emptyNeeded,
      rows,
      ...extra,
    };
  } catch {
    return {
      source: "postgres",
      ready: false,
      needed: needed(
        "The query failed — usually a missing view. Run make db-apply and retry. No conclusion is inferred from the error.",
        emptyNeeded,
      ),
      rows: [],
      ...extra,
    };
  }
}

export async function loadRoleAtDate(on: string | null, person?: string | null, portfolio?: string | null) {
  const hint = needed(
    "Role-at-date needs sourced occupancies in person_roles. Handbook covers parliamentarians; APS secretaries and agency heads come from aps_leaders (directory.gov.au / official executive pages). Stage 1 hearing appearances are not tenures.",
    { sources: ["handbook", "aps_leaders"], tables: ["person_roles", "roles", "agencies"] },
  );
  return withFoundation<RoleAtDateRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT p.slug AS person_slug, p.name AS person_name,
             COALESCE(r.title, pr.organisation, pr.role_type) AS role_title,
             pr.role_type, pr.portfolio, pr.organisation,
             a.slug AS agency_slug, a.name AS agency_name,
             pr.start_date, pr.end_date, pr.source, pr.source_url
      FROM person_roles pr
      JOIN people p ON p.id = pr.person_id
      LEFT JOIN roles r ON r.id = pr.role_id
      LEFT JOIN agencies a ON a.id = COALESCE(pr.agency_id, r.agency_id)
      WHERE ($1::date IS NULL OR pr.start_date IS NULL OR pr.start_date <= $1::date)
        AND ($1::date IS NULL OR pr.end_date IS NULL OR pr.end_date >= $1::date)
        AND ($2::text IS NULL OR p.name ILIKE '%' || $2 || '%' OR p.slug ILIKE '%' || $2 || '%')
        AND ($3::text IS NULL OR pr.portfolio ILIKE '%' || $3 || '%'
             OR r.portfolio ILIKE '%' || $3 || '%'
             OR a.slug ILIKE '%' || $3 || '%'
             OR a.name ILIKE '%' || $3 || '%')
      ORDER BY CASE pr.role_type
                 WHEN 'secretary' THEN 0
                 WHEN 'agency_head' THEN 1
                 WHEN 'deputy' THEN 2
                 WHEN 'minister' THEN 3
                 ELSE 4
               END,
               pr.portfolio NULLS LAST, role_title, p.name
      LIMIT 80
      `,
      [on || null, person?.trim() || null, portfolio?.trim() || null],
    );
    return rows.map((r) => ({
      personSlug: (r.person_slug as string | null) ?? null,
      personName: (r.person_name as string | null) ?? null,
      roleTitle: (r.role_title as string | null) ?? null,
      roleType: String(r.role_type),
      portfolio: (r.portfolio as string | null) ?? null,
      organisation: (r.organisation as string | null) ?? null,
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      startDate: dateOnly(r.start_date),
      endDate: dateOnly(r.end_date),
      source: String(r.source),
      sourceUrl: (r.source_url as string | null) ?? null,
    }));
  }, { on });
}

export async function loadPromiseReceipt() {
  const hint = needed(
    "Promise → receipt needs claims (spans from Hansard chunks) linked to instruments, then sourced outcomes. Hearings already exist; claims and instruments do not until those adapters write rows.",
    { sources: ["estimates", "budget_measure", "qon"], tables: ["claims", "instruments", "outcomes"] },
  );
  return withFoundation<PromiseReceiptRow>(hint, async () => {
    const sql = (await viewExists("v_accountability_promise_receipt"))
      ? `
        SELECT claim_type, text_span, made_on, speaker_name, person_slug, person_name,
               hearing_slug, hearing_title, instrument_title, instrument_type,
               signal AS outcome_signal, outcome_on
        FROM v_accountability_promise_receipt
        ORDER BY made_on DESC NULLS LAST
        LIMIT 80
      `
      : `
        SELECT c.claim_type, c.text_span, c.made_on, c.speaker_name,
               p.slug AS person_slug, p.name AS person_name,
               h.slug AS hearing_slug, h.title AS hearing_title,
               i.title AS instrument_title, i.instrument_type,
               o.signal AS outcome_signal, o.occurred_on AS outcome_on
        FROM claims c
        LEFT JOIN people p ON p.id = c.person_id
        LEFT JOIN hearings h ON h.id = c.hearing_id
        LEFT JOIN instruments i ON i.id = c.instrument_id
        LEFT JOIN outcomes o ON o.instrument_id = i.id
        WHERE c.claim_type IN ('promise', 'assurance', 'taken_on_notice')
        ORDER BY c.made_on DESC NULLS LAST
        LIMIT 80
      `;
    const rows = await query<Record<string, unknown>>(sql);
    return rows.map((r) => ({
      claimType: String(r.claim_type),
      textSpan: String(r.text_span),
      madeOn: dateOnly(r.made_on),
      speakerName: (r.speaker_name as string | null) ?? null,
      personSlug: (r.person_slug as string | null) ?? null,
      personName: (r.person_name as string | null) ?? null,
      hearingSlug: (r.hearing_slug as string | null) ?? null,
      hearingTitle: (r.hearing_title as string | null) ?? null,
      instrumentTitle: (r.instrument_title as string | null) ?? null,
      instrumentType: (r.instrument_type as string | null) ?? null,
      outcomeSignal: (r.outcome_signal as string | null) ?? null,
      outcomeOn: dateOnly(r.outcome_on),
    }));
  });
}

export async function loadQonDebt() {
  const hint = needed(
    "QoN debt counts open and overdue questions by portfolio and answering agency. Run qon (EQON / fixtures/live/qon). Taken-on-notice lines in Hansard are not QoNs until they are promoted. Responsible officials appear after aps_leaders writes person_roles.",
    { sources: ["qon", "aps_leaders", "agencies"], tables: ["qons", "agencies", "person_roles"] },
  );
  return withFoundation<QonDebtRow>(hint, async () => {
    const sql = (await viewExists("v_accountability_qon_debt"))
      ? `
        SELECT portfolio, agency_slug, agency_name,
               responsible_official_slug, responsible_official_name, responsible_official_role,
               openish_count, overdue_count, answered_count, refused_count, qon_count, latest_due
        FROM v_accountability_qon_debt
        ORDER BY overdue_count DESC, openish_count DESC, portfolio
      `
      : `
        SELECT COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
               a.slug AS agency_slug, a.name AS agency_name,
               NULL::text AS responsible_official_slug,
               NULL::text AS responsible_official_name,
               NULL::text AS responsible_official_role,
               COUNT(*) FILTER (WHERE q.status IN ('open', 'overdue', 'unknown'))::int AS openish_count,
               COUNT(*) FILTER (WHERE q.status = 'overdue'
                 OR (q.status = 'open' AND q.due_on IS NOT NULL AND q.due_on < CURRENT_DATE))::int AS overdue_count,
               COUNT(*) FILTER (WHERE q.status = 'answered')::int AS answered_count,
               COUNT(*) FILTER (WHERE q.status = 'refused')::int AS refused_count,
               COUNT(*)::int AS qon_count,
               MAX(q.due_on) AS latest_due
        FROM qons q
        LEFT JOIN agencies a ON a.id = q.answering_agency_id
        GROUP BY q.portfolio, a.slug, a.name
        ORDER BY overdue_count DESC, openish_count DESC
      `;
    const rows = await query<Record<string, unknown>>(sql).catch(async () =>
      query<Record<string, unknown>>(`
        SELECT COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
               a.slug AS agency_slug, a.name AS agency_name,
               NULL::text AS responsible_official_slug,
               NULL::text AS responsible_official_name,
               NULL::text AS responsible_official_role,
               COUNT(*) FILTER (WHERE q.status IN ('open', 'overdue', 'unknown'))::int AS openish_count,
               COUNT(*) FILTER (WHERE q.status = 'overdue'
                 OR (q.status = 'open' AND q.due_on IS NOT NULL AND q.due_on < CURRENT_DATE))::int AS overdue_count,
               COUNT(*) FILTER (WHERE q.status = 'answered')::int AS answered_count,
               COUNT(*) FILTER (WHERE q.status = 'refused')::int AS refused_count,
               COUNT(*)::int AS qon_count,
               MAX(q.due_on) AS latest_due
        FROM qons q
        LEFT JOIN agencies a ON a.id = q.answering_agency_id
        GROUP BY q.portfolio, a.slug, a.name
        ORDER BY overdue_count DESC, openish_count DESC
      `),
    );
    return rows.map((r) => ({
      portfolio: String(r.portfolio),
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      responsibleOfficialSlug: (r.responsible_official_slug as string | null) ?? null,
      responsibleOfficialName: (r.responsible_official_name as string | null) ?? null,
      responsibleOfficialRole: (r.responsible_official_role as string | null) ?? null,
      openishCount: Number(r.openish_count ?? 0),
      overdueCount: Number(r.overdue_count ?? 0),
      answeredCount: Number(r.answered_count ?? 0),
      refusedCount: Number(r.refused_count ?? 0),
      qonCount: Number(r.qon_count ?? 0),
      latestDue: dateOnly(r.latest_due),
    }));
  });
}

export async function loadAgencies() {
  const hint = needed(
    "Agency pages list official-name stubs (agencies ingest) and current secretaries / agency heads after aps_leaders writes person_roles. Empty is correct until those sources run.",
    { sources: ["agencies", "aps_leaders"], tables: ["agencies", "person_roles"] },
  );
  return withFoundation<AgencyRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(`
      SELECT a.slug, a.name, a.portfolio, a.source, a.source_url,
             head.person_slug, head.person_name, head.role_type,
             (SELECT COUNT(*)::int FROM qons q WHERE q.answering_agency_id = a.id) AS qon_count
      FROM agencies a
      LEFT JOIN LATERAL (
        SELECT p.slug AS person_slug, p.name AS person_name, pr.role_type
        FROM person_roles pr
        JOIN people p ON p.id = pr.person_id
        WHERE pr.agency_id = a.id
          AND pr.role_type IN ('secretary', 'agency_head')
          AND (pr.end_date IS NULL OR pr.end_date >= CURRENT_DATE)
        ORDER BY CASE pr.role_type WHEN 'secretary' THEN 0 ELSE 1 END,
                 pr.start_date DESC NULLS LAST
        LIMIT 1
      ) head ON TRUE
      ORDER BY a.name
      LIMIT 80
    `);
    return rows.map((r) => ({
      slug: String(r.slug),
      name: String(r.name),
      portfolio: (r.portfolio as string | null) ?? null,
      source: (r.source as string | null) ?? null,
      sourceUrl: (r.source_url as string | null) ?? null,
      officialSlug: (r.person_slug as string | null) ?? null,
      officialName: (r.person_name as string | null) ?? null,
      officialRole: (r.role_type as string | null) ?? null,
      qonCount: Number(r.qon_count ?? 0),
    }));
  });
}

export async function loadAgency(slug: string) {
  const hint = needed(
    "An agency page needs a row in agencies and, for a responsible official, an open person_roles occupancy from aps_leaders.",
    { sources: ["agencies", "aps_leaders", "qon"], tables: ["agencies", "person_roles", "qons"] },
  );
  const payload = await withFoundation<AgencyRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT a.slug, a.name, a.portfolio, a.source, a.source_url,
             head.person_slug, head.person_name, head.role_type,
             (SELECT COUNT(*)::int FROM qons q WHERE q.answering_agency_id = a.id) AS qon_count
      FROM agencies a
      LEFT JOIN LATERAL (
        SELECT p.slug AS person_slug, p.name AS person_name, pr.role_type
        FROM person_roles pr
        JOIN people p ON p.id = pr.person_id
        WHERE pr.agency_id = a.id
          AND pr.role_type IN ('secretary', 'agency_head', 'deputy')
          AND (pr.end_date IS NULL OR pr.end_date >= CURRENT_DATE)
        ORDER BY CASE pr.role_type
                   WHEN 'secretary' THEN 0
                   WHEN 'agency_head' THEN 1
                   ELSE 2
                 END,
                 pr.start_date DESC NULLS LAST
        LIMIT 1
      ) head ON TRUE
      WHERE a.slug = $1
      `,
      [slug],
    );
    return rows.map((r) => ({
      slug: String(r.slug),
      name: String(r.name),
      portfolio: (r.portfolio as string | null) ?? null,
      source: (r.source as string | null) ?? null,
      sourceUrl: (r.source_url as string | null) ?? null,
      officialSlug: (r.person_slug as string | null) ?? null,
      officialName: (r.person_name as string | null) ?? null,
      officialRole: (r.role_type as string | null) ?? null,
      qonCount: Number(r.qon_count ?? 0),
    }));
  });
  return payload;
}

export async function loadChainCompleteness() {
  const hint = needed(
    "Chain completeness lists instruments that lack a sourced ACCOUNTABLE_FOR (minister) and/or RESPONSIBLE_OFFICIAL (public service) link. Gaps are missing edges, not findings. Fill instruments via budget_measure / austender, then link people.",
    {
      sources: ["budget_measure", "austender", "handbook"],
      tables: ["instruments", "instrument_links", "people"],
    },
  );
  return withFoundation<ChainRow>(hint, async () => {
    const sql = (await viewExists("v_accountability_chain_completeness"))
      ? `
        SELECT slug, title, instrument_type, agency_name,
               has_accountable_minister, has_responsible_official,
               chain_incomplete, source_url
        FROM v_accountability_chain_completeness
        ORDER BY chain_incomplete DESC, title
        LIMIT 80
      `
      : `
        SELECT i.slug, i.title, i.instrument_type, a.name AS agency_name,
               EXISTS (SELECT 1 FROM instrument_links il WHERE il.instrument_id = i.id AND il.link_kind = 'accountable_for') AS has_accountable_minister,
               EXISTS (SELECT 1 FROM instrument_links il WHERE il.instrument_id = i.id AND il.link_kind = 'responsible_official') AS has_responsible_official,
               TRUE AS chain_incomplete, i.source_url
        FROM instruments i
        LEFT JOIN agencies a ON a.id = i.agency_id
        ORDER BY i.title
        LIMIT 80
      `;
    const rows = await query<Record<string, unknown>>(sql);
    return rows.map((r) => ({
      slug: String(r.slug),
      title: String(r.title),
      instrumentType: String(r.instrument_type),
      agencyName: (r.agency_name as string | null) ?? null,
      hasAccountableMinister: Boolean(r.has_accountable_minister),
      hasResponsibleOfficial: Boolean(r.has_responsible_official),
      chainIncomplete: Boolean(r.chain_incomplete),
      sourceUrl: (r.source_url as string | null) ?? null,
    }));
  });
}

export async function loadInstruments(q: string | null) {
  const hint = needed(
    "The instruments explorer lists programs, measures, bills, contracts, grants, and policies once those adapters write rows. Search is title ILIKE only. budget_measure and austender now persist sourced rows; instrument_propose stays proposed-only.",
    {
      sources: ["budget_measure", "austender", "instrument_propose", "anao"],
      tables: ["instruments", "agencies"],
    },
  );
  return withFoundation<InstrumentRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT i.slug, i.title, i.instrument_type,
             a.slug AS agency_slug, a.name AS agency_name,
             i.announced_on, i.amount_aud, i.source, i.source_url,
             i.status
      FROM instruments i
      LEFT JOIN agencies a ON a.id = i.agency_id
      WHERE ($1::text IS NULL OR i.title ILIKE '%' || $1 || '%'
             OR i.slug ILIKE '%' || $1 || '%'
             OR i.identifiers::text ILIKE '%' || $1 || '%')
      ORDER BY i.title
      LIMIT 80
      `,
      [q?.trim() || null],
    ).catch(async () =>
      query<Record<string, unknown>>(
        `
        SELECT i.slug, i.title, i.instrument_type,
               a.slug AS agency_slug, a.name AS agency_name,
               i.announced_on, i.amount_aud, i.source, i.source_url
        FROM instruments i
        LEFT JOIN agencies a ON a.id = i.agency_id
        WHERE ($1::text IS NULL OR i.title ILIKE '%' || $1 || '%'
               OR i.slug ILIKE '%' || $1 || '%'
               OR i.identifiers::text ILIKE '%' || $1 || '%')
        ORDER BY i.title
        LIMIT 80
        `,
        [q?.trim() || null],
      ),
    );
    return rows.map((r) => ({
      slug: String(r.slug),
      title: String(r.title),
      instrumentType: String(r.instrument_type),
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      announcedOn: dateOnly(r.announced_on),
      amountAud: r.amount_aud != null ? String(r.amount_aud) : null,
      source: (r.source as string | null) ?? null,
      sourceUrl: (r.source_url as string | null) ?? null,
      status: (r.status as string | null) ?? null,
    }));
  }, { query: q });
}

export async function loadInstrument(slug: string) {
  const hint = needed(
    "An instrument dossier needs a sourced row in instruments. budget_measure and austender persist asserted rows; instrument_propose stays proposed-only.",
    {
      sources: ["budget_measure", "austender", "instrument_propose"],
      tables: ["instruments", "agencies"],
    },
  );
  return withFoundation<InstrumentRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT i.slug, i.title, i.instrument_type,
             a.slug AS agency_slug, a.name AS agency_name,
             i.announced_on, i.commenced_on, i.ended_on, i.amount_aud,
             i.source, i.source_url, i.status, i.summary
      FROM instruments i
      LEFT JOIN agencies a ON a.id = i.agency_id
      WHERE i.slug = $1
      LIMIT 1
      `,
      [slug],
    );
    return rows.map((r) => ({
      slug: String(r.slug),
      title: String(r.title),
      instrumentType: String(r.instrument_type),
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      announcedOn: dateOnly(r.announced_on),
      commencedOn: dateOnly(r.commenced_on),
      endedOn: dateOnly(r.ended_on),
      amountAud: r.amount_aud != null ? String(r.amount_aud) : null,
      source: (r.source as string | null) ?? null,
      sourceUrl: (r.source_url as string | null) ?? null,
      status: (r.status as string | null) ?? null,
      summary: (r.summary as string | null) ?? null,
    }));
  });
}

export type QonStatus = "open" | "answered" | "overdue" | "refused" | "unknown";

export type QonRow = {
  sourceKey: string;
  qonNumber: string | null;
  portfolioQuestionNumber: string | null;
  portfolio: string | null;
  agencyName: string | null;
  askedBy: string | null;
  askedOn: string | null;
  dueOn: string | null;
  answeredOn: string | null;
  status: QonStatus;
  sourceUrl: string | null;
  committeeName: string | null;
  estimatesRound: string | null;
  questionRef: string | null;
  answerRef: string | null;
};

export type QonPortfolioCount = {
  portfolio: string;
  questionCount: number;
  openCount: number;
  answeredCount: number;
  overdueCount: number;
  unknownCount: number;
  refusedCount: number;
};

export async function loadQon(limit = 40): Promise<{
  source: "postgres" | "unavailable";
  questions: QonRow[];
  byPortfolio: QonPortfolioCount[];
}> {
  if (!(await postgresAvailable())) {
    return { source: "unavailable", questions: [], byPortfolio: [] };
  }
  try {
    const [rows, counts] = await Promise.all([
      query<Record<string, unknown>>(
        `
        SELECT q.source_key, q.number AS qon_number, q.portfolio,
               a.name AS agency_name, q.asking_member, q.asked_on, q.due_on,
               q.answered_on, q.status, q.source_url, q.question_ref, q.answer_ref,
               q.identifiers
        FROM qons q
        LEFT JOIN agencies a ON a.id = q.answering_agency_id
        ORDER BY q.asked_on DESC NULLS LAST, q.number
        LIMIT $1
        `,
        [limit],
      ).catch(async () =>
        query<Record<string, unknown>>(
          `
          SELECT q.source_key, q.number AS qon_number, q.portfolio,
                 a.name AS agency_name, q.asking_member, q.asked_on, q.due_on,
                 q.answered_on, q.status, q.source_url, q.question_ref, q.answer_ref
          FROM qons q
          LEFT JOIN agencies a ON a.id = q.answering_agency_id
          ORDER BY q.asked_on DESC NULLS LAST, q.number
          LIMIT $1
          `,
          [limit],
        ),
      ),
      query<Record<string, unknown>>(`
        SELECT portfolio,
               qon_count AS question_count,
               openish_count AS open_count,
               answered_count,
               overdue_count,
               refused_count
        FROM v_accountability_qon_debt
        ORDER BY overdue_count DESC, openish_count DESC, portfolio
      `).catch(async () =>
        query<Record<string, unknown>>(`
          SELECT COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
                 COUNT(*)::int AS question_count,
                 COUNT(*) FILTER (WHERE q.status IN ('open', 'unknown'))::int AS open_count,
                 COUNT(*) FILTER (WHERE q.status = 'answered')::int AS answered_count,
                 COUNT(*) FILTER (WHERE q.status = 'overdue')::int AS overdue_count,
                 COUNT(*) FILTER (WHERE q.status = 'refused')::int AS refused_count
          FROM qons q
          GROUP BY 1
          ORDER BY question_count DESC, portfolio
        `),
      ),
    ]);
    return {
      source: "postgres",
      questions: rows.map((row) => {
        const identifiers = (row.identifiers as Record<string, unknown> | null) || {};
        return {
          sourceKey: String(row.source_key),
          qonNumber: (row.qon_number as string | null) ?? null,
          portfolioQuestionNumber:
            (identifiers.portfolio_question_number as string | null) ?? null,
          portfolio: (row.portfolio as string | null) ?? null,
          agencyName: (row.agency_name as string | null) ?? null,
          askedBy: (row.asking_member as string | null) ?? null,
          askedOn: dateOnly(row.asked_on),
          dueOn: dateOnly(row.due_on),
          answeredOn: dateOnly(row.answered_on),
          status: (row.status as QonStatus) || "unknown",
          sourceUrl: (row.source_url as string | null) ?? null,
          committeeName: (identifiers.committee_name as string | null) ?? null,
          estimatesRound: (identifiers.estimates_round as string | null) ?? null,
          questionRef: (row.question_ref as string | null) ?? null,
          answerRef: (row.answer_ref as string | null) ?? null,
        };
      }),
      byPortfolio: counts.map((row) => ({
        portfolio: String(row.portfolio),
        questionCount: Number(row.question_count ?? 0),
        openCount: Number(row.open_count ?? 0),
        answeredCount: Number(row.answered_count ?? 0),
        overdueCount: Number(row.overdue_count ?? 0),
        unknownCount: Number(row.unknown_count ?? 0),
        refusedCount: Number(row.refused_count ?? 0),
      })),
    };
  } catch {
    return { source: "unavailable", questions: [], byPortfolio: [] };
  }
}

export type AccountabilitySummary = {
  source: "postgres" | "unavailable";
  agencies: number;
  handbookEntries: number;
  questions: number;
  instrumentsProposed: number;
  hearingSegments: number;
  anaoItems: number;
  contracts: number;
  measures: number;
  qonByPortfolio: QonPortfolioCount[];
};

export async function loadAccountabilitySummary(): Promise<AccountabilitySummary> {
  const empty: AccountabilitySummary = {
    source: "unavailable",
    agencies: 0,
    handbookEntries: 0,
    questions: 0,
    instrumentsProposed: 0,
    hearingSegments: 0,
    anaoItems: 0,
    contracts: 0,
    measures: 0,
    qonByPortfolio: [],
  };
  if (!(await postgresAvailable())) {
    return empty;
  }
  try {
    const [counts, qon] = await Promise.all([
      query<Record<string, unknown>>(`
        SELECT
          (SELECT COUNT(*)::int FROM agencies) AS agencies,
          (SELECT COUNT(*)::int FROM handbook_entries) AS handbook_entries,
          (SELECT COUNT(*)::int FROM qons) AS questions,
          (SELECT COUNT(*)::int FROM instruments WHERE COALESCE(status, '') = 'proposed') AS instruments_proposed,
          (SELECT COUNT(*)::int FROM hearing_segments) AS hearing_segments,
          (SELECT COUNT(*)::int FROM scrutiny_items WHERE item_type = 'anao') AS anao_items,
          (SELECT COUNT(*)::int FROM instruments WHERE instrument_type = 'contract') AS contracts,
          (SELECT COUNT(*)::int FROM instruments WHERE instrument_type IN ('measure', 'program') AND COALESCE(status, '') <> 'proposed') AS measures
      `).catch(async () =>
        query<Record<string, unknown>>(`
          SELECT
            (SELECT COUNT(*)::int FROM agencies) AS agencies,
            (SELECT COUNT(*)::int FROM handbook_entries) AS handbook_entries,
            (SELECT COUNT(*)::int FROM qons) AS questions,
            (SELECT COUNT(*)::int FROM instruments) AS instruments_proposed,
            0::int AS hearing_segments,
            (SELECT COUNT(*)::int FROM scrutiny_items WHERE item_type = 'anao') AS anao_items,
            (SELECT COUNT(*)::int FROM instruments WHERE instrument_type = 'contract') AS contracts,
            (SELECT COUNT(*)::int FROM instruments WHERE instrument_type IN ('measure', 'program')) AS measures
        `),
      ),
      loadQon(1),
    ]);
    const row = counts[0] || {};
    return {
      source: "postgres",
      agencies: Number(row.agencies ?? 0),
      handbookEntries: Number(row.handbook_entries ?? 0),
      questions: Number(row.questions ?? 0),
      instrumentsProposed: Number(row.instruments_proposed ?? 0),
      hearingSegments: Number(row.hearing_segments ?? 0),
      anaoItems: Number(row.anao_items ?? 0),
      contracts: Number(row.contracts ?? 0),
      measures: Number(row.measures ?? 0),
      qonByPortfolio: qon.byPortfolio,
    };
  } catch {
    return empty;
  }
}
