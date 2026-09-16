import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  assignLane,
  buildArcs,
  filterInstruments,
  hearingMoments,
  occupantsAtDate,
  packIntervals,
  parseAtlasParams,
  resolveWindow,
  tenuresFromRoles,
  type HearingAppearance,
  type TenureInput,
} from "../src/lib/atlas-query.ts";

function role(partial: Partial<TenureInput> = {}): TenureInput {
  return {
    id: partial.id ?? "role-1",
    personId: partial.personId ?? "p1",
    personSlug: partial.personSlug ?? "glyn-davis",
    personName: partial.personName ?? "Glyn Davis",
    roleType: partial.roleType ?? "secretary",
    roleTitle: partial.roleTitle ?? "Secretary",
    start: partial.start ?? "2022-06-06",
    end: partial.end ?? null,
    source: partial.source ?? "aps_leaders",
    href: partial.href ?? "/people/glyn-davis",
    agencySlug: partial.agencySlug ?? "pmc",
    agencyName: partial.agencyName ?? "Department of the Prime Minister and Cabinet",
    portfolio: partial.portfolio ?? "Prime Minister and Cabinet",
  };
}

describe("resolveWindow", () => {
  it("defaults to a bounded span ending at the latest data, never unbounded", () => {
    const window = resolveWindow(
      { min: "2010-01-01", max: "2026-02-01" },
      {},
      { today: "2026-09-16", defaultSpanDays: 366 * 4 },
    );
    assert.equal(window.to, "2026-02-01");
    assert.ok(window.from >= "2021-01-01", window.from);
    assert.ok(window.from <= "2022-03-01", window.from);
    assert.equal(window.clamped, false);
    assert.ok(window.bounds.min === "2010-01-01");
  });

  it("clamps an oversized requested range", () => {
    const window = resolveWindow(
      { min: "2000-01-01", max: "2026-01-01" },
      { from: "2000-01-01", to: "2026-01-01" },
      { maxSpanDays: 366 * 4, today: "2026-09-16" },
    );
    assert.equal(window.to, "2026-01-01");
    assert.equal(window.clamped, true);
    assert.ok(window.from > "2000-01-01");
  });

  it("uses the observed cluster when it is shorter than the default span", () => {
    const window = resolveWindow(
      { min: "2024-02-01", max: "2024-06-15" },
      {},
      { today: "2026-09-16", defaultSpanDays: 366 * 4 },
    );
    assert.equal(window.from, "2024-01-02");
    assert.equal(window.to, "2024-06-29");
  });

  it("swaps inverted from/to", () => {
    const window = resolveWindow(
      { min: "2023-01-01", max: "2025-01-01" },
      { from: "2025-01-01", to: "2023-06-01" },
      { today: "2026-01-01" },
    );
    assert.ok(window.from <= window.to);
  });
});

describe("assignLane", () => {
  it("prefers agency in agency mode, then portfolio", () => {
    const agency = assignLane(
      { agencySlug: "finance", agencyName: "Department of Finance", portfolio: "Finance", personId: "p1" },
      "agency",
    );
    assert.equal(agency.id, "agency:finance");
    assert.equal(agency.kind, "agency");
    assert.equal(agency.href, "/agencies/finance");

    const portfolio = assignLane({ portfolio: "Finance" }, "agency");
    assert.equal(portfolio.id, "portfolio:finance");
    assert.equal(portfolio.kind, "portfolio");

    const none = assignLane({}, "agency");
    assert.equal(none.id, "unassigned");
  });

  it("uses person lanes in person mode", () => {
    const lane = assignLane(
      { personId: "p1", personSlug: "katy-gallagher", personName: "Katy Gallagher", agencySlug: "finance" },
      "person",
    );
    assert.equal(lane.id, "person:katy-gallagher");
    assert.equal(lane.kind, "person");
    assert.equal(lane.href, "/people/katy-gallagher");
  });
});

describe("tenuresFromRoles — appearance is not occupancy", () => {
  it("returns sourced person_roles and ignores hearing_people", () => {
    const appearances: HearingAppearance[] = [
      { hearingId: "h1", personId: "witness-only" },
      { hearingId: "h1", personId: "p1" },
    ];
    const roles = [role()];
    const tenures = tenuresFromRoles(roles, appearances);
    assert.equal(tenures.length, 1);
    assert.equal(tenures[0].personId, "p1");
    assert.equal(tenures[0].source, "aps_leaders");
  });

  it("does not invent a tenure from an Estimates appearance alone", () => {
    const appearances: HearingAppearance[] = [{ hearingId: "h-estimates", personId: "official-in-room" }];
    const tenures = tenuresFromRoles([], appearances);
    assert.deepEqual(tenures, []);
  });

  it("drops role rows that lack a person or source", () => {
    const tenures = tenuresFromRoles([
      role({ id: "ok" }),
      role({ id: "no-source", source: "", personId: "p2" }),
      role({ id: "no-person", personId: "" }),
    ]);
    assert.equal(tenures.length, 1);
    assert.equal(tenures[0].id, "ok");
  });
});

describe("moments and occupants", () => {
  it("rolls hearings to one moment each and never emits a segment node", () => {
    const moments = hearingMoments(
      [
        {
          id: "h1",
          slug: "fpa-2024-02",
          title: "Finance Estimates",
          heldOn: "2024-02-12",
          portfolio: "Finance",
          href: "/hearings/fpa-2024-02",
          segmentCount: 10_412,
          portfolioChipCount: 2,
          agencyChipCount: 4,
          takenOnNoticeCount: 7,
        },
      ],
      "agency",
    );
    assert.equal(moments.length, 1);
    assert.equal(moments[0].id, "hearing:h1");
    assert.equal(moments[0].kind, "hearing");
    assert.equal(moments[0].meta?.segmentCount, 10_412);
  });

  it("lists role-at-date occupants from tenures only", () => {
    const occupants = occupantsAtDate(
      [
        { ...role({ id: "open", start: "2022-01-01", end: null }), laneId: "agency:pmc" },
        { ...role({ id: "ended", personId: "p2", start: "2018-01-01", end: "2021-12-31" }), laneId: "agency:pmc" },
        { ...role({ id: "later", personId: "p3", start: "2025-01-01", end: null }), laneId: "agency:pmc" },
      ],
      "2023-06-01",
    );
    assert.equal(occupants.length, 1);
    assert.equal(occupants[0].personName, "Glyn Davis");
  });
});

describe("instruments and arcs", () => {
  it("hides proposed instruments unless included or focused", () => {
    const rows = [
      {
        id: "i1",
        slug: "bp2-measure",
        title: "A measure",
        type: "measure",
        status: "published",
        start: "2024-07-01",
        end: null,
        href: "/accountability/instruments/bp2-measure",
      },
      {
        id: "i2",
        slug: "guessed-program",
        title: "Guessed program",
        type: "program",
        status: "proposed",
        start: "2024-02-01",
        end: null,
        href: "/accountability/instruments/guessed-program",
      },
    ];
    assert.equal(filterInstruments(rows, { includeProposed: false }).length, 1);
    assert.equal(filterInstruments(rows, { includeProposed: true }).length, 2);
    assert.equal(
      filterInstruments(rows, { includeProposed: false, focusInstrument: "guessed-program" }).length,
      2,
    );
  });

  it("keeps sparse arcs only when both ends are in the payload", () => {
    const arcs = buildArcs(
      [
        { id: "c1", claimType: "taken_on_notice", hearingId: "h1", qonId: "q1", instrumentId: null },
        { id: "c2", claimType: "promise", hearingId: "h-missing", qonId: "q1", instrumentId: null },
      ],
      [],
      new Set(["hearing:h1", "qon:q1:asked"]),
      new Set(),
    );
    assert.equal(arcs.length, 1);
    assert.equal(arcs[0].kind, "ton");
    assert.equal(arcs[0].fromMomentId, "hearing:h1");
    assert.equal(arcs[0].toMomentId, "qon:q1:asked");
  });
});

describe("parseAtlasParams and packing", () => {
  it("parses lane, toggles, and ISO dates", () => {
    const params = parseAtlasParams(
      new URLSearchParams("lane=person&includeProposed=1&qon=0&from=2023-01-01&agency=finance"),
    );
    assert.equal(params.lane, "person");
    assert.equal(params.includeProposed, true);
    assert.equal(params.qon, false);
    assert.equal(params.anao, true);
    assert.equal(params.from, "2023-01-01");
    assert.equal(params.agency, "finance");
  });

  it("stacks overlapping intervals onto separate rows", () => {
    const packed = packIntervals([
      { id: "a", start: "2022-01-01", end: "2024-01-01" },
      { id: "b", start: "2023-01-01", end: "2025-01-01" },
      { id: "c", start: "2024-06-01", end: "2024-12-01" },
    ]);
    const byId = Object.fromEntries(packed.map((p) => [p.id, p.row]));
    assert.equal(byId.a, 0);
    assert.equal(byId.b, 1);
    assert.ok(byId.c === 0 || byId.c === 1);
  });
});
