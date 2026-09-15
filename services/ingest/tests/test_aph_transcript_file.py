from __future__ import annotations

import json
from pathlib import Path

import pytest

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.aph_transcript_file import AphTranscriptFileSource

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LIVE_TRANSCRIPTS = FIXTURES / "live" / "transcripts"
EXCERPT = FIXTURES / "transcript_fpa_28778_excerpt.json"


def test_single_excerpt_file(tmp_path: Path) -> None:
    dest = tmp_path / "28778.json"
    dest.write_text(EXCERPT.read_text(), encoding="utf-8")
    batch = AphTranscriptFileSource(path=dest).fetch()
    assert batch.source == "aph_transcript_file"
    assert len(batch.hearings) == 1
    hearing = batch.hearings[0]
    assert hearing.source == "estimates"
    assert hearing.hearing_type == "estimates"
    assert hearing.source_key == "hansard:committees/estimate/28778"
    assert hearing.documents
    assert "I declare open this hearing" in (hearing.documents[0].content_text or "")
    assert hearing.committee and "Finance" in hearing.committee.name


def test_directory_limit_and_incremental(tmp_path: Path) -> None:
    (tmp_path / "28778.json").write_text(EXCERPT.read_text(), encoding="utf-8")
    extra = json.loads(EXCERPT.read_text())
    extra["SystemId"] = "committees/estimate/29629/0000"
    extra["MainTitle"] = "Community Affairs Legislation Committee - 05/06/2026 - Estimates"
    extra["Date"] = "05/06/2026"
    (tmp_path / "29629.json").write_text(json.dumps(extra), encoding="utf-8")

    limited = AphTranscriptFileSource(path=tmp_path).fetch(limit=1)
    assert len(limited.hearings) == 1

    skipped = AphTranscriptFileSource(path=tmp_path).fetch(
        incremental_keys={"hansard:committees/estimate/28778"}
    )
    assert [h.source_key for h in skipped.hearings] == ["hansard:committees/estimate/29629"]


def test_rejects_html(tmp_path: Path) -> None:
    dest = tmp_path / "29629.json"
    dest.write_text("<!DOCTYPE html><html><body>challenge</body></html>\n", encoding="utf-8")
    batch = AphTranscriptFileSource(path=dest).fetch()
    assert batch.hearings == []
    assert batch.meta["errors"]
    assert "HTML" in batch.meta["errors"][0]


def test_live_fixtures_are_api_json() -> None:
    expected = ("29617.json", "29625.json", "29629.json")
    for name in expected:
        path = LIVE_TRANSCRIPTS / name
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8").lstrip()
        assert text.startswith("{"), f"{name} is not JSON"
        payload = json.loads(text)
        assert payload.get("TalkText"), f"{name} missing TalkText"
        assert "committees/estimate/" in str(payload.get("SystemId"))

    batch = AphTranscriptFileSource(path=LIVE_TRANSCRIPTS).fetch()
    assert len(batch.hearings) == 3
    assert all(h.documents for h in batch.hearings)
    titles = " ".join(h.title for h in batch.hearings)
    assert "Community Affairs" in titles
    assert "Economics" in titles
    assert "Education and Employment" in titles
    assert {h.source_key for h in batch.hearings} == {
        "hansard:committees/estimate/29617",
        "hansard:committees/estimate/29625",
        "hansard:committees/estimate/29629",
    }


def test_dry_run_live_fixtures() -> None:
    result = run_ingest(
        "aph_transcript_file",
        dry_run=True,
        source_path=str(LIVE_TRANSCRIPTS),
    )
    assert result.status == "dry_run"
    assert result.fetched == 3
    assert result.upserted == 0
    assert result.meta["with_transcript"] == 3


def test_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        AphTranscriptFileSource(path=missing).fetch()
