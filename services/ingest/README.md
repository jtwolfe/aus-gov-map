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
| `estimates` | APH Hansard Search (`chi=5`) + `GET /api/hansard/transcript` for Official text; HTML committee pages as listing fallback |
| `estimates_schedule` | Same as `estimates`, tagged for cron / “what's new” |
| `senate_committee` | APH Hansard Search (`chi=6`, `commsen`) + transcript API; Senate index HTML as listing fallback |
| `openaustralia` | Hook only — chamber XML at data.openaustralia.org.au does not include Estimates |

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
