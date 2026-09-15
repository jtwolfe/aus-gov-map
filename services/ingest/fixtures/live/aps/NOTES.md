# APS leaders fixtures

Offline fallback for `--source aps_leaders` when `directory.gov.au` (and many
department sites) time out or 403 from a datacentre IP.

## What is real

| File | Source URL | What it grounds |
| --- | --- | --- |
| `leaders.json` | [Treasury executive](https://treasury.gov.au/the-department/about-treasury/our-executive); [Home Affairs senior staff](https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff) | Current Treasury secretary + deputies; Home Affairs secretary + a deputy. Jenny Wilkinson’s Finance secretary tenure is included only because the Treasury page states August 2022–June 2025. |
| `treasury_executive.excerpt.html` | same Treasury URL | Public sentences used by the HTML parser. Markup simplified; names and dated claims unchanged. |
| `home_affairs_senior_staff.excerpt.html` | same Home Affairs URL | Secretary / Deputy Secretary names as published 2026-09-15. Markup simplified. |

© Commonwealth of Australia. Attribute the originating agency. Research / non-commercial.

Directory URLs (for the live adapter; this IP could not fetch them):

- https://www.directory.gov.au/
- https://www.directory.gov.au/portfolios/treasury/department-treasury
- https://www.directory.gov.au/portfolios/home-affairs/department-home-affairs
- https://www.directory.gov.au/reports/australian-government-organisations-register
- Directory XML export: https://www.directory.gov.au/sites/default/files/export.xml (timed out here)
- AGOR CSV on [data.gov.au](https://data.gov.au/data/dataset/australian-government-organisations-register) lists bodies, not occupants.

## Dates

When a page says “June 2025” without a day, ingest stores `2025-06-01` and notes
that only the month is sourced. Current incumbents without a stated start stay
`start_date=null`, `end_date=null`. Do not invent historical tenures.

## Follow-up (not in this fixture)

Full secretary timelines: department annual reports, Gazette, and the Wayback
Machine copies of directory.gov.au agency pages. Appearance at Estimates is
**not** a tenure.
