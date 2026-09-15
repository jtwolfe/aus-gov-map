# Accountability map — schema contract and coverage

This document is the **name contract** for the first real data pipelines.
A parallel “foundation schema” PR should reuse these table names rather than
inventing a second set. The additive migration is
`infra/postgres/007_accountability_pipelines.sql` (`CREATE TABLE IF NOT EXISTS`).

## What’s real vs proposed

| Layer | Status | What you can trust |
| --- | --- | --- |
| **Handbook people + roles** | **Real** (public APH OData / fixture fallback) | Parliamentarians, chamber tenure, party, ministries when the Handbook publishes them. Attribution: Parliamentary Handbook / Parliament of Australia. |
| **Estimates segments** | **Real structure, derived** | Portfolio / agency headers and speaker turns parsed from Official `TalkText`. Not a second Hansard — same Official, annotated. |
| **Taken on notice markers** | **Real phrases, incomplete QoN** | “take/taken on notice” in Officials. These are **not** the Table Office QoN register. |
| **Questions on Notice** | **Best-effort real** | Senate Estimates EQON search (`/api/qon/getestimatesdata`) when reachable; otherwise committed JSON under `services/ingest/fixtures/live/qon/`. Status is APH’s field mapped to `open` / `answered` / `overdue` / `unknown`. |
| **Instruments** | **Proposed only** | Regex candidates (bills, programs, contract/grant mentions) with low confidence, linked to a source chunk. **Not asserted facts.** Human review required. |
| **Agencies / departments** | **Stub, official names** | Seeded major Commonwealth departments and parliamentary departments. Secretaries / SES are **not** in the Handbook — needs a separate APS / directory.gov.au source. |
| **Fixture seed Officials** | **Invented** | `data/fixtures/seed.json` is sample dialogue, not Hansard. |

## Tables

| Table | Purpose |
| --- | --- |
| `people` | Existing. Handbook upserts here (slug merge unchanged). |
| `handbook_entries` | Existing (`005_handbook.sql`). Keyed by Handbook `PHID`. |
| `handbook_roles` | Time-bounded ministry / party / parliamentary roles. |
| `handbook_tenure` | Chamber + electorate/state service windows. |
| `agencies` | Department / agency stub (`slug`, `short_code`, `portfolio`). |
| `hearing_segments` | Structured Official blocks (header / speaker / taken-on-notice). |
| `questions_on_notice` | EQON rows + optional transcript-derived markers. |
| `instruments` | Proposed decision objects (`status='proposed'`). |
| `chunks.metadata` | `portfolio`, `agency`, `taken_on_notice` for filters. |

## Views / metrics

- `v_qon_by_portfolio` — counts by portfolio and status.

## CLI

```bash
ingest run --source handbook --limit 20 --dry-run
ingest run --source qon --limit 20 --dry-run
ingest run --source agencies --dry-run
ingest run --source instrument_propose --limit 2 --dry-run
ingest run --source aph_transcript_file --limit 1 --dry-run   # segments + chunk annotation
# persist when DATABASE_URL is set (omit --dry-run)
```

`--path` may point at a fixture directory for `handbook`, `qon`, `agencies`,
`instrument_propose`, and `aph_transcript_file`. Live APH fetches use a
browser-like User-Agent; empty/WAF responses fall back to committed fixtures.

## Gaps (not in this pipeline)

- APS secretaries and deputy secretaries as first-class people (Handbook is parliamentarians only).
- Full historical EQON backfill (176k+ rows exist; ingest is capped with `--limit`).
- Asserted instruments / bills register (this PR only proposes from text).
- OpenAustralia Estimates coverage (still none — chamber XML only).
