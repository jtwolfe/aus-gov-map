"""Budget / PBS measure ingest stub (Stage 2).

Do not invent measures or amounts. ``fetch()`` returns an empty batch.

Intended upstream:
  - Budget Papers: https://budget.gov.au
  - Portfolio Budget Statements:
    https://www.finance.gov.au/publications/portfolio-budget-statements
  - Mid-Year Economic and Fiscal Outlook / additional estimates statements
    on the same Finance and Treasury sites.
  - data.gov.au occasionally hosts machine-readable Budget tables;
    prefer those over PDF scrape.

Each measure / program becomes an ``instruments`` row
(type measure|program) with nullable amounts and PBS identifiers.

Target tables: ``instruments``, ``instrument_links`` (FUNDED_BY, ACCOUNTABLE_FOR).
See docs/accountability-map.md.
"""

from __future__ import annotations

from aus_gov_ingest.models import SourceBatch

ENDPOINTS = {
    "budget": "https://budget.gov.au",
    "pbs": "https://www.finance.gov.au/publications/portfolio-budget-statements",
    "treasury_budget": "https://treasury.gov.au/publication",
    "data_gov": "https://data.gov.au/data/organization/department-of-the-treasury",
}


class BudgetMeasureSource:
    """Empty Stage 2 adapter — no invented Budget measures."""

    name = "budget_measure"
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
                    "Stage 2 stub: map PBS / Budget Paper measures into "
                    "instruments (type measure|program). No invented amounts."
                ),
                "schema": "infra/postgres/007_accountability.sql",
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
            },
        )
