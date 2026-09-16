# aus-gov-map

A continuously updated map of **Australian Commonwealth public data**.

Stage 1 covers **Senate committees and Estimates hearings**: search the record, open a hearing or a person, and follow who sat with whom. Stage 1.1 prefers live Postgres, persists pinboards, and adds starter Insights queries. Stage 2 adds the **Accountability Foundation** — a sourced decision / duty map (roles, instruments, scrutiny, outcomes) with empty-safe lenses. It does not assign guilt.

This repository is a working scaffold — not a production service and not a historical backfill.

## How the map fits together

Search a hearing or person, open the dossier, then step sideways into the duty
map. **Hearings** and **People** are the Stage 1 record. **Agencies**,
**Accountability** lenses, and the **Atlas** read the same Postgres tables:
occupancy (`person_roles`), instruments, QoNs, ANAO items, and sparse claim
arcs. Boards pin anything you want to keep. Empty states name the ingest that
fills the missing layer — silence is not a finding, and sitting in Estimates
is not a tenure. A later **Laws** reading room can hang off the same chrome.

## Architecture

```
                    ┌─────────────────┐
   APH / ParlInfo ─►│  Python ingest  │──upsert──► Postgres + pgvector
   Estimates sched. │  fetch → parse  │            hearings, documents,
   (OpenAustralia)  │  chunk → embed  │            chunks + vector,
                    └────────┬────────┘            people, ingest_runs,
                             │                     boards / pins
                             └──upsert──► Neo4j
                                          Person ─APPEARED_AT→ Hearing
                                          Hearing ─HELD_BY→ Committee
                                          Hearing ─DISCUSSES→ Topic
                                          Document ─TRANSCRIPT_OF→ Hearing

   Next.js (App Router) ──read──► Postgres whenever DATABASE_URL reaches a live server
                         ──else─► data/fixtures/seed.json
                         ──write─► boards / pins (API; not localStorage on the happy path)
```

| Path | Role |
| --- | --- |
| `apps/web` | Next.js + TypeScript reading room |
| `services/ingest` | Modular Python ingest + CLI |
| `infra/postgres` | Extensions, schema, seed SQL, Stage 2 accountability tables |
| `infra/neo4j` | Constraints / indexes + Stage 1 + duty-map graph |
| `docs/accountability-map.md` | Stage 2 architecture (layers, edges, non-goals, sources, metrics) |
| `docs/responsibility-atlas.md` | Responsibility Atlas (temporal duty view, `/atlas`, query contract) |
| `docs/laws-and-precedent.md` | Stage 3a: Bills/Acts, divisions, precedent on the same spine |
| `data/fixtures` | Offline seed (hearings, people, sample Official) |

## How to run

### 1. Databases

```bash
cp .env.example .env
make db-up          # Postgres only — prints DATABASE_URL
# or:
make up             # Postgres + Neo4j
```

That starts **Postgres 16 + pgvector** (`localhost:5432`) and optionally **Neo4j 5** (`7474` / `7687`). Schema and the fixture seed load on first Postgres init. Incremental files (`004`–`013`) also run on a fresh volume. Neo4j constraints are applied by `neo4j-init`.

```
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov
neo4j / ausgovmap
```

Existing volumes do **not** re-run `infra/postgres/*.sql`. Apply analytics views, Handbook stubs, accountability tables, Atlas helpers, laws/precedent, and the demo board with:

```bash
make db-apply
```

### 2. Web app (prefers Postgres)

```bash
make web-dev
# equivalent:
# cd apps/web && DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov npm run dev
```

Open http://localhost:3000

The App Router **prefers `DATABASE_URL`** whenever Postgres answers. Search, hearing pages, person pages, Insights, and boards then read live rows (including `hansard:` Officials). If the URL is unset or the server is down, the UI serves `data/fixtures/seed.json`.

### Current coverage

The home page strip counts **hearings / people / chunks** from the active store, and splits **live Hansard** (`source_key` starting `hansard:`) vs **sample fixture**. After a typical local ingest you should see the three invented fixture hearings plus the committed Estimates Officials under `services/ingest/fixtures/live/transcripts` (21 Hansard JSON files, including `29617` / `29625` / `29629`).

```bash
# How to refresh that picture
make db-up
make seed                 # optional invented Officials
make ingest-live-files    # committed APH JSON → Postgres
make web-dev              # coverage strip reads DATABASE_URL
```

`GET /api/health` also returns those counts.

### 3. Ingest CLI

```bash
cd services/ingest
python3 -m pip install -e ".[dev]"

# Fetch/parse only (no Postgres required)
python -m aus_gov_ingest run --source fixture --dry-run

# Offline seed into Postgres (+ Neo4j if Bolt is up)
python -m aus_gov_ingest seed
# equivalent:
python -m aus_gov_ingest run --source fixture

# Officials from committed APH transcript JSON (offline; no APH fetch)
python -m aus_gov_ingest run --source aph_transcript_file --dry-run
# same dry-run from the repo root (21 Official JSON files):
make ingest-backfill-files
# persist into Postgres + seed the FOI/procurement demo board:
make ingest-live-files
# equivalent:
# DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
#   python -m aus_gov_ingest run --source aph_transcript_file --no-graph

# Live Estimates Officials (APH Hansard JSON API)
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source estimates --limit 3 --dry-run
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source estimates --limit 3 --no-graph
python -m aus_gov_ingest run --source estimates --incremental --limit 10

# Senate committee Officials
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source senate_committee --limit 2 --dry-run

# Cron-friendly entrypoint (incremental Estimates)
python -m aus_gov_ingest cron
```

Suggested daily cron — live Estimates with **no invented fixture fallback**, plus
committed Official JSON if APH is unreachable:

```
15 6 * * * cd /path/to/aus-gov-map/services/ingest && \
  INGEST_FALLBACK_FIXTURE=0 \
  python -m aus_gov_ingest run --source estimates --incremental \
  >> /var/log/aus-gov-ingest.log 2>&1
30 6 * * * cd /path/to/aus-gov-map/services/ingest && \
  AUS_GOV_TRANSCRIPT_PATH=/path/to/aus-gov-map/services/ingest/fixtures/live/transcripts \
  python -m aus_gov_ingest run --source aph_transcript_file --incremental \
  >> /var/log/aus-gov-ingest.log 2>&1
```

See `services/ingest/README.md` and `services/ingest/fixtures/live/NOTES.md`.

After `pip install -e .`, `ingest` and `aus-gov-ingest` are the same console script:

```bash
ingest run --source estimates --limit 5
```

Live APH fetches use a **browser-like User-Agent**. Bot-like UAs get **403** from Azure Front Door on `www.aph.gov.au`. Direct ParlInfo XML/PDF still JS-challenges many datacentre IPs; ingest reads Official text from `GET /api/hansard/transcript` instead. If a live fetch fails and `INGEST_FALLBACK_FIXTURE=1`, the invented fixture is loaded.

Optional app containers:

```bash
docker compose --profile app up --build
```

## Search

- **Keyword** — Postgres full-text over hearings, documents, chunks, and people (`websearch_to_tsquery` + `ILIKE`). Fixture mode uses the same lexical fallback.
- **Filters** — committee, date range, person name, Estimates vs other. They apply to the hearing a hit belongs to.
- **Semantic** — pgvector cosine against chunk embeddings when they exist. The web app hashes the query with the same bag-of-tokens embedder as ingest (`EMBEDDING_PROVIDER=hash`). Swap ingest to `openai` or `sentence-transformers` if you re-embed.
- Combined is the default in the UI.
- Hearing and person pages show a **Live Hansard** vs **Sample fixture** badge, Commonwealth / CC BY-NC-ND attribution, and `source_url`.

## Boards and pins

When Postgres is up, **create a board**, **pin** a hearing / person / chunk, **list** boards, and **open** a board — all via `/api/boards` and `/api/pins`. localStorage is only a fallback if the database is down.

Seed a demo board from FOI / procurement-ish chunk hits (prefers live `hansard:` rows):

```bash
make db-apply
# or: python -m aus_gov_ingest seed-demo-board
```

If no matching chunks exist yet, ingest Officials (or the fixture) first, then re-run `seed-demo-board`.

## Insights

`/insights` runs the starter inefficiency queries (people across many Estimates hearings, densest recent committees, repeated topic / FOI-procurement mentions). SQL views: `infra/postgres/analytics/`. Cypher twins: `infra/neo4j/queries/`.

## Responsibility Atlas

`/atlas` is a **temporal duty view** (past left → present right), not a
force-directed graph. Swimlanes are portfolios or people; bars are sourced
`person_roles`; points are hearings / QoNs / ANAO; threads are instruments.
Architecture, API contract, and acceptance criteria:
[`docs/responsibility-atlas.md`](docs/responsibility-atlas.md).

## Laws and precedent (Stage 3a)

`/laws` is the Bill / Act reading room on the same duty map. Dossiers show
register status, sourced divisions (They Vote For You), and court holdings
that cite the Act. Votes stay on dossiers — not as Atlas moments. Spec:
[`docs/laws-and-precedent.md`](docs/laws-and-precedent.md).

```bash
make db-apply
make ingest-laws                 # dry-run FRL / TVFY / judgments fixtures
# make ingest-laws DRY_RUN=      # persist
```

## Accountability map (Stage 2)

The product is becoming a **decision / duty map**: who held which office when (elected **and** public service), which instrument they were accountable or responsible for, and where that chain was later tested. Architecture: [`docs/accountability-map.md`](docs/accountability-map.md).

**Non-goals:** no automated “guilt” labels; sourced chains only; Hansard is a citation, not ground truth; no invented officials.

| Layer | Postgres | Ingest `--source` |
| --- | --- | --- |
| Occupancy | `roles`, `person_roles` (FK to existing `people`; Handbook tables stay provenance) | `handbook` (live OData + fixture fallback); `aps_leaders` (secretaries / agency heads) |
| Agencies | `agencies` | `agencies` (official-name stubs); `aps_leaders` (links incumbents) |
| Instruments | `instruments`, `instrument_links` | `instrument_propose` (proposed only); `budget_measure` (BP2 / PBS); `austender` (OCDS); `legislation` (FRL bill/act). `FUNDED_BY` only when title+agency+period or a fixture key uniquely match (`make ingest-links`) |
| Scrutiny | `scrutiny_items`, `qons`, `claims`, `hearing_segments`, `divisions` | `qon` (EQON), `anao` (work index), `theyvoteforyou`, `judgments`, Stage 1 hearings |
| Outcomes | `outcomes` (sourced signals only) | `anao` (parseable finding language only) |

Web: **Accountability**, **Laws**, and **Atlas** in the nav. Lenses (safe with zero rows):

0. Responsibility Atlas — `/atlas` (temporal duty view; spec: [`docs/responsibility-atlas.md`](docs/responsibility-atlas.md))
1. Role at date — `/accountability/role-at-date`
2. Promise → receipt — `/accountability/promise-receipt`
3. QoN debt — `/accountability/qon-debt`
4. Chain completeness — `/accountability/chain-completeness`
5. Instruments explorer — `/accountability/instruments`
6. Laws — `/laws` (Bills/Acts, votes, judgments; spec: [`docs/laws-and-precedent.md`](docs/laws-and-precedent.md))

The Atlas is the left→right past–present reading room for the same tables: tenure bars from `person_roles`, hearing-level moments (segments rolled up), QoN/ANAO points, instrument threads, and sparse claim arcs. Fixture mode degrades to an empty state plus a link to Accountability — it does not invent officials.

APIs under `/api/accountability/*` read the views in `infra/postgres/analytics/accountability_*.sql` when present. `GET /api/qon` lists foundation `qons`.

```bash
make db-apply   # 007–013 + views
cd services/ingest
python -m aus_gov_ingest run --source handbook --limit 20 --dry-run
python -m aus_gov_ingest run --source aps_leaders --limit 10 --dry-run
python -m aus_gov_ingest run --source qon --limit 20 --dry-run
python -m aus_gov_ingest run --source agencies --dry-run
python -m aus_gov_ingest run --source instrument_propose --limit 1 --dry-run
python -m aus_gov_ingest run --source anao --limit 5 --dry-run
python -m aus_gov_ingest run --source budget_measure --limit 10 --dry-run
python -m aus_gov_ingest run --source austender --limit 10 --dry-run
python -m aus_gov_ingest run --source legislation --limit 10 --dry-run
python -m aus_gov_ingest run --source theyvoteforyou --limit 5 --dry-run
python -m aus_gov_ingest run --source judgments --dry-run
# After hearings exist, attach QoN hearing_id (fixture key or unique match):
# make ingest-qon-hearings DRY_RUN=
# Budget + AusTender FUNDED_BY when evidenced:
# make ingest-links DRY_RUN=
# persist (omit --dry-run) when DATABASE_URL reaches Postgres:
# DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
#   python -m aus_gov_ingest run --source anao --limit 10 --no-graph
```

Estimates Official ingest also writes `hearing_segments` (portfolio / agency headers, speaker turns, taken-on-notice markers). Instrument candidates from text are **proposed only**. APS secretaries are ingested via `aps_leaders` (directory.gov.au / official executive pages / cited fixtures). Appearance at Estimates is **not** a tenure. Historical secretary timelines may need annual reports or the Wayback Machine.

## Graph model

See `infra/neo4j/README.md`. Stage 1 nodes: `Person`, `Hearing`, `Committee`, `Topic`, `Document`. Stage 2 adds `Role`, `Agency`, `Instrument`, `ScrutinyItem` and edges `HELD_ROLE_DURING`, `ACCOUNTABLE_FOR`, `RESPONSIBLE_OFFICIAL`, `PROMISED_IN`, `TESTED_IN`, `VOTED_ON`, `FUNDED_BY`.

## Licensing and attribution

- **Code** is MIT (`LICENSE`).
- **Official Hansard / committee / Estimates records** are typically © Commonwealth of Australia and often [CC BY-NC-ND](https://creativecommons.org/licenses/by-nc-nd/4.0/). Attribute the Parliament of Australia. This project is framed as **research / non-commercial**.
- Fixture prose in `data/fixtures` is **invented sample Official**, not a parliamentary transcript.

## Later (not in this foundation)

- Full historical backfill of Hansard
- Full Budget Paper PDF table extraction (this pass uses BP2 DOCX + PBS CSV)
- Questions on notice answers at scale (EQON has 176k+ rows; ingest is capped)
- OpenAustralia / TheyWorkForYou-AU XML
- GrantConnect + full FRL backfill + full TheyVoteForYou division lists
- Broader `FUNDED_BY` (this pass writes sourced contract↔program links only; Act↔appropriation remains later)
- Live Jade / AustLII judgment scrape (fixture MVP only)
- Asserted bills / instruments from Estimates text (this repo still proposes those candidates)
- Full historical APS secretary timelines (annual reports / Wayback)
- Auth-backed shared boards
- Production deploy

## Tests

```bash
cd services/ingest && python3 -m pytest
cd apps/web && npm run lint && npm run build
# Search + pins (offline always; Postgres/API when env is set)
python3 scripts/verify_search_pins.py
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov python3 scripts/verify_search_pins.py
WEB_URL=http://localhost:3000 python3 scripts/verify_search_pins.py
python3 scripts/verify_atlas.py
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov python3 scripts/verify_atlas.py
WEB_URL=http://localhost:3000 python3 scripts/verify_atlas.py
python3 scripts/verify_laws.py
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov python3 scripts/verify_laws.py
WEB_URL=http://localhost:3000 python3 scripts/verify_laws.py
cd apps/web && npm test
```
