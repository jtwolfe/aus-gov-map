# Responsibility Atlas

A **left → right past–future temporal duty view** of the Accountability
Foundation. Researchers inspect what was worked on, for how long, and by
whom — using sourced occupancies, hearings, QoNs, ANAO items, and
instruments. It does not assign guilt.

Route: `/atlas`. API: `GET /api/atlas`. This is a reading-room lens on
the same schema as [`docs/accountability-map.md`](accountability-map.md),
not a second graph.

## Purpose

- Show **multi-year structure** from real rows: `person_roles`,
  `hearings`, `qons`, `scrutiny_items`, `instruments`, `claims`.
- Make **role-at-date** spatial: a vertical as-of cursor crosses the
  lanes and lists occupants in view.
- Keep **Estimates appearances** as dated moments. They never become
  tenure bars.
- Let a researcher **filter** to an agency, person, or instrument and
  jump to the underlying dossier.

## Non-goals

- Full historical Federation atlas (no unbounded world history in one
  paint).
- Force-directed or 3D / WebGL “hairball” graphs.
- Invented people, roles, findings, or automated guilt labels.
- Treating “sat at Estimates” as occupancy.
- Sitting-calendar futures unless a sourced calendar exists (this
  scaffold does not; the future zone is omitted).

## Visual grammar

X-axis is **time** (past left, present / latest data right). Y-axis is
**swimlanes**.

| Mark | Meaning | Source |
| --- | --- | --- |
| **Lane** | Portfolio / agency (default) or a person | `agencies.portfolio` / `agencies.slug`, or `people` |
| **Tenure bar** | Occupancy of a seat | `person_roles` only (`handbook`, `aps_leaders`, …) |
| **Moment** | Dated scrutiny point | Hearing (segments rolled up), QoN asked/answered, ANAO item |
| **Instrument thread** | Longer band for a measure / program / contract | `instruments` dates; proposed is dashed and off by default |
| **Arc** | Sparse promise / TON / tested link | `claims` → later QoN / hearing / instrument when `qon_id`, `instrument_id`, or `tested_in` exists |
| **Scrubber** | Vertical as-of line | Client cursor; optional `asOf=` on the API |
| **Focus** | Dim unrelated marks | `focus=person:slug\|agency:slug\|instrument:slug` |

### Honesty (must stay in the UI)

- Sitting in Estimates is **not** a tenure.
- No automated guilt labels.
- Hansard, QoNs, and ANAO items are sourced public records; attribute
  the Commonwealth.
- Proposed instruments are visually distinct and toggleable.

### Zones

| Zone | Rule |
| --- | --- |
| Settled past | Dates before the open-present window |
| Open present | Roughly the last 90 days through today: overdue QoNs, open-ended roles, live contracts |
| Future | **Omitted** — no sitting calendar in this schema |

## Query contract

`GET /api/atlas`

| Param | Meaning |
| --- | --- |
| `from`, `to` | Inclusive `YYYY-MM-DD` window. Default is a **bounded** range covering existing hearings + roles (see Performance). |
| `agency` | Agency slug or name (`ILIKE`) |
| `portfolio` | Portfolio string (`ILIKE`) |
| `person` | Person slug or name (`ILIKE`) |
| `instrument` | Instrument slug or title (`ILIKE`) |
| `lane` | `agency` (default) or `person` |
| `includeProposed` | `0` (default) or `1` |
| `asOf` | Optional date; when set, payload includes `asOf` occupants |
| `qon` | `0` to omit QoN moments (default `1`) |
| `anao` | `0` to omit ANAO moments (default `1`) |
| `arcs` | `0` to omit arcs (default `1`) |
| `compact` | `1` for mini-atlas caps (fewer lanes / marks) |

### Response shape

```json
{
  "source": "postgres",
  "ready": true,
  "needed": { "note": "...", "sources": [], "tables": [] },
  "window": { "from": "2022-07-01", "to": "2026-06-30", "bounds": { "min": "...", "max": "..." } },
  "laneMode": "agency",
  "lanes": [{ "id": "agency:pmc", "label": "Department of the Prime Minister and Cabinet", "kind": "agency", "href": "/agencies/pmc" }],
  "tenures": [{
    "id": "…",
    "laneId": "agency:pmc",
    "personId": "…",
    "personSlug": "glyn-davis",
    "personName": "…",
    "roleType": "secretary",
    "roleTitle": "Secretary",
    "start": "2022-06-06",
    "end": null,
    "source": "aps_leaders",
    "href": "/people/glyn-davis"
  }],
  "moments": [{
    "id": "hearing:…",
    "laneId": "portfolio:finance",
    "at": "2025-02-24",
    "kind": "hearing",
    "title": "…",
    "href": "/hearings/…",
    "status": null,
    "meta": { "segmentCount": 120, "portfolioChips": 3 }
  }],
  "instruments": [{
    "id": "…",
    "laneId": "agency:finance",
    "title": "…",
    "type": "contract",
    "status": "active",
    "start": "2024-07-01",
    "end": null,
    "href": "/accountability/instruments/…"
  }],
  "arcs": [{
    "id": "…",
    "fromMomentId": "hearing:…",
    "toMomentId": "qon:…:asked",
    "toInstrumentId": null,
    "kind": "ton"
  }],
  "asOf": {
    "date": "2025-02-24",
    "occupants": [{ "laneId": "…", "personName": "…", "roleType": "secretary", "href": "/people/…" }]
  }
}
```

Moment `kind`: `hearing` | `qon` | `anao`. QoN asked vs answered are
separate moment ids (`qon:{id}:asked`, `qon:{id}:answered`) sharing one
ledger row. Arc `kind`: `promise` | `assurance` | `ton` | `tested`.

Fixture mode (no `DATABASE_URL`, or foundation tables missing) returns
`ready: false`, empty arrays, and a needed-hint that points at
Accountability — **no invented tenures**.

## Focus and filter URL params

The `/atlas` page is a shareable GET form. The same keys are accepted as
query params (plus client-only cursor state):

```
/atlas?from=2023-01-01&to=2026-06-30&lane=agency&agency=finance
  &person=&instrument=&includeProposed=0&qon=1&anao=1&arcs=1
  &asOf=2024-11-18&focus=person:glyn-davis
```

| Key | Client behaviour |
| --- | --- |
| Filter keys | Submit reloads payload |
| `asOf` | Scrubber; occupants computed from loaded tenures (API also accepts it) |
| `focus` | Dim marks that do not share person / agency / instrument |

Mini-atlas uses the same API with `compact=1` and a tight filter
(`person`, `agency`, or `instrument`).

## Performance strategy

- **Windowing.** Default window is the overlap of observed data bounds
  (hearings + `person_roles` + QoNs + ANAO + instruments), then **clamped
  to four years** ending at the latest bound (padded). Callers may pass
  `from`/`to`; the server still clamps to eight years. Never select
  unbounded history.
- **Aggregation.** `hearing_segments` are **not** plotted. They roll up
  to one hearing-level moment; tooltip may show portfolio / agency chip
  counts (`v_atlas_hearing_moments` when `011_atlas.sql` is applied).
- **Lane cap.** Rank lanes by activity in the window; keep 20 (6 when
  `compact=1`). Filter-matching lanes are pinned.
- **Mark caps.** Tenures 400, moments 250, instruments 80, arcs 40
  (half those when compact). Arcs only when both ends are in the
  payload.
- **Proposed instruments.** Excluded unless `includeProposed=1` or the
  focused instrument is proposed.

## Plug-in to Accountability lenses

| Lens | Atlas relationship |
| --- | --- |
| Role at date | Scrubber cross-section is the same occupancy rule (`start <= asOf` and open or `end >= asOf`) |
| Promise → receipt | Sparse arcs from `claims` |
| QoN debt | QoN moments + open/overdue styling in the present zone |
| Chain completeness | Instrument threads; missing duty links stay gaps, not findings |
| Instruments explorer | Threads on the atlas; dossier at `/accountability/instruments/[slug]` |
| Agencies / people | Mini-atlas on those pages |

Nav: **Atlas** sits next to Accountability. The Accountability overview
links here as the temporal reading room.

## Acceptance criteria (“real value”)

A researcher can:

1. Open `/atlas` and see multi-year structure from real DB fields (or a
   clear empty state that names which ingest fills which layer — never a
   blank storm, never invented officials).
2. Filter to an agency and see secretary / minister bars plus Estimates
   moments.
3. Scrub to a date and see who held roles in the visible lanes.
4. Toggle arcs / QoN and open an answered or overdue question in
   context (href to dossier or `source_url`).
5. Jump to hearing, person, agency, and instrument pages.

Tests must prove: date windowing, lane assignment, and **no tenure from
hearing appearance alone**.
