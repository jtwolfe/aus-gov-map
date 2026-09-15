"""ANAO (Auditor-General) ingest stub (Stage 2).

Do not invent findings. ``fetch()`` returns an empty batch.

Intended upstream:
  - Public site: https://www.anao.gov.au
  - Work / reports index: https://www.anao.gov.au/work
  - Individual reports expose HTML plus PDF; some listing pages are
    filterable by entity and year. Prefer a published feed or data.gov.au
    dump over a brittle scrape when one is available.
  - Performance audits, financial statements, and information reports
    become ``scrutiny_items`` (type anao) and optional ``outcomes``.

Target tables: ``scrutiny_items``, ``outcomes``, ``instrument_links`` (TESTED_IN).
See docs/accountability-map.md.
"""

from __future__ import annotations

from aus_gov_ingest.models import SourceBatch

ENDPOINTS = {
    "home": "https://www.anao.gov.au",
    "work": "https://www.anao.gov.au/work",
    "data_gov": "https://data.gov.au/data/organization/australian-national-audit-office",
}


class AnaoSource:
    """Empty Stage 2 adapter — no invented audit findings."""

    name = "anao"
    ENDPOINTS = ENDPOINTS

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        return SourceBatch(
            source=self.name,
            hearings=[],
            people=[],
            meta={
                "status": "not_implemented",
                "endpoints": ENDPOINTS,
                "note": (
                    "Stage 2 stub: list ANAO reports into scrutiny_items "
                    "(type anao) and optional outcomes. No invented findings."
                ),
                "schema": "infra/postgres/007_accountability.sql",
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
            },
        )
