import json
from pathlib import Path

from aus_gov_ingest.chunking import chunk_text, extract_speaker
from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.segments import annotate_chunks, is_taken_on_notice, parse_official_segments
from aus_gov_ingest.sources.hansard import hearing_from_transcript, hit_from_transcript_payload

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXCERPT = FIXTURES / "transcript_fpa_28778_excerpt.json"


def test_parse_excerpt_headers_and_speakers() -> None:
    payload = json.loads(EXCERPT.read_text())
    segments = parse_official_segments(payload["TalkText"])
    kinds = {s.kind for s in segments}
    assert "portfolio_header" in kinds
    assert "agency_header" in kinds
    assert "speaker_turn" in kinds
    portfolios = {s.portfolio for s in segments if s.portfolio}
    assert any("Parliamentary" in (p or "") for p in portfolios)
    agencies = {s.agency for s in segments if s.agency}
    assert any("Parliamentary Services" in (a or "") for a in agencies)
    assert any(s.speaker_name and "CHAIR" in s.speaker_name for s in segments)
    assert any(is_taken_on_notice(s.content) for s in segments)


def test_hearing_from_transcript_attaches_segments() -> None:
    payload = json.loads(EXCERPT.read_text())
    hit = hit_from_transcript_payload(payload)
    hearing = hearing_from_transcript(hit, payload, source="estimates", hearing_type="estimates")
    assert hearing.segments
    assert hearing.portfolio
    chunks = annotate_chunks(chunk_text(hearing.documents[0].content_text or ""), hearing.segments)
    assert chunks
    assert any(c.speaker_name for c in chunks)


def test_extract_speaker_variants() -> None:
    assert extract_speaker("CHAIR: Hello") == "CHAIR"
    assert extract_speaker("Senator PATERSON: How many SES roles?")
    assert extract_speaker("Ms Hinchcliffe: I'll take that on notice.")


def test_text_fallback_portfolio_and_ton() -> None:
    text = (
        "FINANCE PORTFOLIO\n"
        "Department of Finance\n"
        "CHAIR: We turn to outcome 2.\n"
        "Ms Example: I will take that on notice.\n"
    )
    segments = parse_official_segments(text)
    assert any(s.kind == "portfolio_header" for s in segments)
    assert any(s.kind == "agency_header" for s in segments)
    assert any(s.kind == "taken_on_notice" for s in segments)
    assert any(s.portfolio and "Finance" in s.portfolio for s in segments)


def test_aph_transcript_dry_run_reports_segments() -> None:
    result = run_ingest(
        "aph_transcript_file",
        dry_run=True,
        source_path=str(EXCERPT),
    )
    assert result.status == "dry_run"
    assert result.fetched == 1
    assert result.meta.get("segments", 0) >= 1
