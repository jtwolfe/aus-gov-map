# Accountability map (Stage 2)

Stage 1 mapped **who appeared** at Senate committees and Estimates hearings.
Stage 2 turns that record into a **decision / duty map**: a sourced graph of
who held which office when, which public instrument they were accountable
or responsible for, how those instruments were scrutinised, and what
signals later appeared — without labelling anyone “guilty”.

This document is the foundation. Tables, Cypher, ingest adapters, and the
Accountability lenses all follow it. Sparse data is expected; empty UI
states should say **what source is missing**, not invent a conclusion.

## How Stage 1 hearings plug in

A hearing is already a dated event with people (`hearing_people`), text
(`chunks`), and a committee. Stage 2 treats that event as **scrutiny**,
not as proof.

| Stage 1 object | Duty-map use |
| --- | --- |
| `hearings` + `held_on` | Date of a decision-adjacent event. Join to `person_roles` to ask *who held the seat that day*. |
| `hearing_people.role` | Appearance in the room (`minister`, `official`, …). Not the same as a Handbook / AAO tenure. |
| `chunks` + `speaker_name` | Spans for `claims` (promise, assurance, taken on notice, denial). Hansard is the citation, not the verdict. |
| `people` | Shared person key. Handbook tenures and Estimates appearances **join here** — do not invent a second people table. |
| `v_people_across_estimates` | Starter “who keeps appearing” signal; Stage 2 keeps it as a coverage metric, not a charge. |

Typical join: hearing date → overlapping `person_roles` → `roles` /
`agencies` → `instruments` linked as `ACCOUNTABLE_FOR` or
`RESPONSIBLE_OFFICIAL` → `scrutiny_items` / `qons` / `claims` that
**test** a prior promise.

```
Person ──HELD_ROLE_DURING──► Role ──(portfolio / agency)──► Agency
  │                            │
  │ APPEARED_AT (Stage 1)      │ ACCOUNTABLE_FOR / RESPONSIBLE_OFFICIAL
  ▼                            ▼
Hearing ◄── hearing_segment ── Instrument ◄──FUNDED_BY── Instrument
  │              │                    │
  │ chunks       │                    │ PROMISED_IN / TESTED_IN / VOTED_ON
  ▼              ▼                    ▼
Claim         ScrutinyItem          QoN / ANAO / Division
                                      │
                                      ▼
                                   Outcome (signal, sourced)
```

## Entity layers

### 1. Actors

Existing `people` rows: senators, members, ministers, secretaries, agency
staff, witnesses. Identity stays here. Stage 2 adds **time-bounded duty**,
not a parallel cast list.

Handbook extract tables (`handbook_entries`, `handbook_roles`,
`handbook_tenure`) remain the **provenance** store for Parliamentary
Handbook payloads. When a real extract is wired, those rows should
**promote** into `roles` / `person_roles` (and optionally `agencies`)
rather than become a second person graph.

### 2. Time-bounded Roles

A **Role** is a seat or office (Minister for X, Secretary of Y, committee
chair, MP for Z). A **person_role** is occupancy: this person, this seat,
these dates, this source.

`role_type` (shared catalog + occupancy):

| Type | Typical source |
| --- | --- |
| `minister` | Handbook ministry records, AAO, ministry lists |
| `shadow` | Handbook shadow ministry records |
| `secretary` | AAO, department annual reports, Estimates appearance titles |
| `deputy` | Same as secretary / minister, deputy occupancy |
| `committee` | Handbook committee membership, Senate committee pages |
| `mp` | Handbook tenure (House) |
| `senator` | Handbook tenure (Senate) |
| `agency_head` | AAO, agency sites, Estimates |
| `other` | Only when the source does not fit the types above |

`portfolio` / `organisation` / `agency_id` sit on both the role catalog
and the occupancy so a messy source can be stored before a clean Agency
row exists.

### 3. Instruments

A public **thing that can be decided, funded, or delivered**:

`program` · `measure` · `bill` · `contract` · `grant` · `policy` · `other`

Identifiers live in `instruments.identifiers` (JSONB): bill number, AusTender
CN, GrantConnect GA, PBS measure id, appropriation line. Amounts and dates
are nullable. An instrument without an accountable minister or responsible
official is a **chain gap**, not a finding of fault.

### 4. Scrutiny events

`scrutiny_items.type`:

| Type | Meaning |
| --- | --- |
| `hearing_segment` | A dated hearing (or a span of one) — Stage 1 plug-in |
| `qon` | Question on notice (Estimates or chamber) |
| `anao` | Auditor-General report or extract |
| `inquiry_report` | Committee inquiry report |
| `division` | Recorded vote (TheyVoteForYou / Hansard division) |
| `other` | Sourced scrutiny that does not fit yet |

`qons` is the typed QoN ledger (status, due date, asker, answering
minister / agency). A QoN may point at a `scrutiny_items` row and at a
hearing. `claims` optionally capture a speaker’s **text span** in a chunk:
`promise`, `assurance`, `taken_on_notice`, `denial`.

### 5. Outcomes / signals

`outcomes` are **stubs**: a dated, sourced signal attached to an
instrument (`receipt`, `audit_finding`, `delivery`, `lapse`, …).
`signal` is descriptive (`met`, `unmet`, `partial`, `adverse`,
`unknown`) and **must** carry `source` / `source_url`. Outcomes are not
verdicts.

## Critical edges

Stored in Postgres as `instrument_links` (and occupancy as `person_roles`)
and in Neo4j as the named relationships. Every edge needs a `source`.

| Edge | From → to | Question it answers |
| --- | --- | --- |
| `HELD_ROLE_DURING` | Person → Role | Who occupied this seat between these dates? |
| `ACCOUNTABLE_FOR` | Person (minister / cabinet seat) → Instrument | Who was the accountable authority in the political sense *according to the source*? |
| `RESPONSIBLE_OFFICIAL` | Person (secretary / agency head / SES) → Instrument | Who was the public-service responsible officer *according to the source*? |
| `PROMISED_IN` | Claim → Instrument | Where was a delivery or assurance stated? |
| `TESTED_IN` | Instrument → ScrutinyItem | Where was that instrument later examined (hearing, QoN, ANAO, division)? |
| `VOTED_ON` | Person → Instrument (usually a bill) | How did this person vote, if a sourced division exists? |
| `FUNDED_BY` | Instrument → Instrument | Which appropriation, measure, or program funded this contract / grant? |

`instrument_links.link_kind` also allows `mentioned` for weak, sourced
co-occurrence (a hearing mentioned a program) without implying duty.

## Explicit non-goals

- **No automated “guilt” labels.** The product traces duty, dates, and
  sources. It does not score integrity or name a culprit.
- **Sourced chains only.** A role, link, or outcome without a `source`
  (Handbook, AAO, Hansard `source_key`, ANAO URL, AusTender CN, …) is
  incomplete data, not a displayable fact.
- **Hansard is not ground truth.** Officials are a contemporaneous
  transcript of what was *said*. They are evidence of claims and
  appearances. They are not a finding, an AAO, or a contract.
- **No invented officials or tenures.** Empty Handbook / QoN / ANAO
  tables are correct. Fixture hearing prose stays labeled sample.
- **Appearance ≠ occupancy.** Sitting at the table as “official” does
  not create a `secretary` tenure.
- **Reshuffle is fog, not motive.** Short or overlapping tenures are a
  *coverage* metric (`reshuffle fog`), not an implication of evasion.

## Public sources

| Source | What it grounds | Adapter |
| --- | --- | --- |
| [Parliamentary Handbook](https://handbook.aph.gov.au) / [handbookapi.aph.gov.au](https://handbookapi.aph.gov.au) | People, tenures, ministries, shadow ministries | `handbook` (live OData + fixture fallback; promotes into `person_roles`) |
| Administrative Arrangements Order (AAO), PMC | Which department / minister owns which function | `agencies` stub list (official names); AAO dump later |
| Senate Estimates / chamber Questions on Notice | QoN debt, taken-on-notice claims | `qon` (EQON search → `qons`); TON markers → `claims` |
| [ANAO](https://www.anao.gov.au) | Audit gravity, outcome signals | `anao` (stub) |
| Budget Papers / [PBS](https://www.finance.gov.au/publications/portfolio-budget-statements) | Measures, programs, amounts | `budget_measure` (stub) |
| [AusTender](https://www.tenders.gov.au) | Contracts, CN identifiers, suppliers, amounts | `austender` (stub) |
| [GrantConnect](https://www.grants.gov.au) | Grants | Documented; no adapter yet |
| [Federal Register of Legislation](https://www.legislation.gov.au) | Bills / Acts as instruments | Documented; no adapter yet |
| [TheyVoteForYou](https://theyvoteforyou.org.au/help/api) | Divisions, `VOTED_ON` | Documented; no adapter yet |
| Stage 1 APH Hansard JSON | Hearings, chunks, claims spans | Existing `estimates` / `aph_transcript_file` |

Companion endpoints used by the Handbook adapter (OData, as consumed by
[ausPH](https://github.com/palesl/ausPH) and OpenSanctions):

- `https://handbookapi.aph.gov.au/api/individuals`
- `https://handbookapi.aph.gov.au/api/ministryrecords`
- `https://handbookapi.aph.gov.au/api/shadowministryrecords`
- `https://handbookapi.aph.gov.au/api/StatisticalInformation/Ministries`
- `https://handbookapi.aph.gov.au/api/StatisticalInformation/SittingDaysForYear?year=`
- Current parliamentarians (APH, not Handbook): `https://www.aph.gov.au/api/parliamentarian/`

## Metrics

Computed as SQL views (and Cypher twins). All are **coverage / process**
measures. None are guilt scores.

| Metric | Definition | View / query |
| --- | --- | --- |
| **QoN debt** | Open or overdue questions, counted by portfolio and answering agency | `v_accountability_qon_debt` |
| **Promise → receipt** | Claims of type promise / assurance / taken_on_notice joined to instruments and later outcomes | `v_accountability_promise_receipt` |
| **Role at decision** | Occupancy overlapping an instrument date or a hearing `held_on` | API over `person_roles` + hearings |
| **Audit gravity** | ANAO (and similar) scrutiny items / outcomes per instrument or agency | `v_accountability_audit_gravity` |
| **Reshuffle fog** | Distinct occupants of the same role or portfolio in a window; short tenures | `v_accountability_reshuffle_fog` |
| **Chain completeness** | Instruments missing `accountable_for` and/or `responsible_official` links | `v_accountability_chain_completeness` |
| **Estimates continuity** | People appearing at more than one Estimates hearing (Stage 1.1, retained) | `v_people_across_estimates` / `v_accountability_people_estimates` |

## Web lenses

`/accountability` is the reading room for these metrics. Each lens must
render with **zero rows**: explain which ingest source and which tables
fill it. Copy must not invent political conclusions.

## Schema and apply

- Additive migration: `infra/postgres/007_accountability.sql`
- Pipeline extensions: `infra/postgres/008_hearing_segments.sql` (`hearing_segments`, instrument `status`/`confidence`, `qons.identifiers`)
- Handbook stub remains `005_handbook.sql` (extended, not replaced)
- Views: `infra/postgres/analytics/accountability_*.sql` plus `v_qon_by_portfolio` alias
- Existing volumes: `make db-apply`
- Graph: `infra/neo4j/constraints.cypher` + `infra/neo4j/queries/accountability/`

## What is real vs proposed (pipeline fill)

| Layer | Status | What you can trust |
| --- | --- | --- |
| Handbook people + roles | **Real** (APH OData / fixture fallback) | Parliamentarians, chamber tenure, ministries. Promoted into `roles` / `person_roles`. Not APS secretaries. |
| Estimates segments | **Real structure, derived** | Portfolio / agency headers and speaker turns from Official `TalkText`. Same Official, annotated. |
| Taken on notice | **Real phrases, incomplete QoN** | Markers in Officials become `claims.taken_on_notice`. Not the Table Office register. |
| Questions on Notice | **Best-effort real** | EQON search into foundation `qons`. Status mapped to `open` / `answered` / `overdue` / `unknown`. |
| Instruments from text | **Proposed only** | Regex candidates with `instruments.status='proposed'` and a `mentioned` chunk link. Human review required. |
| Agencies | **Stub, official names** | Seeded departments upserted into foundation `agencies` (`short_name` from the fixture `short_code`). |
