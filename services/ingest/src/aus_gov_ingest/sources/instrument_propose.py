"""Propose decision-object candidates from Estimates Official text.

Output rows are status='proposed' with low confidence. Not asserted facts.
"""

from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.chunking import chunk_text
from aus_gov_ingest.instruments import propose_instruments
from aus_gov_ingest.models import InstrumentIn, SourceBatch
from aus_gov_ingest.segments import annotate_chunks, parse_official_segments
from aus_gov_ingest.sources.aph_transcript_file import AphTranscriptFileSource, default_transcript_dir


class InstrumentProposeSource:
    name = "instrument_propose"

    def __init__(self, *, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_transcript_dir()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        hearings = AphTranscriptFileSource(path=self.path).fetch(
            limit=limit, incremental_keys=None
        ).hearings
        known = incremental_keys or set()
        instruments: list[InstrumentIn] = []
        for hearing in hearings:
            for document in hearing.documents:
                text = document.content_text or ""
                segments = parse_official_segments(text)
                chunks = annotate_chunks(chunk_text(text), segments)
                proposed = propose_instruments(
                    chunks,
                    hearing_source_key=hearing.source_key,
                    document_source_key=document.source_key,
                )
                for item in proposed:
                    if item.source_key in known:
                        continue
                    instruments.append(item)
            if limit and len(hearings) >= limit:
                # limit applies to source hearings scanned, not instrument count
                pass
        return SourceBatch(
            source=self.name,
            hearings=[],
            instruments=instruments,
            meta={
                "status": "proposed_only",
                "path": str(self.path),
                "hearings_scanned": len(hearings),
                "proposed": len(instruments),
                "by_kind": _count_kind(instruments),
                "note": (
                    "Candidates only. Low confidence. Linked to chunk source_key "
                    "when Officials have been ingested. Human review required."
                ),
            },
        )


def _count_kind(items: list[InstrumentIn]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts
