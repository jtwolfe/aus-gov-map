from __future__ import annotations

from typing import Protocol

from aus_gov_ingest.models import SourceBatch


class Source(Protocol):
    name: str

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        """Return a batch of hearings. limit=0 means no cap."""
        ...
