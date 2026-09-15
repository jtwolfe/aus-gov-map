import { postgresAvailable, query } from "./db";

export type AccountabilitySource = "postgres" | "fixture";

export type NeededHint = {
  note: string;
  apply?: string;
  sources?: string[];
  tables?: string[];
};

export type RoleAtDateRow = {
  personSlug: string | null;
  personName: string | null;
  roleTitle: string | null;
  roleType: string;
  portfolio: string | null;
  organisation: string | null;
  agencyName: string | null;
  startDate: string | null;
  endDate: string | null;
  source: string;
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
  openishCount: number;
  overdueCount: number;
  answeredCount: number;
  refusedCount: number;
  qonCount: number;
  latestDue: string | null;
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
  agencyName: string | null;
  announcedOn: string | null;
  amountAud: string | null;
  source: string | null;
  sourceUrl: string | null;
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
    "Role-at-date needs sourced occupancies in person_roles (promoted from Handbook tenures or AAO). Stage 1 hearing appearances are not tenures. Ingest: handbook (set HANDBOOK_LIVE=1 to probe OData).",
    { sources: ["handbook"], tables: ["person_roles", "roles", "handbook_roles"] },
  );
  return withFoundation<RoleAtDateRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT p.slug AS person_slug, p.name AS person_name,
             COALESCE(r.title, pr.organisation, pr.role_type) AS role_title,
             pr.role_type, pr.portfolio, pr.organisation,
             a.name AS agency_name, pr.start_date, pr.end_date, pr.source
      FROM person_roles pr
      JOIN people p ON p.id = pr.person_id
      LEFT JOIN roles r ON r.id = pr.role_id
      LEFT JOIN agencies a ON a.id = COALESCE(pr.agency_id, r.agency_id)
      WHERE ($1::date IS NULL OR pr.start_date IS NULL OR pr.start_date <= $1::date)
        AND ($1::date IS NULL OR pr.end_date IS NULL OR pr.end_date >= $1::date)
        AND ($2::text IS NULL OR p.name ILIKE '%' || $2 || '%' OR p.slug ILIKE '%' || $2 || '%')
        AND ($3::text IS NULL OR pr.portfolio ILIKE '%' || $3 || '%' OR r.portfolio ILIKE '%' || $3 || '%')
      ORDER BY pr.portfolio NULLS LAST, role_title, p.name
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
      agencyName: (r.agency_name as string | null) ?? null,
      startDate: dateOnly(r.start_date),
      endDate: dateOnly(r.end_date),
      source: String(r.source),
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
    "QoN debt counts open and overdue questions by portfolio and answering agency. Run the qon adapter once a real extract exists. Taken-on-notice lines in Hansard are not QoNs until they are promoted.",
    { sources: ["qon"], tables: ["qons", "agencies"] },
  );
  return withFoundation<QonDebtRow>(hint, async () => {
    const sql = (await viewExists("v_accountability_qon_debt"))
      ? `
        SELECT portfolio, agency_slug, agency_name, openish_count, overdue_count,
               answered_count, refused_count, qon_count, latest_due
        FROM v_accountability_qon_debt
        ORDER BY overdue_count DESC, openish_count DESC, portfolio
      `
      : `
        SELECT COALESCE(q.portfolio, '(unspecified portfolio)') AS portfolio,
               a.slug AS agency_slug, a.name AS agency_name,
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
    const rows = await query<Record<string, unknown>>(sql);
    return rows.map((r) => ({
      portfolio: String(r.portfolio),
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      openishCount: Number(r.openish_count ?? 0),
      overdueCount: Number(r.overdue_count ?? 0),
      answeredCount: Number(r.answered_count ?? 0),
      refusedCount: Number(r.refused_count ?? 0),
      qonCount: Number(r.qon_count ?? 0),
      latestDue: dateOnly(r.latest_due),
    }));
  });
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
    "The instruments explorer lists programs, measures, bills, contracts, grants, and policies once those adapters write rows. Search is title ILIKE only.",
    {
      sources: ["budget_measure", "austender"],
      tables: ["instruments", "agencies"],
    },
  );
  return withFoundation<InstrumentRow>(hint, async () => {
    const rows = await query<Record<string, unknown>>(
      `
      SELECT i.slug, i.title, i.instrument_type, a.name AS agency_name,
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
    );
    return rows.map((r) => ({
      slug: String(r.slug),
      title: String(r.title),
      instrumentType: String(r.instrument_type),
      agencyName: (r.agency_name as string | null) ?? null,
      announcedOn: dateOnly(r.announced_on),
      amountAud: r.amount_aud != null ? String(r.amount_aud) : null,
      source: (r.source as string | null) ?? null,
      sourceUrl: (r.source_url as string | null) ?? null,
    }));
  }, { query: q });
}

export const LENSES = [
  { href: "/accountability", label: "Overview", match: "exact" as const },
  { href: "/accountability/role-at-date", label: "Role at date" },
  { href: "/accountability/promise-receipt", label: "Promise → receipt" },
  { href: "/accountability/qon-debt", label: "QoN debt" },
  { href: "/accountability/chain-completeness", label: "Chain completeness" },
  { href: "/accountability/instruments", label: "Instruments" },
];
