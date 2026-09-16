from datetime import date
from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.legislation import (
    LegislationSource,
    instrument_from_frl,
    parse_frl_title_html,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "legislation"


def test_frl_record_maps_act_identifiers() -> None:
    item = instrument_from_frl(
        {
            "frl_id": "C2013A00123",
            "title": "Public Governance, Performance and Accountability Act 2013",
            "instrument_type": "act",
            "status": "in_force",
            "year": 2013,
            "number": 123,
            "as_made_on": "2013-06-29",
            "commenced_on": "2014-07-01",
            "source_url": "https://www.legislation.gov.au/C2013A00123",
            "agency_name": "Department of Finance",
        }
    )
    assert item is not None
    assert item.source_key == "frl:C2013A00123"
    assert item.kind == "act"
    assert item.status == "in_force"
    assert item.identifiers["frl_id"] == "C2013A00123"
    assert item.identifiers["year"] == 2013
    assert item.identifiers["number"] == 123
    assert item.announced_on == date(2013, 6, 29)
    assert item.commenced_on == date(2014, 7, 1)
    assert item.source_url and "legislation.gov.au" in item.source_url


def test_frl_does_not_invent_commencement() -> None:
    item = instrument_from_frl(
        {
            "frl_id": "C2022A00088",
            "title": "National Anti-Corruption Commission Act 2022",
            "instrument_type": "act",
            "status": "in_force",
        }
    )
    assert item is not None
    assert item.commenced_on is None
    assert item.announced_on is None
    assert item.ended_on is None


def test_bill_source_key_stable_without_frl_id() -> None:
    item = instrument_from_frl(
        {
            "title": "National Anti-Corruption Commission Bill 2022",
            "instrument_type": "bill",
            "status": "passed",
            "source_key": "frl:bill:national-anti-corruption-commission-bill-2022",
        }
    )
    assert item is not None
    assert item.kind == "bill"
    assert item.source_key == "frl:bill:national-anti-corruption-commission-bill-2022"
    assert instrument_from_frl(
        {
            "title": "National Anti-Corruption Commission Bill 2022",
            "instrument_type": "bill",
            "status": "passed",
            "source_key": "frl:bill:national-anti-corruption-commission-bill-2022",
        }
    ).source_key == item.source_key


def test_parse_frl_html_extracts_title() -> None:
    html = """
    <html><body>
      <h1>Freedom of Information Act 1982</h1>
      <p>No. 3, 1982</p>
    </body></html>
    """
    record = parse_frl_title_html(
        html, frl_id="C2004A02562", url="https://www.legislation.gov.au/C2004A02562"
    )
    assert record is not None
    assert "Freedom of Information Act 1982" in record["title"]
    assert record["number"] == 3
    assert record["year"] == 1982


def test_legislation_source_fixture_limit() -> None:
    batch = LegislationSource(path=FIXTURES).fetch(limit=3)
    assert batch.source == "legislation"
    assert len(batch.instruments) == 3
    assert all(i.kind in {"bill", "act"} for i in batch.instruments)
    keys = [i.source_key for i in batch.instruments]
    assert len(keys) == len(set(keys))


def test_legislation_dry_run() -> None:
    result = run_ingest("legislation", dry_run=True, source_path=str(FIXTURES), limit=5)
    assert result.status == "dry_run"
    assert result.fetched >= 3
    assert result.meta["instruments"] >= 3
    assert result.upserted == 0
