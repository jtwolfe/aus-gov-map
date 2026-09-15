from aus_gov_ingest.sources import SOURCES, get_source


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


def test_stub_sources_return_empty_with_endpoints() -> None:
    for name in ("anao", "budget_measure", "austender"):
        batch = get_source(name).fetch(limit=3)
        assert batch.source == name
        assert batch.hearings == []
        assert batch.people == []
        assert batch.meta["status"] == "not_implemented"
        assert batch.meta["endpoints"]
        assert "No invented" in batch.meta["note"] or "invent" in batch.meta["note"].lower()
        assert batch.meta["schema"]


def test_qon_is_implemented() -> None:
    src = get_source("qon")
    assert src.name == "qon"
    assert src.ENDPOINTS["eqon_search"].startswith("https://www.aph.gov.au/api/qon/")
