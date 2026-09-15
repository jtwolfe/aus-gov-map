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

# Live Estimates schedule ("what's new")
python -m aus_gov_ingest run --source estimates --limit 10

# Senate committee adapter (best-effort APH pages)
python -m aus_gov_ingest run --source senate_committee --limit 5

# Cron-friendly incremental Estimates
python -m aus_gov_ingest cron
```

`ingest` and `aus-gov-ingest` are the same console script after install.

## Sources

| `--source` | Behaviour |
| --- | --- |
| `fixture` | Load `data/fixtures/seed.json` |
| `estimates` | APH Senate Estimates landing + committee pages; incremental vs existing `source_key`s |
| `senate_committee` | Adapter toward APH Senate committee pages |
| `openaustralia` | Hook only — XML later |

If a live fetch fails (APH commonly returns 403 to automated clients) and `INGEST_FALLBACK_FIXTURE=1` (default in `.env.example`), fixture records are loaded instead.

## Embeddings

`EMBEDDING_PROVIDER` is pluggable:

- `hash` (default) — deterministic 384-d bag-of-tokens vector. No API key. Good enough to exercise pgvector.
- `openai` — `OPENAI_API_KEY` + `text-embedding-3-small` (padded/truncated to `EMBEDDING_DIM`).
- `sentence-transformers` — optional extra; install `[sentence-transformers]`.

Upserts are idempotent on `source_key` (hearings, documents, chunks, people slugs).

## Cron

`python -m aus_gov_ingest cron` is the entrypoint stub. Wire it as:

```
15 6 * * * cd /path/to/aus-gov-map/services/ingest && python -m aus_gov_ingest cron >> /var/log/aus-gov-ingest.log 2>&1
```

It records a row in `ingest_runs` and only inserts hearings whose `source_key` is new.

## Graph

```bash
python -m aus_gov_ingest graph-init
```

See `infra/neo4j/README.md`. Neo4j is optional: ingest continues if Bolt is down.
