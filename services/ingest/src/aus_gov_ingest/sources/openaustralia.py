from __future__ import annotations

from aus_gov_ingest.models import SourceBatch


class OpenAustraliaSource:
    """Hook for later: OpenAustralia / TheyWorkForYou-AU XML dumps.

    https://data.openaustralia.org.au/ serves chamber Hansard XML (Senate /
    House debates) and is reachable without the APH WAF. It does **not**
    cover Senate Estimates or committee Officials — those come from the
    APH Hansard API used by the estimates / senate_committee adapters.
    This adapter stays a no-op for Stage 1.
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
