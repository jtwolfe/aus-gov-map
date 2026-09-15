from pathlib import Path

from aus_gov_ingest.sources import SOURCES, get_source

LIVE = Path(__file__).resolve().parents[1] / "fixtures" / "live"


def test_accountability_sources_are_registered() -> None:
    for name in (
        "handbook",
        "qon",
        "anao",
        "budget_measure",
        "austender",
        "agencies",
        "instrument_propose",
    ):
        assert name in SOURCES


def test_first_pass_adapters_return_rows_from_fixtures() -> None:
    paths = {
        "anao": LIVE / "anao",
        "budget_measure": LIVE / "budget",
        "austender": LIVE / "austender",
    }
    for name in ("anao", "budget_measure", "austender"):
        src = get_source(name, path=str(paths[name]))
        batch = src.fetch(limit=3)
        assert batch.source == name
        assert batch.meta.get("status") in {"ok", "empty"}
        assert batch.meta["endpoints"]
        assert batch.meta["schema"]
        note = (batch.meta.get("note") or "").lower()
        assert "invent" in note
        if name == "anao":
            assert batch.scrutiny_items
        else:
            assert batch.instruments


def test_qon_is_implemented() -> None:
    src = get_source("qon")
    assert src.name == "qon"
    assert src.ENDPOINTS["eqon_search"].startswith("https://www.aph.gov.au/api/qon/")
