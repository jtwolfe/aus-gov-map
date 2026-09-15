"""AusTender contract notice ingest stub (Stage 2).

Do not invent CNs or suppliers. ``fetch()`` returns an empty batch.

Intended upstream:
  - Public site: https://www.tenders.gov.au
  - Reported contract notices (CN) search / export (CSV) from AusTender
    Reports. Bulk historical extracts also appear on data.gov.au.
  - Related: GrantConnect reported grants — https://www.grants.gov.au
    (separate adapter later; documented here so the instrument types
    contract vs grant stay distinct).

Each CN becomes ``instruments`` (type contract) with identifiers.CN,
nullable amount_aud, agency_id, and FUNDED_BY links when a PBS measure
is cited.

Target tables: ``instruments``, ``agencies``, ``instrument_links``.
See docs/accountability-map.md.
"""

from __future__ import annotations

from aus_gov_ingest.models import SourceBatch

ENDPOINTS = {
    "home": "https://www.tenders.gov.au",
    "search": "https://www.tenders.gov.au/Search/CnAdvancedSearch",
    "data_gov": "https://data.gov.au/data/dataset?q=austender",
    "grantconnect": "https://www.grants.gov.au",
}


class AustenderSource:
    """Empty Stage 2 adapter — no invented contract notices."""

    name = "austender"
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
                    "Stage 2 stub: map AusTender CN exports into instruments "
                    "(type contract). GrantConnect stays a documented sibling "
                    "for type grant. No invented CNs."
                ),
                "schema": "infra/postgres/007_accountability.sql",
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
            },
        )
