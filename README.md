# aus-gov-map

A continuously updated map of **Australian Commonwealth public data**.

Stage 1 covers **Senate committees and Estimates hearings**: search the record, open a hearing or a person, and follow who sat with whom. Stage 1.1 prefers live Postgres, persists pinboards, and adds starter Insights queries.

This repository is a working scaffold — not a production service and not a historical backfill.

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
| `infra/postgres` | Extensions, schema, seed SQL |
| `infra/neo4j` | Constraints / indexes + graph model |
| `data/fixtures` | Offline seed (hearings, people, sample Official) |

## How to run

### 1. Databases

```bash
cp .env.example .env
make db-up          # Postgres only — prints DATABASE_URL
# or:
make up             # Postgres + Neo4j
```

That starts **Postgres 16 + pgvector** (`localhost:5432`) and optionally **Neo4j 5** (`7474` / `7687`). Schema and the fixture seed load on first Postgres init. Incremental Stage 1.1 files (`004`–`006`) also run on a fresh volume. Neo4j constraints are applied by `neo4j-init`.

```
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov
neo4j / ausgovmap
```

Existing volumes do **not** re-run `infra/postgres/*.sql`. Apply analytics views, Handbook stubs, and the demo board with:

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

## Stage 2 stub — Parliamentary Handbook

Empty ingest source `handbook` (no fake officials) plus tables in `infra/postgres/005_handbook.sql` for tenure, electorate, and roles linked to `people`. See comments in `services/ingest/src/aus_gov_ingest/sources/handbook.py` pointing at handbook.aph.gov.au.

## Graph model

See `infra/neo4j/README.md`. Stage 1 nodes: `Person`, `Hearing`, `Committee`, `Topic`, `Document`.

## Licensing and attribution

- **Code** is MIT (`LICENSE`).
- **Official Hansard / committee / Estimates records** are typically © Commonwealth of Australia and often [CC BY-NC-ND](https://creativecommons.org/licenses/by-nc-nd/4.0/). Attribute the Parliament of Australia. This project is framed as **research / non-commercial**.
- Fixture prose in `data/fixtures` is **invented sample Official**, not a parliamentary transcript.

## Stage 2 / 3 (not in this scaffold)

- Full historical backfill of Hansard
- Questions on notice answers at scale
- OpenAustralia / TheyWorkForYou-AU XML
- Bills, divisions, agency graphs
- Auth-backed shared boards
- Production deploy
- Wiring the Handbook adapter to a real extract

## Tests

```bash
cd services/ingest && python3 -m pytest
cd apps/web && npm run lint && npm run build
# Search + pins (offline always; Postgres/API when env is set)
python3 scripts/verify_search_pins.py
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov python3 scripts/verify_search_pins.py
WEB_URL=http://localhost:3000 python3 scripts/verify_search_pins.py
```
