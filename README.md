# aus-gov-map

A continuously updated map of **Australian Commonwealth public data**.

Stage 1 covers **Senate committees and Estimates hearings**: search the record, open a hearing or a person, and follow who sat with whom.

This repository is a working scaffold — not a production service and not a historical backfill.

## Architecture

```
                    ┌─────────────────┐
   APH / ParlInfo ─►│  Python ingest  │──upsert──► Postgres + pgvector
   Estimates sched. │  fetch → parse  │            hearings, documents,
   (OpenAustralia)  │  chunk → embed  │            chunks + vector,
                    └────────┬────────┘            people, ingest_runs,
                             │                     boards / pins (stubs)
                             └──upsert──► Neo4j
                                          Person ─APPEARED_AT→ Hearing
                                          Hearing ─HELD_BY→ Committee
                                          Hearing ─DISCUSSES→ Topic
                                          Document ─TRANSCRIPT_OF→ Hearing

   Next.js (App Router) ──read──► Postgres if DATABASE_URL is up
                         ──else─► data/fixtures/seed.json
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
docker compose up -d
```

That starts **Postgres 16 + pgvector** (`localhost:5432`) and **Neo4j 5** (`7474` / `7687`). Schema and the fixture seed load on first Postgres init. Neo4j constraints are applied by `neo4j-init`.

```
postgres://ausgov:ausgov@localhost:5432/ausgov
neo4j / ausgovmap
```

### 2. Web app (works offline)

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

If `DATABASE_URL` is unset or Postgres is down, the UI serves `data/fixtures/seed.json`. Search, hearing pages, person pages, and board stubs all work against that seed.

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

# Live Estimates (“what's new” when used incrementally / via cron)
python -m aus_gov_ingest run --source estimates --limit 10
python -m aus_gov_ingest run --source estimates --incremental --limit 10

# Senate committee adapter
python -m aus_gov_ingest run --source senate_committee --limit 5

# Cron-friendly entrypoint (incremental Estimates)
python -m aus_gov_ingest cron
```

After `pip install -e .`, `ingest` and `aus-gov-ingest` are the same console script:

```bash
ingest run --source estimates --limit 5
```

Live APH fetches are best-effort. If they fail and `INGEST_FALLBACK_FIXTURE=1`, the fixture is loaded instead.

Optional app containers:

```bash
docker compose --profile app up --build
```

## Search

- **Keyword** — titles, summaries, people, transcript excerpts (`tsvector` / `pg_trgm` when Postgres is up; lexical fallback on the fixture).
- **Semantic** — pgvector cosine path once ingest has written embeddings. Default embedder is a deterministic hashed bag-of-tokens (no API key). Swap with `EMBEDDING_PROVIDER=openai` or `sentence-transformers`.
- Combined is the default in the UI.

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

## Tests

```bash
cd services/ingest && python3 -m pytest
cd apps/web && npm run lint && npm run build
```
