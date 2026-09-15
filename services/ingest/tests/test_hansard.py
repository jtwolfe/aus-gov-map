from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.sources.hansard import (
    HansardHit,
    hearing_from_transcript,
    html_to_text,
    parse_search_hits,
)
from aus_gov_ingest.sources.util import parse_date, slug

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_date_formats() -> None:
    assert str(parse_date("27 March 2025")) == "2025-03-27"
    assert str(parse_date("05 Jun 2026")) == "2026-06-05"
    assert str(parse_date("27/03/2025")) == "2025-03-27"
    assert slug("Finance and Public Administration") == "finance-and-public-administration"


def test_parse_search_hits_unique_documents() -> None:
    html = (FIXTURES / "hansard_search_estimates.html").read_text()
    hits = parse_search_hits(html, kinds=("estimate",))
    assert [document_id(h) for h in hits] == ["29629", "28778"]
    assert hits[0].sid == "0000"
    assert hits[0].held_on_text and "2026" in hits[0].held_on_text


def document_id(hit: HansardHit) -> str:
    return hit.bid.strip("/").split("/")[-1]


def test_hearing_from_real_excerpt() -> None:
    import json

    payload = json.loads((FIXTURES / "transcript_fpa_28778_excerpt.json").read_text())
    hit = HansardHit(
        title="Finance and Public Administration Legislation Committee;27/03/2025;Estimates",
        bid="committees/estimate/28778/",
        sid="0000",
        kind="estimate",
        display_url="https://www.aph.gov.au/Parliamentary_Business/Hansard/Hansard_Display?bid=committees/estimate/28778/&sid=0000",
        held_on_text="27 Mar 2025",
    )
    hearing = hearing_from_transcript(hit, payload, source="estimates", hearing_type="estimates")
    assert hearing.held_on.isoformat() == "2025-03-27"
    assert hearing.hearing_type == "estimates"
    assert hearing.source_key == "hansard:committees/estimate/28778"
    assert hearing.documents
    text = hearing.documents[0].content_text or ""
    assert "I declare open this hearing" in text
    assert "Ngunnawal" in text
    assert any(p.person and "Hinchcliffe" in p.person.name for p in hearing.people)
    assert hearing.committee and "Finance" in hearing.committee.name


def test_html_to_text_strips_tags() -> None:
    assert html_to_text("<p>CHAIR: Hello</p>") == "CHAIR: Hello"
