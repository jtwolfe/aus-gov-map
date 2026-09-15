"""Parliamentary Handbook ingest stub (Stage 2).

Do not invent officials here. Wire a real extract before emitting people.

Intended upstream:
  - Public site: https://handbook.aph.gov.au
  - Historical / companion Handbook data used for senator and member
    biographies, electorate, chamber, party, and role tenure.
  - APH has also published handbook-style APIs / data extracts used by
    parliamentary information services; prefer an official dump over HTML
    scrape when one is available.

Target tables (empty until a real source is connected):
  - handbook_entries.person_id → people.id
  - handbook_roles (ministerial / parliamentary / party roles + dates)
  - handbook_tenure (chamber, electorate, parliament number, start/end)

See infra/postgres/005_handbook.sql.
"""

from __future__ import annotations

from aus_gov_ingest.models import SourceBatch


class HandbookSource:
    """Empty Stage 2 adapter — no fake Handbook rows."""

    name = "handbook"
    HOME = "https://handbook.aph.gov.au"

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        return SourceBatch(
            source=self.name,
            hearings=[],
            people=[],
            committees=[],
            meta={
                "status": "not_implemented",
                "home": self.HOME,
                "note": (
                    "Stage 2 stub: fetch Handbook officials (tenure, electorate, "
                    "roles) and link to people. No invented data."
                ),
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
                "schema": "infra/postgres/005_handbook.sql",
            },
        )
