# APS leaders fixtures

Offline fallback for `--source aps_leaders` when `directory.gov.au` (and many
department sites) time out or 403 from a datacentre IP / Azure WAF.

## What is real

| File | Source URL | What it grounds |
| --- | --- | --- |
| `leaders.json` | [Treasury executive](https://treasury.gov.au/the-department/about-treasury/our-executive); [Home Affairs senior staff](https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff); [Wilkinson Treasury instrument](https://www.pmc.gov.au/resources/instrument-appointment-ms-jenny-wilkinson-psm-0); [Wilkinson Finance instrument](https://www.pmc.gov.au/sites/default/files/resource/download/instrument-appointment-finance-wilkinson.pdf); [Foster instrument](https://www.pmc.gov.au/resources/instrument-appointment-ms-stephanie-foster-psm) | Current Treasury secretary + deputies; Home Affairs secretary + a deputy. Dated occupancies use the instrument day when published; month-only executive-page claims stay noted. |
| `historical_tenures.json` | [PMC secretary appointments](https://www.pmc.gov.au/government/administration/secretary-appointments) plus the linked instruments / PM media | Prior PMC/Treasury secretaries (Davis, Kennedy) and current department secretaries with a stated commencement. Appointment-term expiry is **not** stored as `end_date` while they are still serving. |
| `treasury_executive.excerpt.html` | same Treasury URL | Public sentences used by the HTML parser. Markup simplified; names and dated claims unchanged. **Not** loaded when ingesting the directory (`.excerpt.html` is skipped). |
| `home_affairs_senior_staff.excerpt.html` | same Home Affairs URL | Secretary / Deputy Secretary names as published 2026-09-15. Markup simplified. Parser-test only. |

© Commonwealth of Australia. Attribute the originating agency. Research / non-commercial.

Directory URLs (for the live adapter; this IP could not fetch them — fixture fallback is expected):

- https://www.directory.gov.au/
- https://www.directory.gov.au/portfolios/treasury/department-treasury
- https://www.directory.gov.au/portfolios/home-affairs/department-home-affairs
- https://www.directory.gov.au/reports/australian-government-organisations-register
- Directory XML export: https://www.directory.gov.au/sites/default/files/export.xml (timed out here)
- AGOR CSV on [data.gov.au](https://data.gov.au/data/dataset/australian-government-organisations-register) lists bodies, not occupants.

## Dates

When a page says “June 2025” without a day, ingest stores `2025-06-01` and notes
that only the month is sourced. When a Public Service Act instrument states a
commencement day, that day is stored instead. Current incumbents without a
stated occupancy end stay `end_date=null` even if the appointment *term* has an
expiry. Do not invent historical tenures. Appearance at Estimates is **not** a
tenure.

## Follow-up (not in this fixture)

Earlier secretary timelines: department annual reports, Gazette, and Wayback
Machine copies of directory.gov.au agency pages. Acting secretaries without a
stated start are omitted.
