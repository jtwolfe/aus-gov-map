/**
 * Pure Responsibility Atlas query builders.
 * Tenures come only from person_roles-shaped rows — never hearing appearances.
 */

export const DEFAULT_MAX_SPAN_DAYS = 366 * 4;
export const REQUEST_MAX_SPAN_DAYS = 366 * 8;
export const OPEN_PRESENT_DAYS = 90;

export type LaneMode = "agency" | "person";
export type LaneKind = "agency" | "portfolio" | "person" | "unassigned";
export type MomentKind = "hearing" | "qon" | "anao";
export type ArcKind = "promise" | "assurance" | "ton" | "tested";

export type AtlasParams = {
  from: string | null;
  to: string | null;
  agency: string | null;
  portfolio: string | null;
  person: string | null;
  instrument: string | null;
  lane: LaneMode;
  includeProposed: boolean;
  asOf: string | null;
  qon: boolean;
  anao: boolean;
  arcs: boolean;
  compact: boolean;
  focus: string | null;
};

export type DataBounds = {
  min: string | null;
  max: string | null;
};

export type DateWindow = {
  from: string;
  to: string;
  bounds: DataBounds;
  clamped: boolean;
};

export type LaneHint = {
  agencySlug?: string | null;
  agencyName?: string | null;
  portfolio?: string | null;
  personId?: string | null;
  personSlug?: string | null;
  personName?: string | null;
};

export type Lane = {
  id: string;
  label: string;
  kind: LaneKind;
  href: string | null;
};

export type TenureInput = {
  id: string;
  personId: string;
  personSlug: string | null;
  personName: string;
  roleType: string;
  roleTitle: string | null;
  start: string | null;
  end: string | null;
  source: string;
  href: string | null;
} & LaneHint;

export type HearingAppearance = {
  hearingId: string;
  personId: string;
};

export type HearingRollup = {
  id: string;
  slug: string;
  title: string;
  heldOn: string | null;
  portfolio: string | null;
  href: string;
  segmentCount: number;
  portfolioChipCount: number;
  agencyChipCount: number;
  takenOnNoticeCount: number;
} & LaneHint;

export type QonEvent = {
  id: string;
  number: string | null;
  askedOn: string | null;
  answeredOn: string | null;
  dueOn: string | null;
  status: string;
  title: string;
  href: string | null;
} & LaneHint;

export type AnaoItem = {
  id: string;
  title: string;
  publishedOn: string | null;
  href: string | null;
} & LaneHint;

export type InstrumentInput = {
  id: string;
  slug: string;
  title: string;
  type: string;
  status: string | null;
  start: string | null;
  end: string | null;
  href: string;
} & LaneHint;

export type ClaimLink = {
  id: string;
  claimType: string;
  hearingId: string | null;
  qonId: string | null;
  instrumentId: string | null;
};

export type TestedLink = {
  instrumentId: string;
  hearingId: string | null;
  qonId: string | null;
  scrutinyId: string | null;
};

export type AtlasTenure = TenureInput & { laneId: string };
export type AtlasMoment = {
  id: string;
  laneId: string;
  at: string;
  kind: MomentKind;
  title: string;
  href: string | null;
  status: string | null;
  meta?: Record<string, number | string | null>;
};
export type AtlasInstrument = InstrumentInput & { laneId: string };
export type AtlasArc = {
  id: string;
  fromMomentId: string;
  toMomentId: string | null;
  toInstrumentId: string | null;
  kind: ArcKind;
};
export type AsOfOccupant = {
  laneId: string;
  personSlug: string | null;
  personName: string;
  roleType: string;
  roleTitle: string | null;
  href: string | null;
  source: string;
};

const ISO = /^\d{4}-\d{2}-\d{2}$/;

export function isIsoDate(value: string | null | undefined): value is string {
  return Boolean(value && ISO.test(value));
}

export function slugify(value: string | null | undefined): string {
  const s = (value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return s || "unassigned";
}

export function parseBool(value: string | null, defaultValue: boolean): boolean {
  if (value == null || value === "") return defaultValue;
  return !["0", "false", "off", "no"].includes(value.toLowerCase());
}

export function parseAtlasParams(search: URLSearchParams): AtlasParams {
  const lane = search.get("lane") === "person" ? "person" : "agency";
  return {
    from: isIsoDate(search.get("from")) ? search.get("from") : null,
    to: isIsoDate(search.get("to")) ? search.get("to") : null,
    agency: search.get("agency")?.trim() || null,
    portfolio: search.get("portfolio")?.trim() || null,
    person: search.get("person")?.trim() || null,
    instrument: search.get("instrument")?.trim() || null,
    lane,
    includeProposed: parseBool(search.get("includeProposed"), false),
    asOf: isIsoDate(search.get("asOf")) ? search.get("asOf") : null,
    qon: parseBool(search.get("qon"), true),
    anao: parseBool(search.get("anao"), true),
    arcs: parseBool(search.get("arcs"), true),
    compact: parseBool(search.get("compact"), false),
    focus: search.get("focus")?.trim() || null,
  };
}

export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return dt.toISOString().slice(0, 10);
}

export function clampIso(iso: string, min: string, max: string): string {
  if (iso < min) return min;
  if (iso > max) return max;
  return iso;
}

export function daysBetween(from: string, to: string): number {
  const a = Date.parse(`${from}T00:00:00Z`);
  const b = Date.parse(`${to}T00:00:00Z`);
  return Math.round((b - a) / 86400000);
}

export function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Bound the paint window. Default covers observed data, then clamps to
 * maxSpanDays ending at the latest bound. Never returns an unbounded range.
 */
export function resolveWindow(
  bounds: DataBounds,
  requested: { from?: string | null; to?: string | null } = {},
  options: { maxSpanDays?: number; defaultSpanDays?: number; today?: string } = {},
): DateWindow {
  const today = options.today ?? todayUtc();
  const defaultSpan = options.defaultSpanDays ?? DEFAULT_MAX_SPAN_DAYS;
  const maxSpan = options.maxSpanDays ?? (requested.from || requested.to ? REQUEST_MAX_SPAN_DAYS : defaultSpan);

  const dataMin = isIsoDate(bounds.min) ? bounds.min : null;
  const dataMax = isIsoDate(bounds.max) ? bounds.max : null;
  const latest = dataMax && dataMax < today ? dataMax : dataMax ?? today;
  const earliest = dataMin ?? addDays(latest, -defaultSpan);
  const observedSpan = dataMin && dataMax ? daysBetween(dataMin, dataMax) : defaultSpan;

  let from: string;
  let to: string;
  if (isIsoDate(requested.from) || isIsoDate(requested.to)) {
    from = isIsoDate(requested.from) ? requested.from : addDays(latest, -defaultSpan);
    to = isIsoDate(requested.to) ? requested.to : latest;
  } else if (dataMin && dataMax && observedSpan <= defaultSpan) {
    // Dense first paint: don't leave years of empty gutter when the store is a short cluster.
    from = addDays(dataMin, -30);
    to = addDays(dataMax, 14);
  } else {
    from = addDays(latest, -defaultSpan);
    to = latest;
  }

  if (from > to) {
    const swap = from;
    from = to;
    to = swap;
  }

  // Keep the window intersecting observed data when we have bounds.
  if (dataMin && to < dataMin) to = dataMin;
  if (dataMax && from > dataMax) from = dataMax;

  from = clampIso(from, addDays(earliest, -31), addDays(latest, 31));
  to = clampIso(to, from, addDays(latest, 31));

  let clamped = false;
  if (daysBetween(from, to) > maxSpan) {
    from = addDays(to, -maxSpan);
    clamped = true;
  }

  return { from, to, bounds: { min: dataMin, max: dataMax }, clamped };
}

export function openPresentStart(window: DateWindow, today = todayUtc()): string {
  const presentEnd = window.to < today ? window.to : today;
  const start = addDays(presentEnd, -OPEN_PRESENT_DAYS);
  return start < window.from ? window.from : start;
}

export function assignLane(hint: LaneHint, mode: LaneMode): Lane {
  if (mode === "person") {
    if (hint.personId || hint.personSlug) {
      const id = `person:${hint.personSlug || hint.personId}`;
      return {
        id,
        label: hint.personName || hint.personSlug || "Person",
        kind: "person",
        href: hint.personSlug ? `/people/${hint.personSlug}` : null,
      };
    }
    return { id: "unassigned", label: "Unassigned", kind: "unassigned", href: null };
  }

  if (hint.agencySlug) {
    return {
      id: `agency:${hint.agencySlug}`,
      label: hint.agencyName || hint.agencySlug,
      kind: "agency",
      href: `/agencies/${hint.agencySlug}`,
    };
  }
  if (hint.portfolio) {
    const slug = slugify(hint.portfolio);
    return {
      id: `portfolio:${slug}`,
      label: hint.portfolio,
      kind: "portfolio",
      href: `/atlas?portfolio=${encodeURIComponent(hint.portfolio)}`,
    };
  }
  return { id: "unassigned", label: "Unassigned", kind: "unassigned", href: null };
}

/**
 * Tenures are occupancies. Hearing appearances must not be passed in.
 * This function ignores a parallel appearance list on purpose.
 */
export function tenuresFromRoles(
  roles: TenureInput[],
  appearances?: HearingAppearance[],
): TenureInput[] {
  void appearances;
  return roles.filter((row) => row.id && row.personId && row.source);
}

export function overlapsWindow(
  start: string | null,
  end: string | null,
  from: string,
  to: string,
): boolean {
  const s = start ?? from;
  const e = end ?? to;
  return s <= to && e >= from;
}

export function activeOn(start: string | null, end: string | null, on: string): boolean {
  if (start && start > on) return false;
  if (end && end < on) return false;
  return true;
}

export function occupantsAtDate(tenures: AtlasTenure[], on: string): AsOfOccupant[] {
  return tenures
    .filter((row) => activeOn(row.start, row.end, on))
    .map((row) => ({
      laneId: row.laneId,
      personSlug: row.personSlug,
      personName: row.personName,
      roleType: row.roleType,
      roleTitle: row.roleTitle,
      href: row.href,
      source: row.source,
    }));
}

export function hearingMoments(rows: HearingRollup[], mode: LaneMode): AtlasMoment[] {
  const out: AtlasMoment[] = [];
  for (const row of rows) {
    if (!isIsoDate(row.heldOn)) continue;
    const lane = assignLane(row, mode);
    out.push({
      id: `hearing:${row.id}`,
      laneId: lane.id,
      at: row.heldOn,
      kind: "hearing",
      title: row.title,
      href: row.href,
      status: null,
      meta: {
        segmentCount: row.segmentCount,
        portfolioChips: row.portfolioChipCount,
        agencyChips: row.agencyChipCount,
        takenOnNotice: row.takenOnNoticeCount,
      },
    });
  }
  return out;
}

export function qonMoments(rows: QonEvent[], mode: LaneMode): AtlasMoment[] {
  const out: AtlasMoment[] = [];
  for (const row of rows) {
    const lane = assignLane(row, mode);
    if (isIsoDate(row.askedOn)) {
      out.push({
        id: `qon:${row.id}:asked`,
        laneId: lane.id,
        at: row.askedOn,
        kind: "qon",
        title: row.title,
        href: row.href,
        status: row.status,
      });
    }
    if (isIsoDate(row.answeredOn) && row.answeredOn !== row.askedOn) {
      out.push({
        id: `qon:${row.id}:answered`,
        laneId: lane.id,
        at: row.answeredOn,
        kind: "qon",
        title: `${row.title} (answered)`,
        href: row.href,
        status: "answered",
      });
    }
  }
  return out;
}

export function anaoMoments(rows: AnaoItem[], mode: LaneMode): AtlasMoment[] {
  const out: AtlasMoment[] = [];
  for (const row of rows) {
    if (!isIsoDate(row.publishedOn)) continue;
    const lane = assignLane(row, mode);
    out.push({
      id: `anao:${row.id}`,
      laneId: lane.id,
      at: row.publishedOn,
      kind: "anao",
      title: row.title,
      href: row.href,
      status: null,
    });
  }
  return out;
}

export function isProposedStatus(status: string | null | undefined): boolean {
  return (status ?? "").toLowerCase() === "proposed";
}

export function filterInstruments(
  rows: InstrumentInput[],
  opts: { includeProposed: boolean; focusInstrument?: string | null },
): InstrumentInput[] {
  return rows.filter((row) => {
    if (!isProposedStatus(row.status)) return true;
    if (opts.includeProposed) return true;
    const focus = (opts.focusInstrument ?? "").toLowerCase();
    if (!focus) return false;
    return row.slug.toLowerCase() === focus || row.title.toLowerCase().includes(focus);
  });
}

export function buildArcs(
  claims: ClaimLink[],
  tested: TestedLink[],
  momentIds: Set<string>,
  instrumentIds: Set<string>,
): AtlasArc[] {
  const arcs: AtlasArc[] = [];
  const seen = new Set<string>();

  const push = (arc: AtlasArc) => {
    if (seen.has(arc.id)) return;
    const hasFrom = momentIds.has(arc.fromMomentId);
    const hasTo =
      (arc.toMomentId && momentIds.has(arc.toMomentId)) ||
      (arc.toInstrumentId && instrumentIds.has(arc.toInstrumentId));
    if (!hasFrom || !hasTo) return;
    seen.add(arc.id);
    arcs.push(arc);
  };

  for (const claim of claims) {
    const from = claim.hearingId ? `hearing:${claim.hearingId}` : null;
    if (!from) continue;
    const kind: ArcKind =
      claim.claimType === "taken_on_notice"
        ? "ton"
        : claim.claimType === "assurance"
          ? "assurance"
          : "promise";
    if (claim.qonId) {
      push({
        id: `claim:${claim.id}:qon`,
        fromMomentId: from,
        toMomentId: `qon:${claim.qonId}:asked`,
        toInstrumentId: null,
        kind,
      });
    }
    if (claim.instrumentId) {
      push({
        id: `claim:${claim.id}:instrument`,
        fromMomentId: from,
        toMomentId: null,
        toInstrumentId: claim.instrumentId,
        kind,
      });
    }
  }

  for (const link of tested) {
    const toMoment = link.hearingId
      ? `hearing:${link.hearingId}`
      : link.qonId
        ? `qon:${link.qonId}:asked`
        : link.scrutinyId
          ? `anao:${link.scrutinyId}`
          : null;
    if (!toMoment) continue;
    // Prefer a claim on the same instrument as the from-end; otherwise skip
    // if we cannot find a hearing moment that mentioned it.
    const fromClaim = claims.find((c) => c.instrumentId === link.instrumentId && c.hearingId);
    const fromMomentId = fromClaim?.hearingId ? `hearing:${fromClaim.hearingId}` : null;
    if (!fromMomentId || fromMomentId === toMoment) continue;
    push({
      id: `tested:${link.instrumentId}:${toMoment}`,
      fromMomentId,
      toMomentId: toMoment,
      toInstrumentId: null,
      kind: "tested",
    });
  }

  return arcs;
}

export function laneActivityScore(
  laneId: string,
  tenures: AtlasTenure[],
  moments: AtlasMoment[],
  instruments: AtlasInstrument[],
): number {
  const tenureDays = tenures
    .filter((t) => t.laneId === laneId)
    .reduce((sum, t) => {
      const start = t.start ?? t.end ?? "";
      const end = t.end ?? t.start ?? "";
      if (!start || !end) return sum + 30;
      return sum + Math.max(1, daysBetween(start, end));
    }, 0);
  const momentCount = moments.filter((m) => m.laneId === laneId).length;
  const instrumentCount = instruments.filter((i) => i.laneId === laneId).length;
  return tenureDays / 30 + momentCount * 4 + instrumentCount * 3;
}

export function rankLanes(
  lanes: Lane[],
  tenures: AtlasTenure[],
  moments: AtlasMoment[],
  instruments: AtlasInstrument[],
  pinnedIds: Set<string>,
  limit: number,
): Lane[] {
  const scored = lanes.map((lane) => ({
    lane,
    pin: pinnedIds.has(lane.id) ? 1 : 0,
    score: laneActivityScore(lane.id, tenures, moments, instruments),
  }));
  scored.sort((a, b) => b.pin - a.pin || b.score - a.score || a.lane.label.localeCompare(b.lane.label));
  const kept = scored.slice(0, limit).map((row) => row.lane);
  if (![...kept].some((l) => l.id === "unassigned") && lanes.some((l) => l.id === "unassigned")) {
    // Drop empty unassigned unless it survived ranking.
  }
  return kept.filter((lane) => lane.id !== "unassigned" || scored.find((s) => s.lane.id === lane.id && s.score > 0));
}

export function capsFor(compact: boolean) {
  return compact
    ? { lanes: 6, tenures: 80, moments: 80, instruments: 24, arcs: 16 }
    : { lanes: 20, tenures: 400, moments: 250, instruments: 80, arcs: 40 };
}

export function markMatchesFocus(
  focus: string | null,
  mark: { laneId: string; personSlug?: string | null; href?: string | null; id?: string; slug?: string },
): boolean {
  if (!focus) return true;
  const [kind, ...rest] = focus.split(":");
  const value = rest.join(":").toLowerCase();
  if (!value) return true;
  if (kind === "person") {
    return (
      mark.laneId === `person:${value}` ||
      (mark.personSlug ?? "").toLowerCase() === value ||
      (mark.href ?? "").toLowerCase().includes(`/people/${value}`)
    );
  }
  if (kind === "agency") {
    return mark.laneId === `agency:${value}` || mark.laneId.includes(value);
  }
  if (kind === "instrument") {
    return (mark.slug ?? "").toLowerCase() === value || (mark.id ?? "") === value;
  }
  return true;
}

export type PackedBar = { id: string; row: number };

/** Interval packing so overlapping tenures stack instead of colliding. */
export function packIntervals(items: { id: string; start: string; end: string }[]): PackedBar[] {
  const sorted = [...items].sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end));
  const rowEnds: string[] = [];
  const out: PackedBar[] = [];
  for (const item of sorted) {
    let row = rowEnds.findIndex((end) => end < item.start);
    if (row === -1) {
      row = rowEnds.length;
      rowEnds.push(item.end);
    } else {
      rowEnds[row] = item.end;
    }
    out.push({ id: item.id, row });
  }
  return out;
}
