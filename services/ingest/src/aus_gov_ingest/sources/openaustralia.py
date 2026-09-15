from __future__ import annotations

from aus_gov_ingest.models import SourceBatch


class OpenAustraliaSource:
    """Hook for later: OpenAustralia / TheyWorkForYou-AU XML dumps.

    See http://data.openaustralia.org.au/ — Hansard XML is useful once Stage 1
    Estimates coverage is stable. This adapter is intentionally a no-op.
    """

    name = "openaustralia"
    DATA_HOME = "http://data.openaustralia.org.au/"

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        return SourceBatch(
            source="openaustralia",
            hearings=[],
            meta={
                "status": "not_implemented",
                "note": "Stage 2 hook — parse OpenAustralia XML Hansard dumps.",
                "home": self.DATA_HOME,
                "limit": limit,
                "skipped_existing": len(incremental_keys or []),
            },
        )
