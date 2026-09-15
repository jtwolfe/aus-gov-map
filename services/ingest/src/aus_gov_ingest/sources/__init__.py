from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.sources.aph_transcript_file import AphTranscriptFileSource
from aus_gov_ingest.sources.base import Source
from aus_gov_ingest.sources.estimates import EstimatesSource
from aus_gov_ingest.sources.fixture import FixtureSource
from aus_gov_ingest.sources.openaustralia import OpenAustraliaSource
from aus_gov_ingest.sources.schedule import EstimatesScheduleSource
from aus_gov_ingest.sources.senate_committee import SenateCommitteeSource

SOURCES: dict[str, type] = {
    "fixture": FixtureSource,
    "estimates": EstimatesSource,
    "estimates_schedule": EstimatesScheduleSource,
    "senate_committee": SenateCommitteeSource,
    "aph_transcript_file": AphTranscriptFileSource,
    "openaustralia": OpenAustraliaSource,
}


def get_source(name: str, *, path: str | Path | None = None) -> Source:
    key = name.replace("-", "_").lower()
    if key not in SOURCES:
        known = ", ".join(sorted(SOURCES))
        raise ValueError(f"Unknown source {name!r}. Choose one of: {known}")
    cls = SOURCES[key]
    if key == "aph_transcript_file":
        return cls(path=path)
    if path:
        raise ValueError(f"--path is only valid with aph_transcript_file, not {name!r}")
    return cls()


__all__ = ["Source", "SOURCES", "get_source"]
