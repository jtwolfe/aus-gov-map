import type { NeededHint } from "./accountability";
import { postgresAvailable, query } from "./db";
import {
  anaoMoments,
  assignLane,
  buildArcs,
  capsFor,
  filterInstruments,
  hearingMoments,
  occupantsAtDate,
  parseAtlasParams,
  qonMoments,
  rankLanes,
  resolveWindow,
  tenuresFromRoles,
  type AnaoItem,
  type AtlasArc,
  type AtlasInstrument,
  type AtlasMoment,
  type AtlasParams,
  type AtlasTenure,
  type ClaimLink,
  type DataBounds,
  type DateWindow,
  type HearingAppearance,
  type HearingRollup,
  type InstrumentInput,
  type Lane,
  type QonEvent,
  type TenureInput,
  type TestedLink,
} from "./atlas-query";

export type AtlasPayload = {
  source: "postgres" | "fixture";
  ready: boolean;
  needed: NeededHint;
  window: DateWindow;
  laneMode: AtlasParams["lane"];
  params: AtlasParams;
  lanes: Lane[];
  tenures: AtlasTenure[];
  moments: AtlasMoment[];
  instruments: AtlasInstrument[];
  arcs: AtlasArc[];
  asOf: {
    date: string;
    occupants: ReturnType<typeof occupantsAtDate>;
  } | null;
  counts: {
    lanes: number;
    tenures: number;
    moments: number;
    instruments: number;
    arcs: number;
    droppedLanes: number;
  };
};

const FOUNDATION = ["person_roles", "hearings", "agencies", "people"] as const;

function dateOnly(value: unknown): string | null {
  return value ? String(value).slice(0, 10) : null;
}

function needed(note: string, extra: Partial<NeededHint> = {}): NeededHint {
  return {
    note,
    apply: "make db-apply",
    sources: extra.sources ?? [
      "handbook",
      "aps_leaders",
      "estimates",
      "qon",
      "anao",
      "budget_measure",
      "austender",
    ],
    tables: extra.tables ?? [
      "person_roles",
      "hearings",
      "qons",
      "scrutiny_items",
      "instruments",
      "claims",
    ],
  };
}

const EMPTY_HINT = needed(
  "The Atlas reads sourced occupancies, hearing-level moments, QoNs, ANAO items, and instruments. Fixture mode has hearings only — no invented tenures. Start Postgres, apply 007–011, then run the listed ingest sources.",
);

async function tablesExist(names: readonly string[]): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = ANY($1)
    `,
    [names],
  );
  return (rows[0]?.n ?? 0) >= names.length;
}

async function relationExists(name: string, kind: "views" | "tables" = "views"): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.${kind}
    WHERE table_schema = 'public' AND table_name = $1
    `,
    [name],
  );
  return (rows[0]?.n ?? 0) === 1;
}

function emptyPayload(source: AtlasPayload["source"], hint: NeededHint, params: AtlasParams): AtlasPayload {
  const window = resolveWindow({ min: null, max: null }, { from: params.from, to: params.to });
  return {
    source,
    ready: false,
    needed: hint,
    window,
    laneMode: params.lane,
    params,
    lanes: [],
    tenures: [],
    moments: [],
    instruments: [],
    arcs: [],
    asOf: params.asOf ? { date: params.asOf, occupants: [] } : null,
    counts: { lanes: 0, tenures: 0, moments: 0, instruments: 0, arcs: 0, droppedLanes: 0 },
  };
}

function like(value: string | null): string | null {
  return value?.trim() || null;
}

export async function loadAtlas(input: URLSearchParams | AtlasParams): Promise<AtlasPayload> {
  const params = input instanceof URLSearchParams ? parseAtlasParams(input) : input;

  if (!(await postgresAvailable())) {
    return emptyPayload(
      "fixture",
      needed(
        "Postgres is not reachable. The bundled fixture has hearings only — the Atlas will not invent tenures, QoNs, or instruments. Open Accountability for the empty-safe lenses, or start Postgres with make db-up.",
      ),
      params,
    );
  }

  try {
    if (!(await tablesExist(FOUNDATION))) {
      return emptyPayload(
        "postgres",
        needed("Foundation tables are missing. Run make db-apply so person_roles and hearings exist."),
        params,
      );
    }

    const hasQons = await tablesExist(["qons"]);
    const hasScrutiny = await tablesExist(["scrutiny_items"]);
    const hasInstruments = await tablesExist(["instruments"]);
    const hasClaims = await tablesExist(["claims"]);
    const hasSegments = await tablesExist(["hearing_segments"]);
    const hasHearingView = await relationExists("v_atlas_hearing_moments");
    const hasClaimsQon = hasClaims && (await columnExists("claims", "qon_id"));
    const hasInstrumentStatus = hasInstruments && (await columnExists("instruments", "status"));

    const bounds = await loadBounds();
    const window = resolveWindow(bounds, { from: params.from, to: params.to });
    const caps = capsFor(params.compact);
    const agency = like(params.agency);
    const portfolio = like(params.portfolio);
    const person = like(params.person);
    const instrument = like(params.instrument);

    const [roleRows, appearanceRows, hearingRows, qonRows, anaoRows, instrumentRows, claimRows, testedRows] =
      await Promise.all([
        loadTenures(window, { agency, portfolio, person }),
        person && params.lane === "person"
          ? loadAppearances(person)
          : Promise.resolve<HearingAppearance[]>([]),
        loadHearings(window, { agency, portfolio, person, hasSegments, hasHearingView }),
        params.qon && hasQons
          ? loadQons(window, { agency, portfolio, person })
          : Promise.resolve<QonEvent[]>([]),
        params.anao && hasScrutiny
          ? loadAnao(window, { agency, portfolio })
          : Promise.resolve<AnaoItem[]>([]),
        hasInstruments
          ? loadInstrumentRows(window, { agency, portfolio, instrument, hasInstrumentStatus })
          : Promise.resolve<InstrumentInput[]>([]),
        params.arcs && hasClaims
          ? loadClaims(hasClaimsQon)
          : Promise.resolve<ClaimLink[]>([]),
        params.arcs && hasInstruments
          ? loadTestedLinks()
          : Promise.resolve<TestedLink[]>([]),
      ]);

    const roleTenures = tenuresFromRoles(roleRows, appearanceRows);
    const instrumentsIn = filterInstruments(instrumentRows, {
      includeProposed: params.includeProposed,
      focusInstrument: instrument,
    });

    const laneMap = new Map<string, Lane>();
    const tenures: AtlasTenure[] = [];
    for (const row of roleTenures) {
      const lane = assignLane(row, params.lane);
      laneMap.set(lane.id, lane);
      tenures.push({ ...row, laneId: lane.id });
    }

    // Person-mode hearing moments sit on the person who appeared, not a fake tenure.
    let hearingsForMoments = hearingRows;
    if (params.lane === "person" && appearanceRows.length) {
      hearingsForMoments = hearingRows.map((h) => {
        const hit = appearanceRows.find((a) => a.hearingId === h.id);
        if (!hit) return h;
        const tenure = roleTenures.find((t) => t.personId === hit.personId);
        return {
          ...h,
          personId: hit.personId,
          personSlug: tenure?.personSlug ?? person,
          personName: tenure?.personName ?? person,
        };
      });
    }

    const moments: AtlasMoment[] = [
      ...hearingMoments(hearingsForMoments, params.lane),
      ...qonMoments(qonRows, params.lane),
      ...anaoMoments(anaoRows, params.lane),
    ];
    for (const moment of moments) {
      if (!laneMap.has(moment.laneId)) {
        laneMap.set(moment.laneId, {
          id: moment.laneId,
          label: labelFromLaneId(moment.laneId, moment.title),
          kind: kindFromLaneId(moment.laneId),
          href: hrefFromLaneId(moment.laneId),
        });
      }
    }

    const instruments: AtlasInstrument[] = [];
    for (const row of instrumentsIn) {
      const lane = assignLane(row, params.lane);
      laneMap.set(lane.id, lane);
      instruments.push({ ...row, laneId: lane.id });
    }

    const pinned = new Set<string>();
    if (agency) pinned.add(`agency:${agency}`);
    if (portfolio) pinned.add(`portfolio:${slugish(portfolio)}`);
    if (person && params.lane === "person") pinned.add(`person:${person}`);

    const ranked = rankLanes([...laneMap.values()], tenures, moments, instruments, pinned, caps.lanes);
    const kept = new Set(ranked.map((l) => l.id));
    const tenuresKept = tenures.filter((t) => kept.has(t.laneId)).slice(0, caps.tenures);
    const momentsKept = moments.filter((m) => kept.has(m.laneId)).slice(0, caps.moments);
    const instrumentsKept = instruments.filter((i) => kept.has(i.laneId)).slice(0, caps.instruments);

    const momentIds = new Set(momentsKept.map((m) => m.id));
    const instrumentIds = new Set(instrumentsKept.map((i) => i.id));
    const arcs = params.arcs
      ? buildArcs(claimRows, testedRows, momentIds, instrumentIds).slice(0, caps.arcs)
      : [];

    const asOfDate = params.asOf && params.asOf >= window.from && params.asOf <= window.to
      ? params.asOf
      : params.asOf;
    const asOf = asOfDate
      ? { date: asOfDate, occupants: occupantsAtDate(tenuresKept, asOfDate) }
      : null;

    return {
      source: "postgres",
      ready: true,
      needed: EMPTY_HINT,
      window,
      laneMode: params.lane,
      params,
      lanes: ranked,
      tenures: tenuresKept,
      moments: momentsKept,
      instruments: instrumentsKept,
      arcs,
      asOf,
      counts: {
        lanes: ranked.length,
        tenures: tenuresKept.length,
        moments: momentsKept.length,
        instruments: instrumentsKept.length,
        arcs: arcs.length,
        droppedLanes: Math.max(0, laneMap.size - ranked.length),
      },
    };
  } catch {
    return emptyPayload(
      "postgres",
      needed("The Atlas query failed — usually a missing view or column. Run make db-apply (007–011) and retry. No conclusion is inferred."),
      params,
    );
  }
}

async function columnExists(table: string, column: string): Promise<boolean> {
  const rows = await query<{ n: number }>(
    `
    SELECT COUNT(*)::int AS n
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2
    `,
    [table, column],
  );
  return (rows[0]?.n ?? 0) === 1;
}

async function loadBounds(): Promise<DataBounds> {
  const rows = await query<Record<string, unknown>>(`
    SELECT
      LEAST(
        (SELECT MIN(held_on) FROM hearings),
        (SELECT MIN(start_date) FROM person_roles),
        (SELECT MIN(asked_on) FROM qons),
        (SELECT MIN(published_on) FROM scrutiny_items WHERE item_type = 'anao'),
        (SELECT MIN(COALESCE(commenced_on, announced_on)) FROM instruments)
      ) AS min_date,
      GREATEST(
        (SELECT MAX(held_on) FROM hearings),
        (SELECT MAX(COALESCE(end_date, CURRENT_DATE)) FROM person_roles),
        (SELECT MAX(COALESCE(answered_on, due_on, asked_on)) FROM qons),
        (SELECT MAX(published_on) FROM scrutiny_items WHERE item_type = 'anao'),
        (SELECT MAX(COALESCE(ended_on, commenced_on, announced_on, CURRENT_DATE)) FROM instruments)
      ) AS max_date
  `).catch(async () =>
    query<Record<string, unknown>>(`
      SELECT
        LEAST(
          (SELECT MIN(held_on) FROM hearings),
          (SELECT MIN(start_date) FROM person_roles)
        ) AS min_date,
        GREATEST(
          (SELECT MAX(held_on) FROM hearings),
          (SELECT MAX(COALESCE(end_date, CURRENT_DATE)) FROM person_roles)
        ) AS max_date
    `),
  );
  return {
    min: dateOnly(rows[0]?.min_date),
    max: dateOnly(rows[0]?.max_date),
  };
}

async function loadTenures(
  window: DateWindow,
  filters: { agency: string | null; portfolio: string | null; person: string | null },
): Promise<TenureInput[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT pr.id, p.id AS person_id, p.slug AS person_slug, p.name AS person_name,
           pr.role_type, COALESCE(r.title, pr.organisation, pr.role_type) AS role_title,
           pr.portfolio, pr.organisation, pr.source, pr.source_url,
           pr.start_date, pr.end_date,
           a.slug AS agency_slug, a.name AS agency_name
    FROM person_roles pr
    JOIN people p ON p.id = pr.person_id
    LEFT JOIN roles r ON r.id = pr.role_id
    LEFT JOIN agencies a ON a.id = COALESCE(pr.agency_id, r.agency_id)
    WHERE (pr.end_date IS NULL OR pr.end_date >= $1::date)
      AND (pr.start_date IS NULL OR pr.start_date <= $2::date)
      AND ($3::text IS NULL OR a.slug ILIKE $3 OR a.name ILIKE '%' || $3 || '%'
           OR pr.organisation ILIKE '%' || $3 || '%')
      AND ($4::text IS NULL OR pr.portfolio ILIKE '%' || $4 || '%'
           OR r.portfolio ILIKE '%' || $4 || '%' OR a.portfolio ILIKE '%' || $4 || '%')
      AND ($5::text IS NULL OR p.slug ILIKE $5 OR p.name ILIKE '%' || $5 || '%')
    ORDER BY COALESCE(pr.start_date, $1::date), p.name
    LIMIT 400
    `,
    [window.from, window.to, filters.agency, filters.portfolio, filters.person],
  );
  return rows.map((r) => ({
    id: String(r.id),
    personId: String(r.person_id),
    personSlug: (r.person_slug as string | null) ?? null,
    personName: String(r.person_name),
    roleType: String(r.role_type),
    roleTitle: (r.role_title as string | null) ?? null,
    start: dateOnly(r.start_date),
    end: dateOnly(r.end_date),
    source: String(r.source),
    href: r.person_slug ? `/people/${r.person_slug}` : null,
    agencySlug: (r.agency_slug as string | null) ?? null,
    agencyName: (r.agency_name as string | null) ?? null,
    portfolio: (r.portfolio as string | null) ?? null,
  }));
}

async function loadAppearances(person: string): Promise<HearingAppearance[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT hp.hearing_id, hp.person_id
    FROM hearing_people hp
    JOIN people p ON p.id = hp.person_id
    WHERE p.slug ILIKE $1 OR p.name ILIKE '%' || $1 || '%'
    `,
    [person],
  );
  return rows.map((r) => ({
    hearingId: String(r.hearing_id),
    personId: String(r.person_id),
  }));
}

async function loadHearings(
  window: DateWindow,
  opts: {
    agency: string | null;
    portfolio: string | null;
    person: string | null;
    hasSegments: boolean;
    hasHearingView: boolean;
  },
): Promise<HearingRollup[]> {
  const rollup = opts.hasHearingView
    ? `
      SELECT h.id, h.slug, h.title, h.held_on, h.portfolio, h.source_url,
             COALESCE(v.segment_count, 0) AS segment_count,
             COALESCE(v.portfolio_chip_count, 0) AS portfolio_chip_count,
             COALESCE(v.agency_chip_count, 0) AS agency_chip_count,
             COALESCE(v.taken_on_notice_count, 0) AS taken_on_notice_count
      FROM hearings h
      LEFT JOIN v_atlas_hearing_moments v ON v.hearing_id = h.id
    `
    : opts.hasSegments
      ? `
      SELECT h.id, h.slug, h.title, h.held_on, h.portfolio, h.source_url,
             COUNT(hs.id)::int AS segment_count,
             COUNT(DISTINCT hs.portfolio) FILTER (WHERE hs.portfolio IS NOT NULL)::int AS portfolio_chip_count,
             COUNT(DISTINCT hs.agency) FILTER (WHERE hs.agency IS NOT NULL)::int AS agency_chip_count,
             COUNT(*) FILTER (WHERE hs.kind = 'taken_on_notice')::int AS taken_on_notice_count
      FROM hearings h
      LEFT JOIN hearing_segments hs ON hs.hearing_id = h.id
      `
      : `
      SELECT h.id, h.slug, h.title, h.held_on, h.portfolio, h.source_url,
             0::int AS segment_count, 0::int AS portfolio_chip_count,
             0::int AS agency_chip_count, 0::int AS taken_on_notice_count
      FROM hearings h
    `;

  const groupBy = opts.hasHearingView || !opts.hasSegments ? "" : "GROUP BY h.id";
  const sql = `
    ${rollup}
    WHERE h.held_on IS NOT NULL
      AND h.held_on >= $1::date AND h.held_on <= $2::date
      AND ($3::text IS NULL OR h.portfolio ILIKE '%' || $3 || '%'
           ${opts.hasSegments ? "OR EXISTS (SELECT 1 FROM hearing_segments s WHERE s.hearing_id = h.id AND (s.agency ILIKE '%' || $3 || '%' OR s.portfolio ILIKE '%' || $3 || '%'))" : ""})
      AND ($4::text IS NULL OR h.portfolio ILIKE '%' || $4 || '%')
      AND ($5::text IS NULL OR EXISTS (
            SELECT 1 FROM hearing_people hp
            JOIN people p ON p.id = hp.person_id
            WHERE hp.hearing_id = h.id AND (p.slug ILIKE $5 OR p.name ILIKE '%' || $5 || '%')
          ))
    ${groupBy}
    ORDER BY h.held_on
    LIMIT 200
  `;
  const rows = await query<Record<string, unknown>>(sql, [
    window.from,
    window.to,
    opts.agency,
    opts.portfolio,
    opts.person,
  ]);
  return rows.map((r) => ({
    id: String(r.id),
    slug: String(r.slug),
    title: String(r.title),
    heldOn: dateOnly(r.held_on),
    portfolio: (r.portfolio as string | null) ?? null,
    href: `/hearings/${r.slug}`,
    segmentCount: Number(r.segment_count ?? 0),
    portfolioChipCount: Number(r.portfolio_chip_count ?? 0),
    agencyChipCount: Number(r.agency_chip_count ?? 0),
    takenOnNoticeCount: Number(r.taken_on_notice_count ?? 0),
  }));
}

async function loadQons(
  window: DateWindow,
  filters: { agency: string | null; portfolio: string | null; person: string | null },
): Promise<QonEvent[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT q.id, q.number, q.portfolio, q.asked_on, q.answered_on, q.due_on, q.status,
           q.source_url, q.source_key, q.question_ref,
           a.slug AS agency_slug, a.name AS agency_name,
           ask.slug AS asker_slug, ask.name AS asker_name,
           ans.slug AS answerer_slug, ans.name AS answerer_name
    FROM qons q
    LEFT JOIN agencies a ON a.id = q.answering_agency_id
    LEFT JOIN people ask ON ask.id = q.asking_person_id
    LEFT JOIN people ans ON ans.id = q.answering_minister_id
    WHERE (
        (q.asked_on IS NOT NULL AND q.asked_on >= $1::date AND q.asked_on <= $2::date)
        OR (q.answered_on IS NOT NULL AND q.answered_on >= $1::date AND q.answered_on <= $2::date)
        OR (q.due_on IS NOT NULL AND q.due_on >= $1::date AND q.due_on <= $2::date)
      )
      AND ($3::text IS NULL OR a.slug ILIKE $3 OR a.name ILIKE '%' || $3 || '%')
      AND ($4::text IS NULL OR q.portfolio ILIKE '%' || $4 || '%')
      AND ($5::text IS NULL
           OR ask.slug ILIKE $5 OR ask.name ILIKE '%' || $5 || '%'
           OR ans.slug ILIKE $5 OR ans.name ILIKE '%' || $5 || '%'
           OR q.asking_member ILIKE '%' || $5 || '%')
    ORDER BY COALESCE(q.asked_on, q.due_on) NULLS LAST
    LIMIT 160
    `,
    [window.from, window.to, filters.agency, filters.portfolio, filters.person],
  );
  return rows.map((r) => {
    const number = (r.number as string | null) ?? null;
    const title = number ? `QoN ${number}` : "Question on notice";
    return {
      id: String(r.id),
      number,
      askedOn: dateOnly(r.asked_on),
      answeredOn: dateOnly(r.answered_on),
      dueOn: dateOnly(r.due_on),
      status: String(r.status ?? "unknown"),
      title: r.portfolio ? `${title} · ${r.portfolio}` : title,
      href: (r.source_url as string | null) || "/accountability/qon-debt",
      agencySlug: (r.agency_slug as string | null) ?? null,
      agencyName: (r.agency_name as string | null) ?? null,
      portfolio: (r.portfolio as string | null) ?? null,
      personSlug: (r.answerer_slug as string | null) ?? (r.asker_slug as string | null) ?? null,
      personName: (r.answerer_name as string | null) ?? (r.asker_name as string | null) ?? null,
    };
  });
}

async function loadAnao(
  window: DateWindow,
  filters: { agency: string | null; portfolio: string | null },
): Promise<AnaoItem[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT s.id, s.slug, s.title, s.published_on, s.source_url,
           a.slug AS agency_slug, a.name AS agency_name, a.portfolio
    FROM scrutiny_items s
    LEFT JOIN outcomes o ON o.scrutiny_item_id = s.id
    LEFT JOIN agencies a ON a.id = o.agency_id
    WHERE s.item_type = 'anao'
      AND s.published_on IS NOT NULL
      AND s.published_on >= $1::date AND s.published_on <= $2::date
      AND ($3::text IS NULL OR a.slug ILIKE $3 OR a.name ILIKE '%' || $3 || '%'
           OR s.title ILIKE '%' || $3 || '%')
      AND ($4::text IS NULL OR a.portfolio ILIKE '%' || $4 || '%' OR s.title ILIKE '%' || $4 || '%')
    ORDER BY s.published_on
    LIMIT 80
    `,
    [window.from, window.to, filters.agency, filters.portfolio],
  ).catch(async () =>
    query<Record<string, unknown>>(
      `
      SELECT s.id, s.slug, s.title, s.published_on, s.source_url,
             NULL::text AS agency_slug, NULL::text AS agency_name, NULL::text AS portfolio
      FROM scrutiny_items s
      WHERE s.item_type = 'anao'
        AND s.published_on IS NOT NULL
        AND s.published_on >= $1::date AND s.published_on <= $2::date
      ORDER BY s.published_on
      LIMIT 80
      `,
      [window.from, window.to],
    ),
  );
  return rows.map((r) => ({
    id: String(r.id),
    title: String(r.title),
    publishedOn: dateOnly(r.published_on),
    href: (r.source_url as string | null) || (r.slug ? `/atlas?instrument=${r.slug}` : null),
    agencySlug: (r.agency_slug as string | null) ?? null,
    agencyName: (r.agency_name as string | null) ?? null,
    portfolio: (r.portfolio as string | null) ?? null,
  }));
}

async function loadInstrumentRows(
  window: DateWindow,
  opts: {
    agency: string | null;
    portfolio: string | null;
    instrument: string | null;
    hasInstrumentStatus: boolean;
  },
): Promise<InstrumentInput[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT i.id, i.slug, i.title, i.instrument_type,
           ${opts.hasInstrumentStatus ? "i.status" : "NULL::text AS status"},
           COALESCE(i.commenced_on, i.announced_on) AS start_on,
           i.ended_on, i.source_url,
           a.slug AS agency_slug, a.name AS agency_name, a.portfolio
    FROM instruments i
    LEFT JOIN agencies a ON a.id = i.agency_id
    WHERE (
        COALESCE(i.commenced_on, i.announced_on) IS NULL
        OR COALESCE(i.commenced_on, i.announced_on) <= $2::date
      )
      AND (i.ended_on IS NULL OR i.ended_on >= $1::date)
      AND ($3::text IS NULL OR a.slug ILIKE $3 OR a.name ILIKE '%' || $3 || '%')
      AND ($4::text IS NULL OR a.portfolio ILIKE '%' || $4 || '%' OR i.title ILIKE '%' || $4 || '%')
      AND ($5::text IS NULL OR i.slug ILIKE $5 OR i.title ILIKE '%' || $5 || '%')
    ORDER BY COALESCE(i.commenced_on, i.announced_on) NULLS LAST
    LIMIT 120
    `,
    [window.from, window.to, opts.agency, opts.portfolio, opts.instrument],
  );
  return rows.map((r) => ({
    id: String(r.id),
    slug: String(r.slug),
    title: String(r.title),
    type: String(r.instrument_type),
    status: (r.status as string | null) ?? null,
    start: dateOnly(r.start_on),
    end: dateOnly(r.ended_on),
    href: `/accountability/instruments/${r.slug}`,
    agencySlug: (r.agency_slug as string | null) ?? null,
    agencyName: (r.agency_name as string | null) ?? null,
    portfolio: (r.portfolio as string | null) ?? null,
  }));
}

async function loadClaims(hasQon: boolean): Promise<ClaimLink[]> {
  const rows = await query<Record<string, unknown>>(
    `
    SELECT id, claim_type, hearing_id, instrument_id
           ${hasQon ? ", qon_id" : ", NULL::uuid AS qon_id"}
    FROM claims
    WHERE claim_type IN ('promise', 'assurance', 'taken_on_notice')
    LIMIT 200
    `,
  );
  return rows.map((r) => ({
    id: String(r.id),
    claimType: String(r.claim_type),
    hearingId: r.hearing_id ? String(r.hearing_id) : null,
    qonId: r.qon_id ? String(r.qon_id) : null,
    instrumentId: r.instrument_id ? String(r.instrument_id) : null,
  }));
}

async function loadTestedLinks(): Promise<TestedLink[]> {
  const rows = await query<Record<string, unknown>>(`
    SELECT instrument_id, hearing_id, scrutiny_item_id
    FROM instrument_links
    WHERE link_kind = 'tested_in'
    LIMIT 200
  `).catch(() => []);
  return rows.map((r) => ({
    instrumentId: String(r.instrument_id),
    hearingId: r.hearing_id ? String(r.hearing_id) : null,
    qonId: null,
    scrutinyId: r.scrutiny_item_id ? String(r.scrutiny_item_id) : null,
  }));
}

function slugish(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "unassigned";
}

function labelFromLaneId(id: string, fallback: string): string {
  if (id === "unassigned") return "Unassigned";
  const [, ...rest] = id.split(":");
  const raw = rest.join(":");
  return raw.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || fallback;
}

function kindFromLaneId(id: string): Lane["kind"] {
  if (id.startsWith("agency:")) return "agency";
  if (id.startsWith("portfolio:")) return "portfolio";
  if (id.startsWith("person:")) return "person";
  return "unassigned";
}

function hrefFromLaneId(id: string): string | null {
  if (id.startsWith("agency:")) return `/agencies/${id.slice(7)}`;
  if (id.startsWith("person:")) return `/people/${id.slice(7)}`;
  return null;
}

export { parseAtlasParams };
