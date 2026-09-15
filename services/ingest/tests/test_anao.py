from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.anao import (
    AnaoSource,
    item_from_record,
    named_instrument_from_title,
    parse_audit_signal,
    parse_listing_html,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "anao"


def test_parse_listing_html_extracts_real_report_links() -> None:
    html = (FIXTURES / "listing.excerpt.html").read_text(encoding="utf-8")
    records = parse_listing_html(html, base_url="https://www.anao.gov.au")
    titles = {r["title"] for r in records}
    assert any("Biosecurity" in t for t in titles)
    assert any("Security Enhancement Program" in t for t in titles)
    assert all(r["source_url"].startswith("https://www.anao.gov.au/work/") for r in records)
    assert any(r.get("report_number") and "4" in r["report_number"] for r in records)


def test_item_from_fixture_and_partial_outcome() -> None:
    import json

    raw = json.loads((FIXTURES / "report_04_2026-27_biosecurity_cost_recovery.json").read_text())
    item = item_from_record(raw)
    assert item is not None
    assert item.item_type == "anao"
    assert item.source_url and "anao.gov.au" in item.source_url
    assert item.published_on and item.published_on.isoformat() == "2026-07-29"
    assert item.agency_name and "Agriculture" in item.agency_name
    signal, confidence, notes = parse_audit_signal(raw["excerpt"])
    assert signal == "partial"
    assert confidence > 0
    assert "partly effective" in notes


def test_named_instrument_from_sep_title() -> None:
    raw = {
        "title": "Procurement and Contract Management by the Department of Foreign Affairs and Trade for its Security Enhancement Program",
        "source_url": "https://www.anao.gov.au/work/performance-audit/procurement-and-contract-management-by-dfat-for-security-enhancement-program",
        "entity": "Department of Foreign Affairs and Trade",
        "report_number": "Auditor-General Report No. 25 of 2025–26",
        "published_on": "18 March 2026",
    }
    item = item_from_record(raw)
    assert item is not None
    instrument = named_instrument_from_title(item)
    assert instrument is not None
    assert instrument.kind == "program"
    assert "Security Enhancement Program" in instrument.title
    assert instrument.status == "sourced"


def test_signal_does_not_invent_from_empty_text() -> None:
    signal, confidence, notes = parse_audit_signal("")
    assert signal == "unknown"
    assert confidence == 0
    assert notes == ""
    signal, confidence, _ = parse_audit_signal("The objective of the audit was to assess effectiveness.")
    assert confidence == 0


def test_anao_source_fixture_directory() -> None:
    batch = AnaoSource(path=FIXTURES).fetch(limit=5)
    assert batch.source == "anao"
    assert batch.scrutiny_items
    assert all(s.item_type == "anao" for s in batch.scrutiny_items)
    assert all(s.source_url for s in batch.scrutiny_items)
    assert batch.outcomes  # parseable finding language on some fixtures
    assert all(o.confidence > 0 for o in batch.outcomes)
    assert all(o.signal in {"partial", "adverse", "met", "unknown"} for o in batch.outcomes)


def test_anao_dry_run() -> None:
    result = run_ingest("anao", dry_run=True, source_path=str(FIXTURES), limit=4)
    assert result.status == "dry_run"
    assert result.fetched >= 3
    assert result.meta["scrutiny_items"] >= 3
    assert result.upserted == 0
