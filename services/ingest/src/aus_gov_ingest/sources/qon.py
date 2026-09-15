"""Questions on Notice ingest stub (Stage 2).

Do not invent QoNs or answers. ``fetch()`` returns an empty batch.

Intended upstream (public pages; no stable bulk JSON yet):
  - Senate Estimates hub:
    https://www.aph.gov.au/Parliamentary_Business/Senate_estimates
  - Committee QoN / additional information tabs on each Estimates program
    (PDF / Word answers; ParlInfo document ids).
  - Chamber questions:
    House: https://www.aph.gov.au/Parliamentary_Business/Statistics/House_of_Representatives_Statistics
    Senate questions: ParlInfo search + Notice Paper.
  - Hansard “taken on notice” spans already land in Stage 1 ``chunks``;
    promote those to ``claims.claim_type = taken_on_notice`` and ``qons``.

Target tables: ``qons``, ``scrutiny_items`` (type qon), ``claims``.
See docs/accountability-map.md and infra/postgres/007_accountability.sql.
"""

from __future__ import annotations

from aus_gov_ingest.models import SourceBatch

ENDPOINTS = {
    "estimates_hub": "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates",
    "parlinfo": "https://parlinfo.aph.gov.au/",
    "house_questions": "https://www.aph.gov.au/Parliamentary_Business/Chamber_documents/HoR/Questions_and_Answers",
}


class QonSource:
    """Empty Stage 2 adapter — no invented questions on notice."""

    name = "qon"
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
                    "Stage 2 stub: parse Estimates / chamber QoN lists into qons "
                    "(number, house, portfolio, asker, answering minister/agency, "
                    "asked_on, due_on, answered_on, status). No invented rows."
                ),
                "schema": "infra/postgres/007_accountability.sql",
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
            },
        )
