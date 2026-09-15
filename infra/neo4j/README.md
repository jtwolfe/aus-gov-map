# Neo4j graph model

Applied automatically by the `neo4j-init` Compose service, or:

```bash
python -m aus_gov_ingest graph-init
```

## Stage 1 nodes

| Label | Keys | Meaning |
| --- | --- | --- |
| `Person` | `id`, `slug`, `name` | Senator, minister, or official |
| `Hearing` | `id`, `slug`, `title`, `held_on` | Estimates or committee hearing |
| `Committee` | `id`, `slug`, `name` | Senate committee |
| `Topic` | `id`, `slug`, `name` | Coarse subject tag |
| `Document` | `id`, `title`, `doc_type` | Hansard / program / QON stub |

## Stage 1 relationships

```
(Person)-[:APPEARED_AT {role}]->(Hearing)
(Hearing)-[:HELD_BY]->(Committee)
(Person)-[:MEMBER_OF {role}]->(Committee)
(Hearing)-[:DISCUSSES]->(Topic)
(Document)-[:TRANSCRIPT_OF]->(Hearing)
```

`role` on `APPEARED_AT` is one of: `chair`, `senator`, `minister`, `official`, `witness`.

## Stage 2 nodes (Accountability Foundation)

| Label | Keys | Meaning |
| --- | --- | --- |
| `Role` | `id`, `slug`, `title`, `role_type` | Time-bounded office / seat |
| `Agency` | `id`, `slug`, `name` | Department or agency |
| `Instrument` | `id`, `slug`, `title`, `instrument_type` | Program, measure, bill, contract, grant, policy |
| `ScrutinyItem` | `id`, `slug`, `title`, `item_type` | Hearing segment, QoN, ANAO, division, inquiry |
| `Claim` | `id`, `claim_type` | Promise / assurance / taken on notice / denial |
| `Outcome` | `id`, `outcome_type`, `signal` | Sourced later signal — not a verdict |

## Stage 2 relationships

```
(Person)-[:HELD_ROLE_DURING {start_date, end_date, source}]->(Role)
(Role)-[:OF_AGENCY]->(Agency)
(Person)-[:ACCOUNTABLE_FOR {source}]->(Instrument)
(Person)-[:RESPONSIBLE_OFFICIAL {source}]->(Instrument)
(Claim)-[:PROMISED_IN]->(Instrument)
(Instrument)-[:TESTED_IN]->(ScrutinyItem)
(Person)-[:VOTED_ON {vote, source}]->(Instrument)
(Instrument)-[:FUNDED_BY]->(Instrument)
(Hearing)-[:SCRUTINISES]->(Instrument)
(Instrument)-[:OWNED_BY]->(Agency)
```

Appearance at a hearing (`APPEARED_AT`) is **not** occupancy (`HELD_ROLE_DURING`).
Do not infer `ACCOUNTABLE_FOR` from a minister sitting at Estimates.

Documented MERGE templates and metric queries: `infra/neo4j/queries/accountability/`.
Architecture: `docs/accountability-map.md`.

## Starter queries

Cypher in `infra/neo4j/queries/`:

- `people_across_estimates.cypher` — people who appear at many Estimates hearings
- `committee_activity.cypher` — committees with the most hearings
- `repeated_topics.cypher` — topics discussed across more than one hearing
- `accountability/` — role-at-date, QoN debt, chain completeness, promise→receipt, edges

The web Insights page reads the Postgres twins of the Stage 1.1 queries.
Accountability lenses read `infra/postgres/analytics/accountability_*.sql`.

## Browser

http://localhost:7474 — user `neo4j`, password `ausgovmap`.
