from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.sources.agencies import AgenciesSource
from aus_gov_ingest.sources.anao import AnaoSource
from aus_gov_ingest.sources.aps_leaders import ApsLeadersSource
from aus_gov_ingest.sources.aph_transcript_file import AphTranscriptFileSource
from aus_gov_ingest.sources.austender import AustenderSource
from aus_gov_ingest.sources.base import Source
from aus_gov_ingest.sources.budget_measure import BudgetMeasureSource
from aus_gov_ingest.sources.estimates import EstimatesSource
from aus_gov_ingest.sources.fixture import FixtureSource
from aus_gov_ingest.sources.handbook import HandbookSource
from aus_gov_ingest.sources.instrument_propose import InstrumentProposeSource
from aus_gov_ingest.sources.openaustralia import OpenAustraliaSource
from aus_gov_ingest.sources.qon import QonSource
from aus_gov_ingest.sources.schedule import EstimatesScheduleSource
from aus_gov_ingest.sources.senate_committee import SenateCommitteeSource

SOURCES: dict[str, type] = {
    "fixture": FixtureSource,
    "estimates": EstimatesSource,
    "estimates_schedule": EstimatesScheduleSource,
    "senate_committee": SenateCommitteeSource,
    "aph_transcript_file": AphTranscriptFileSource,
    "openaustralia": OpenAustraliaSource,
    "handbook": HandbookSource,
    "qon": QonSource,
    "anao": AnaoSource,
    "budget_measure": BudgetMeasureSource,
    "austender": AustenderSource,
    "agencies": AgenciesSource,
    "aps_leaders": ApsLeadersSource,
    "instrument_propose": InstrumentProposeSource,
}

PATH_SOURCES = {
    "aph_transcript_file",
    "handbook",
    "qon",
    "agencies",
    "aps_leaders",
    "instrument_propose",
    "anao",
    "budget_measure",
    "austender",
}


def get_source(name: str, *, path: str | Path | None = None) -> Source:
    key = name.replace("-", "_").lower()
    if key not in SOURCES:
        known = ", ".join(sorted(SOURCES))
        raise ValueError(f"Unknown source {name!r}. Choose one of: {known}")
    cls = SOURCES[key]
    if path and key not in PATH_SOURCES:
        allowed = ", ".join(sorted(PATH_SOURCES))
        raise ValueError(f"--path is only valid with {allowed}, not {name!r}")
    if key in PATH_SOURCES:
        return cls(path=path)
    return cls()


__all__ = ["Source", "SOURCES", "PATH_SOURCES", "get_source"]
