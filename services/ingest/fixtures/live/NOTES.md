# Live APH fetch notes (2026-09-15)

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
