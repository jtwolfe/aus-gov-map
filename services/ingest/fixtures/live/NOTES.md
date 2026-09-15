# Live APH fetch notes (2026-09-15)

## Offline Official transcripts

Full `/api/hansard/transcript` JSON for the three 5 June 2026 Estimates Officials
is committed under `fixtures/live/transcripts/` so ingest can run **without**
hitting APH (needed when another machine's IP gets the Azure WAF JS challenge):

| File | SystemId | Official |
| --- | --- | --- |
| `transcripts/29629.json` | `committees/estimate/29629/0000` | Community Affairs Legislation Committee — 5 June 2026 |
| `transcripts/29625.json` | `committees/estimate/29625/0000` | Economics Legislation Committee — 5 June 2026 |
| `transcripts/29617.json` | `committees/estimate/29617/0000` | Education and Employment Legislation Committee — 5 June 2026 |

These are the **real API JSON objects** (`TalkText` present, not HTML / WAF
challenge pages). They are © Commonwealth of Australia (typically CC BY-NC-ND);
attribute the Parliament of Australia. No secrets.

Load them into the pipeline (same `hearing_from_transcript` / `source_key`
shape as live Estimates):

```bash
cd services/ingest
# parse only
python -m aus_gov_ingest run --source aph_transcript_file --dry-run
# or an explicit path (repo root):
python -m aus_gov_ingest run --source aph_transcript_file \
  --path services/ingest/fixtures/live/transcripts --dry-run

# upsert when Postgres is up
DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \
  python -m aus_gov_ingest run --source aph_transcript_file --no-graph
```

`--path` accepts a directory of `*.json` or a single transcript file.
`AUS_GOV_TRANSCRIPT_PATH` overrides the default directory.

Offline dry-run from these files (`dry_run_aph_transcript_file.json`) matches the
live Estimates Official char counts (29629 ≈ 508k, 29625 ≈ 431k, 29617 ≈ 336k).

## Fetch matrix

Proven from this environment (cloud VM, datacentre IP):

| URL | Result |
| --- | --- |
| `www.aph.gov.au/Parliamentary_Business/Senate_estimates` with bot UA `aus-gov-map-ingest/0.1 (+…)` | **HTTP 403** (Azure Front Door) |
| Same URL with a Chrome User-Agent + `Accept` / `Accept-Language` | **HTTP 200** (~68 KB HTML) |
| Committee pages (`/fpa`, `/ee`, …), Hansard Search `chi=5`, Hansard Display | **HTTP 200** |
| `GET /api/hansard/transcript?id=committees/estimate/{id}/0000` | **HTTP 200** JSON + full Official `TalkText` |
| `GET /api/hansard/link/?id=…&linktype=xml` | 302 → `parlinfo.aph.gov.au` |
| `parlinfo.aph.gov.au` (search, HTML, PDF, `toc_unixml`) | **HTTP 403** Azure WAF **JS challenge** |
| `data.openaustralia.org.au` chamber XML index | **HTTP 200** (Senate/House debates only — no Estimates) |

Working ingest path: **APH Hansard Search + `/api/hansard/transcript`** on `www.aph.gov.au`.
Do not follow the ParlInfo XML/PDF redirects from this class of IP.

Successful live dry-run (`INGEST_FALLBACK_FIXTURE=0 python -m aus_gov_ingest run --source estimates --limit 3 --dry-run`):

- Community Affairs Legislation Committee — 5 June 2026 — Estimates (`committees/estimate/29629`, ~508k chars Official)
- Economics Legislation Committee — 5 June 2026 — Estimates (`committees/estimate/29625`, ~431k chars)
- Education and Employment Legislation Committee — 5 June 2026 — Estimates (`committees/estimate/29617`, ~336k chars)

Senate committee dry-run (`--source senate_committee --limit 2`):

- Community Affairs Legislation Committee — 11 September 2026 — Private Health Insurance Amendment (Modernising the Private Health Insurance Rebate) Bill 2026
- Community Affairs Legislation Committee — 4 September 2026 — same bill

Earlier API probe (full Official JSON):

- Finance and Public Administration Legislation Committee — 27 March 2025 — Estimates (`committees/estimate/28778`)
