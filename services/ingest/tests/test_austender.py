import json
from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.austender import AustenderSource, instrument_from_cn

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "austender"


def test_ocds_release_maps_contract() -> None:
    payload = json.loads((FIXTURES / "ocds_sample.json").read_text())
    release = payload["releases"][0]
    item = instrument_from_cn(release)
    assert item is not None
    assert item.kind == "contract"
    assert item.identifiers["CN"].startswith("CN")
    assert item.amount_aud and item.amount_aud > 0
    assert item.agency_name
    assert item.supplier_name
    assert item.source_url and "tenders.gov.au" in item.source_url


def test_flat_cn_row() -> None:
    item = instrument_from_cn(
        {
            "CN ID": "CN4267605",
            "title": "Postal services",
            "agency": "Australian Taxation Office",
            "supplier": "AUSTRALIA POST",
            "amount_aud": "42157396.50",
            "source_url": "https://www.tenders.gov.au/Cn/Show/CN4267605",
        }
    )
    assert item is not None
    assert item.source_key == "austender:CN4267605"
    assert item.agency_slug == "australian-taxation-office"
    assert item.amount_aud == 42157396.50


def test_austender_source_sorts_high_value_and_respects_limit() -> None:
    batch = AustenderSource(path=FIXTURES).fetch(limit=2)
    assert batch.source == "austender"
    assert len(batch.instruments) == 2
    amounts = [i.amount_aud or 0 for i in batch.instruments]
    assert amounts == sorted(amounts, reverse=True)
    assert all(i.kind == "contract" for i in batch.instruments)


def test_austender_dry_run() -> None:
    result = run_ingest("austender", dry_run=True, source_path=str(FIXTURES), limit=3)
    assert result.status == "dry_run"
    assert result.fetched >= 2
    assert result.meta["instruments"] >= 2
    assert result.upserted == 0
