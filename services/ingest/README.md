# aus-gov-ingest

Python ingest for **aus-gov-map**: fetch → parse → chunk → embed → upsert.

```bash
cd services/ingest
python3 -m pip install -e ".[dev]"
cp ../../.env.example ../../.env   # optional

# Offline seed (no network required)
python -m aus_gov_ingest seed
# same as:
python -m aus_gov_ingest run --source fixture

# Offline Officials (committed APH transcript JSON — no network)
python -m aus_gov_ingest run --source aph_transcript_file --dry-run
python -m aus_gov_ingest run --source aph_transcript_file \
  --path fixtures/live/transcripts --no-graph
# or from the repo root: make ingest-backfill-files

# Live Estimates Officials (APH Hansard JSON API — no ParlInfo needed)
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source estimates --limit 3 --dry-run

# Persist the same pass when Postgres is up
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source estimates --limit 3 --no-graph

# Senate committee Officials (chi=6, commsen)
INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source senate_committee --limit 2 --dry-run

# Cron-friendly incremental Estimates
python -m aus_gov_ingest cron
```

`ingest` and `aus-gov-ingest` are the same console script after install.

## Sources

| `--source` | Behaviour |
| --- | --- |
| `fixture` | Load `data/fixtures/seed.json` |
| `aph_transcript_file` | Load saved APH `/api/hansard/transcript` JSON from disk (`--path` file or directory; default `fixtures/live/transcripts`) |
| `estimates` | APH Hansard Search (`chi=5`) + `GET /api/hansard/transcript` for Official text; HTML committee pages as listing fallback |
| `estimates_schedule` | Same as `estimates`, tagged for cron / “what's new” |
| `senate_committee` | APH Hansard Search (`chi=6`, `commsen`) + transcript API; Senate index HTML as listing fallback |
| `openaustralia` | Hook only — chamber XML at data.openaustralia.org.au does not include Estimates |
| `handbook` | Parliamentary Handbook OData — empty unless `HANDBOOK_LIVE=1`; parser maps returned individuals only. Schema: `005_handbook.sql` + `007_accountability.sql` |
| `qon` | Questions on notice stub — empty `qons` / scrutiny. No invented answers |
| `anao` | Auditor-General stub — empty scrutiny / outcomes. No invented findings |
| `budget_measure` | Budget / PBS stub — empty instruments. No invented amounts |
| `austender` | AusTender CN stub — empty contracts. GrantConnect documented as sibling |

APH Azure Front Door **403s bot-like User-Agents**. The client sends a browser-like UA, `Accept` / `Accept-Language`, and keeps session cookies. `parlinfo.aph.gov.au` (XML/PDF/`toc_unixml`) still returns an Azure WAF **JS challenge** from typical datacentre IPs — ingest does **not** follow those redirects. The working structured source is `https://www.aph.gov.au/api/hansard/transcript?id=committees/estimate/{id}/0000`.

If a live fetch fails and `INGEST_FALLBACK_FIXTURE=1` (default in `.env.example`), fixture records are loaded instead. Set `INGEST_FALLBACK_FIXTURE=0` to fail empty rather than substituting invented Official.

See `fixtures/live/NOTES.md` for the fetch matrix from a cloud VM.

## Embeddings

`EMBEDDING_PROVIDER` is pluggable:

- `hash` (default) — deterministic 384-d bag-of-tokens vector. No API key. Good enough to exercise pgvector.
- `openai` — `OPENAI_API_KEY` + `text-embedding-3-small` (padded/truncated to `EMBEDDING_DIM`).
- `sentence-transformers` — optional extra; install `[sentence-transformers]`.

Upserts are idempotent on `source_key` (hearings, documents, chunks, people slugs). Live Hansard keys look like `hansard:committees/estimate/28778`.

## Cron

Suggested daily pair: **live Estimates** with `INGEST_FALLBACK_FIXTURE=0` (do not
substitute invented Official), then **file fallback** over committed
`/api/hansard/transcript` JSON (`AUS_GOV_TRANSCRIPT_PATH`):

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

`python -m aus_gov_ingest cron` is the live incremental Estimates entrypoint
(same as the first job). Export `INGEST_FALLBACK_FIXTURE=0` in that environment:

```
15 6 * * * cd /path/to/aus-gov-map/services/ingest && \
  INGEST_FALLBACK_FIXTURE=0 \
  python -m aus_gov_ingest cron >> /var/log/aus-gov-ingest.log 2>&1
```

It records a row in `ingest_runs` and only inserts hearings whose `source_key` is new.

Discover further Official IDs via Hansard Search `chi=5` (do not invent IDs):

```
python3 scripts/fetch_estimates_transcripts.py --dry-discover
```

## Person merge

Speaker lines like `Senator the Hon …`, `Ms …, Secretary`, and `CHAIR (Senator Pratt)` are normalised to a core-name slug (`james-paterson`, `jaala-hinchcliffe`). `upsert_person` merges when the last name matches and one token set is a subset of the other — it will not collapse two different Smiths. Re-run on an existing database:

```bash
python -m aus_gov_ingest merge-people
```

## Incremental schema (existing volumes)

Docker only applies `infra/postgres/*.sql` on first init. For an already-running volume:

```bash
python -m aus_gov_ingest apply-schema
python -m aus_gov_ingest seed-demo-board
```

That creates analytics views, Handbook stub tables, Stage 2 accountability tables (`007`), a unique pins index, and the FOI/procurement demo board.

## Graph

```bash
python -m aus_gov_ingest graph-init
```

See `infra/neo4j/README.md`. Neo4j is optional: ingest continues if Bolt is down.
