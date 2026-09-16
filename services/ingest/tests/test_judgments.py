from datetime import date
from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.judgments import (
    JudgmentsSource,
    item_from_record,
    links_from_record,
    outcome_from_record,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "judgments"


def test_judgment_maps_citation_and_date() -> None:
    item = item_from_record(
        {
            "citation": "[2014] HCA 23",
            "title": "Williams v Commonwealth of Australia [2014] HCA 23",
            "court": "High Court of Australia",
            "published_on": "2014-06-19",
            "source_url": "https://eresources.hcourt.gov.au/showCase/2014/HCA/23",
            "summary": "Williams (No 2).",
        }
    )
    assert item is not None
    assert item.item_type == "judgment"
    assert item.source_key == "judgment:2014-hca-23"
    assert item.published_on == date(2014, 6, 19)
    assert item.identifiers["citation"] == "[2014] HCA 23"


def test_links_only_allowed_verbs() -> None:
    item = item_from_record({"citation": "[2014] HCA 23", "title": "Williams"})
    links = links_from_record(
        {
            "links": [
                {
                    "instrument_source_key": "frl:C2004A05251",
                    "link_kind": "invalidates",
                    "notes": "s 32B",
                },
                {
                    "instrument_source_key": "frl:C2004A05251",
                    "link_kind": "guilty",
                },
                {"link_kind": "construes"},
            ]
        },
        item,
    )
    assert [lnk.link_kind for lnk in links] == ["invalidates"]
    assert links[0].target_source_key == item.source_key


def test_outcome_is_unknown_not_guilt() -> None:
    item = item_from_record({"citation": "[2023] HCA 37", "title": "NZYQ"})
    outcome = outcome_from_record(
        {"summary": "Construction of detention power.", "links": [{"instrument_source_key": "frl:C1958A00062"}]},
        item,
    )
    assert outcome is not None
    assert outcome.signal == "unknown"
    assert outcome.outcome_type == "court_holding"
    assert "guilt" in (outcome.notes or "").lower() or "not a guilt" in (outcome.notes or "").lower()


def test_judgments_source_fixture() -> None:
    batch = JudgmentsSource(path=FIXTURES).fetch()
    assert batch.scrutiny_items
    assert all(s.item_type == "judgment" for s in batch.scrutiny_items)
    kinds = {lnk.link_kind for lnk in batch.instrument_links}
    assert kinds <= {"construes", "invalidates", "upholds"}
    assert all(o.signal == "unknown" for o in batch.outcomes)


def test_judgments_dry_run() -> None:
    result = run_ingest("judgments", dry_run=True, source_path=str(FIXTURES))
    assert result.status == "dry_run"
    assert result.fetched >= 3
    assert result.meta["instrument_links"] >= 3
    assert result.upserted == 0
