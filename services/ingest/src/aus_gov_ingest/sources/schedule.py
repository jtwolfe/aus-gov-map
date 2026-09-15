from __future__ import annotations

from aus_gov_ingest.models import SourceBatch
from aus_gov_ingest.sources.estimates import EstimatesSource


class EstimatesScheduleSource:
    """'What's new' wrapper: same fetch as Estimates, meant for cron incremental."""

    name = "estimates_schedule"

    def __init__(self) -> None:
        self._inner = EstimatesSource()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        batch = self._inner.fetch(limit=limit, incremental_keys=incremental_keys)
        batch.source = "estimates_schedule"
        batch.meta = {**batch.meta, "mode": "whats_new"}
        return batch
