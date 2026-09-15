# Live APH fetch notes (2026-09-15)

## Offline Official transcripts

Full `/api/hansard/transcript` JSON for **21** Senate Estimates Officials is
committed under `fixtures/live/transcripts/` so ingest can run **without**
hitting APH (needed when another machine's IP gets the Azure WAF JS challenge).

IDs were discovered via Hansard Search `chi=5` (Estimates) using `AphClient`
(browser-like UA on `www.aph.gov.au`). Do not invent IDs. Re-fetch with:

```bash
cd services/ingest
python3 scripts/fetch_estimates_transcripts.py --per-round 5
```

These are the **real API JSON objects** (`TalkText` present, not HTML / WAF
challenge pages). They are © Commonwealth of Australia (typically CC BY-NC-ND);
attribute the Parliament of Australia. No secrets. ~20 MB total; each file is
well under GitHub's blob limit.

| File | SystemId | Round (approx.) | Official |
| --- | --- | --- | --- |
| `transcripts/29629.json` | `committees/estimate/29629/0000` | Budget 2026–27 | Community Affairs Legislation Committee — 5 June 2026 |
| `transcripts/29628.json` | `committees/estimate/29628/0000` | Budget 2026–27 | Community Affairs Legislation Committee — 4 June 2026 |
| `transcripts/29625.json` | `committees/estimate/29625/0000` | Budget 2026–27 | Economics Legislation Committee — 5 June 2026 |
| `transcripts/29624.json` | `committees/estimate/29624/0000` | Budget 2026–27 | Economics Legislation Committee — 4 June 2026 |
| `transcripts/29617.json` | `committees/estimate/29617/0000` | Budget 2026–27 | Education and Employment Legislation Committee — 5 June 2026 |
| `transcripts/29616.json` | `committees/estimate/29616/0000` | Budget 2026–27 | Education and Employment Legislation Committee — 4 June 2026 |
| `transcripts/29420.json` | `committees/estimate/29420/0000` | Additional 2025–26 | Foreign Affairs, Defence and Trade Legislation Committee — 10 March 2026 |
| `transcripts/29374.json` | `committees/estimate/29374/0000` | Additional 2025–26 | Community Affairs Legislation Committee — 12 February 2026 |
| `transcripts/29373.json` | `committees/estimate/29373/0000` | Additional 2025–26 | Economics Legislation Committee — 12 February 2026 |
| `transcripts/29371.json` | `committees/estimate/29371/0000` | Additional 2025–26 | Education and Employment Legislation Committee — 12 February 2026 |
| `transcripts/29370.json` | `committees/estimate/29370/0000` | Additional 2025–26 | Community Affairs Legislation Committee — 11 February 2026 |
| `transcripts/29091.json` | `committees/estimate/29091/0000` | Supplementary 2025–26 | Finance and Public Administration Legislation Committee — 4 November 2025 |
| `transcripts/29004.json` | `committees/estimate/29004/0000` | Supplementary 2025–26 | Community Affairs Legislation Committee — 10 October 2025 |
| `transcripts/29003.json` | `committees/estimate/29003/0000` | Supplementary 2025–26 | Economics Legislation Committee — 10 October 2025 |
| `transcripts/29001.json` | `committees/estimate/29001/0000` | Supplementary 2025–26 | Education and Employment Legislation Committee — 10 October 2025 |
| `transcripts/29000.json` | `committees/estimate/29000/0000` | Supplementary 2025–26 | Community Affairs Legislation Committee — 9 October 2025 |
| `transcripts/28780.json` | `committees/estimate/28780/0000` | Additional 2024–25 | Environment and Communications Legislation Committee — 27 March 2025 |
| `transcripts/28779.json` | `committees/estimate/28779/0000` | Additional 2024–25 | Legal and Constitutional Affairs Legislation Committee — 27 March 2025 |
| `transcripts/28778.json` | `committees/estimate/28778/0000` | Additional 2024–25 | Finance and Public Administration Legislation Committee — 27 March 2025 |
| `transcripts/28751.json` | `committees/estimate/28751/0000` | Additional 2024–25 | Environment and Communications Legislation Committee — 28 February 2025 |
| `transcripts/28750.json` | `committees/estimate/28750/0000` | Additional 2024–25 | Finance and Public Administration Legislation Committee — 28 February 2025 |

Hansard Search `chi=5` with date windows for May–June 2025 did not list Budget
Estimates 2025–26 Officials (federal election caretaker). Additional /
Supplementary 2025–26 and nearby Additional 2024–25 are present.

Load them into the pipeline (same `hearing_from_transcript` / `source_key`
shape as live Estimates):

```bash
cd services/ingest
# parse only (also: make ingest-backfill-files from the repo root)
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

Offline dry-run from these files is recorded in `dry_run_aph_transcript_file.json`
(`fetched` must be **> 3**).

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

## Suggested cron

Daily **live** Estimates (Hansard JSON API). Do **not** substitute invented
fixtures. Keep the committed Official directory as a file fallback when APH
is unreachable from this IP:

```
# Live incremental Estimates (browser-like UA; no invented Official)
15 6 * * * cd /path/to/aus-gov-map/services/ingest && \
  INGEST_FALLBACK_FIXTURE=0 \
  python -m aus_gov_ingest run --source estimates --incremental \
  >> /var/log/aus-gov-ingest.log 2>&1

# File fallback — same source_key shape (hansard:committees/estimate/{id})
30 6 * * * cd /path/to/aus-gov-map/services/ingest && \
  AUS_GOV_TRANSCRIPT_PATH=/path/to/aus-gov-map/services/ingest/fixtures/live/transcripts \
  python -m aus_gov_ingest run --source aph_transcript_file --incremental \
  >> /var/log/aus-gov-ingest.log 2>&1
```

`python -m aus_gov_ingest cron` is the same live Estimates incremental pass;
export `INGEST_FALLBACK_FIXTURE=0` in that environment too.

Equivalent one-shot from the repo root: `make ingest-backfill-files`.

## Accountability pipeline dry-runs (2026-09-15)

Recorded from this environment. Persist with `DATABASE_URL` set and **omit** `--dry-run`.
See `docs/accountability-map.md` for real vs proposed.

```bash
# Handbook — live OData (also: --path fixtures/live/handbook)
python -m aus_gov_ingest run --source handbook --limit 5 --dry-run
# recorded: dry_run_handbook_live.json — fetched 5, roles 29, tenure 18, transport=handbookapi

# QoN — live EQON search (also: --path fixtures/live/qon)
python -m aus_gov_ingest run --source qon --limit 5 --dry-run
# recorded: dry_run_qon_live.json — fetched 5, transport=eqon_api

# Agency stubs
python -m aus_gov_ingest run --source agencies --dry-run
# recorded: dry_run_agencies.json — fetched 25 official-name rows

# Structured Estimates segments (same Official, annotated)
python -m aus_gov_ingest run --source aph_transcript_file \
  --path fixtures/transcript_fpa_28778_excerpt.json --dry-run
# recorded: dry_run_segments.json — 7 segments (portfolio/agency/speaker/QoN markers)

# Proposed instruments (not asserted facts)
python -m aus_gov_ingest run --source instrument_propose \
  --path fixtures/live/transcripts/28778.json --dry-run
# recorded: dry_run_instrument_propose.json — 8 proposed (6 program, 2 contract)
```

Handbook does **not** include APS secretaries. OpenAustralia has **no** Estimates QoN feed.
EQON bulk ZIP downloads require My Parliament sign-in; ingest uses the public search API.
