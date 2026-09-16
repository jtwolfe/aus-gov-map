# Laws and precedent (Stage 3a)

Stage 2 mapped **duty**: who held which office when, and which public
instrument they were accountable or responsible for. Stage 3a puts
**Bills and Acts on that same spine** so a researcher can follow

```
bill → Act → sourced division → (later) appropriation / contract → court / ANAO
```

on one accountability model and the Responsibility Atlas. Precedent
(High Court / Federal Court) is a **sourced scrutiny / outcome layer**
linked to Acts. It is not a guilt score.

This document is the foundation. Tables (`012_laws.sql`,
`013_precedent.sql`), ingest adapters (`legislation`, `theyvoteforyou`,
`judgments`), `/laws` dossiers, and Atlas threads all follow it. Sparse
data is expected; empty UI states name **which ingest fills which
layer**.

Companion specs: [`accountability-map.md`](accountability-map.md),
[`responsibility-atlas.md`](responsibility-atlas.md).

## How this plugs into Stage 2

Bills and Acts are first-class **instruments**. They reuse
`instruments`, `instrument_links`, `scrutiny_items`, and `outcomes`.
Votes get a typed ledger (`divisions`, `division_votes`) because a
division is a many-person event, not a single edge. Judgments land as
`scrutiny_items` (`item_type = judgment`) plus sourced links.

| Stage 2 object | Stage 3a use |
| --- | --- |
| `instruments` (`bill` already allowed) | Add `act`. Status catalog for law: `introduced` · `passed` · `commenced` · `amended` · `repealed` · `as_made` · `in_force` (other instruments keep `proposed` / `sourced` / `unknown`). |
| `instrument_links` | `voted_on` (person → bill, when a resolved voter exists); `tested_in` (hearing / QoN / ANAO → instrument); **new** `construes` · `invalidates` · `upholds` (judgment → Act). `funded_by` stays defined, **deferred** as a fill. |
| `scrutiny_items` | Divisions may also appear as `item_type = division`. Judgments use `judgment`. |
| `outcomes` | Optional sourced court / register signals (`court_holding`, `legislation_status`). Descriptive only. |
| `people` | Shared person key. Vote rows resolve to existing people when names match. **Do not invent MPs.** |
| Atlas | Act / Bill **threads** on the same instrument band. Votes stay on dossiers (not Atlas moments). Judgments stay on dossiers. |

```
Person ──HELD_ROLE_DURING──► Role ──► Agency
  │
  │ VOTED_ON (sourced division only)
  ▼
Instrument (bill | act) ◄──CONSTRUES / UPHOLDS / INVALIDATES── ScrutinyItem (judgment)
  │         │
  │         └──FUNDED_BY──► Instrument (appropriation / measure)   [deferred]
  │
  ├──TESTED_IN──► Hearing / QoN / ANAO
  └── Division ── division_votes (aye / no / abstain)
```

## Entity model

### 1. Law instruments (Bill / Act)

A **Bill** is a proposed law. An **Act** is a law as made or as
compiled. Both are `instruments` rows.

| Field | Use |
| --- | --- |
| `instrument_type` | `bill` or `act` |
| `status` | Law catalog above. `proposed` remains the Stage 2 text-candidate flag and stays visually distinct. |
| `identifiers` (JSONB) | FRL id (e.g. `C2013A00123`), series, year, number, collection (`Act` / `Bill` / `Compilation`), compilation flag, register URL |
| `announced_on` | Introduction / as-made date when the source states it |
| `commenced_on` | Commencement when the source states it |
| `ended_on` | Repeal / sunset when the source states it |
| `source` / `source_url` | Federal Register of Legislation (or APH bill page if that is all the adapter has) |
| `source_key` | Stable upsert key, typically `frl:{frl_id}` or `frl:bill:{slug}` |

A Bill and the Act it became are **two instruments** when both exist.
Link them later with `instrument_links.link_kind = other` (or a future
`became`) only when a source states the relationship. This pass does
not invent “this Bill became that Act” from title similarity alone;
fixtures may state it in `identifiers.related_frl_id` as a hint.

### 2. Divisions / votes

A **division** is a recorded parliamentary vote. Sitting in Estimates
is still **not** a vote and **not** tenure.

| Table | Role |
| --- | --- |
| `divisions` | One row per sourced division: house, date, number, title, aye/no/abstain counts, optional `instrument_id`, optional `scrutiny_item_id`, They Vote For You / Hansard identifiers |
| `division_votes` | Person ↔ division ↔ `aye` \| `no` \| `abstain` \| `absent`. Always stores the **published name**. `person_id` is set only when that name resolves to an existing `people` row. |

`VOTED_ON` on `instrument_links` is written when both the instrument
and the person resolved. It is a convenience edge for the duty graph;
the ledger of record is `division_votes`.

Vote values come from They Vote For You (or a cited Hansard division).
Whip guesses, rebellion flags, and policy scores from TVFY are stored
in `identifiers` when present — they are **that project's** labels,
not ours.

### 3. Judgments as scrutiny / outcomes

A **judgment** is a dated, sourced court decision that **cites** a
mapped Act. MVP is a small High Court / Federal Court fixture set.

| Store | Meaning |
| --- | --- |
| `scrutiny_items.item_type = judgment` | Citation, court, date, catchwords, source URL (Jade / AustLII / court site) |
| `instrument_links` | `construes` (interprets), `upholds` (holds a provision valid), `invalidates` (holds a provision invalid) — only when the published catchwords / headnote support that verb |
| `outcomes` | Optional `court_holding` with `signal = unknown` unless the source uses language we already allow (`met` / `unmet` / `partial` / `adverse`). Default is `unknown`. |

The product **does not** say a minister, official, or party is guilty,
liable, or corrupt. A holding that a provision is invalid is a
**sourced legal event**, attributed to the court.

## Critical edges

| Edge | From → to | Question it answers | Status |
| --- | --- | --- | --- |
| `VOTED_ON` | Person → Instrument (usually a bill) | How did this person vote, if a sourced division exists? | **Filled** when TVFY + resolved person + mapped bill |
| `CONSTRUES` | Judgment → Act | Which Act does this decision interpret? | **Filled** from fixtures / later Jade-AustLII |
| `INVALIDATES` | Judgment → Act | Which provision / application did the court hold invalid? | **Filled** only when the published holding says so |
| `UPHOLDS` | Judgment → Act | Which provision did the court hold valid? | Same honesty rule |
| `TESTED_IN` | Instrument → Hearing / QoN / ANAO | Where was the law later examined in Parliament or audit? | Existing; filled when those adapters link |
| `FUNDED_BY` | Instrument → Instrument | Which appropriation / measure funded a contract or program? | **Deferred** (Budget / AusTender already exist; law↔money join is Stage 3b) |
| `ACCOUNTABLE_FOR` / `RESPONSIBLE_OFFICIAL` | Person → Instrument | Duty on a Bill / Act | Existing; empty until a source names the minister / official |

Every edge needs a `source`.

## Public sources

| Source | What it grounds | Adapter | Live vs fixture |
| --- | --- | --- | --- |
| [Federal Register of Legislation](https://www.legislation.gov.au) | Commonwealth Bills / Acts as instruments; FRL id, series, year, number, status, register URL | `legislation` | Live title / browse pages when reachable; otherwise `fixtures/live/legislation/` |
| [They Vote For You](https://theyvoteforyou.org.au/help/api) | House/Senate divisions and member votes | `theyvoteforyou` | `divisions.json` + per-division JSON when reachable (`THEYVOTEFORYOU_KEY` optional); otherwise `fixtures/live/tvfy/` |
| High Court / Federal Court via [Jade](https://jade.io), [AustLII](https://www.austlii.edu.au), or [hcourt.gov.au](https://www.hcourt.gov.au) | Judgments that cite mapped Acts | `judgments` | **Fixture MVP**. Live scrape is follow-up (licensing + HTML instability). |
| Stage 1–2 sources | Hearings, QoNs, ANAO, Budget, AusTender | unchanged | Unchanged |

Attribute the Commonwealth (FRL, Hansard, court) and They Vote For You
when displaying their rows. Jade / AustLII citations are pointers to
published judgments, not a republication of the full text.

### Why fixtures are first-class

FRL and TVFY are public, but datacentre IPs are often blocked or
rate-limited. Adapters **must** degrade to committed fixtures and say
so in `SourceBatch.meta.transport`. Fixtures use **real public
identifiers and dates**. They do not invent officials, vote positions,
or holdings. Named votes in the TVFY fixture are a **short published
excerpt**, not a full division list.

## Atlas integration

The Atlas already plots `instruments` as threads. Stage 3a:

- Includes `bill` and `act` threads in the default instrument query
  (same window / caps / proposed toggle).
- Points those threads at `/laws/[slug]` (other types stay on
  `/accountability/instruments/[slug]`).
- **Keeps votes and judgments on dossiers**, not as Atlas moments.
  A division is a many-person event; plotting every aye/no would
  crowd the temporal view and imply a score. A researcher opens the
  law page (or the person page) for the vote table, then uses
  mini-atlas for the surrounding duty context.

Default Atlas window is unchanged (bounded, ~four years).

Mini-atlas on a law dossier uses `GET /api/atlas?instrument={slug}&compact=1`.

## Web surfaces

| Route | Role |
| --- | --- |
| `/laws` | Bills and Acts only. Empty state names `legislation`, `theyvoteforyou`, `judgments`. |
| `/laws/[slug]` | Law dossier: identifiers, status timeline, vote summary, linked judgments, linked hearings / QoN / ANAO / contracts when present, mini-atlas. |
| `/accountability/instruments/[slug]` | Still works for every type; Bills/Acts link through to `/laws/[slug]`. |
| `/people/[slug]` | Vote list when `division_votes` resolved that person. |
| `/atlas` | Act/Bill threads as above. |
| Search | Instrument / law hits when the `instruments` table exists. |

Nav: **Laws** next to Accountability / Atlas.

## Honesty / non-goals

- **No automated illegality or guilt labels.** Holdings are the court's
  words, attributed, with `construes` / `upholds` / `invalidates`
  only when the source supports that verb.
- **No invented officials, MPs, or votes.** Unresolved voters stay as
  published names with `person_id` null. The adapter never
  `INSERT`s into `people` for a vote.
- **Appearance ≠ vote ≠ tenure.** Estimates attendance does not create
  a division row or a `VOTED_ON` edge.
- **Proposed / asserted stay visually distinct.** Regex bill candidates
  from Officials remain `status = proposed` and dashed on the Atlas.
  FRL rows are sourced register facts.
- **FUNDED_BY is deferred.** Do not infer that an Act funded a
  contract from title overlap.
- **Hansard / TVFY are not ground truth of “what the law means”.**
  They record what was said or how a chamber divided.
- **Jade / AustLII / court sites are citations**, not a dump of the
  full judgment in this repo.

## Ingest

```bash
# Dry-run (no Postgres). Uses fixtures when live fetch fails.
python -m aus_gov_ingest run --source legislation --limit 10 --dry-run
python -m aus_gov_ingest run --source theyvoteforyou --limit 5 --dry-run
python -m aus_gov_ingest run --source judgments --dry-run

# Persist
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
  python -m aus_gov_ingest run --source legislation --no-graph
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
  python -m aus_gov_ingest run --source theyvoteforyou --limit 20 --no-graph
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
  python -m aus_gov_ingest run --source judgments --no-graph
```

Makefile: `make ingest-laws` (dry-run fixtures) and the same targets
without `DRY_RUN=1` to persist.

Schema: `make db-apply` (now `004`–`013` plus analytics views).

## Acceptance criteria

A researcher can:

1. Open `/laws` and see sourced Bills/Acts, or a clear empty state that
   names `legislation` (and optionally `theyvoteforyou` / `judgments`).
2. Open an Act or Bill dossier and see status, FRL identifiers, source
   URL, any vote summary, any linked judgments, and an embedded
   mini-atlas filtered to that instrument.
3. See votes on a **person** page only when that person already exists
   and a division_vote resolved to them.
4. Run ingest offline from fixtures; live fetch is best-effort.
5. Trust that nothing invents MPs, vote positions, or legal conclusions.

Tests must prove: upsert keys are stable, votes do not create people,
and date parsing does not invent commencements.
