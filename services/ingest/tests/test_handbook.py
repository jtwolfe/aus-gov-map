from aus_gov_ingest.sources import SOURCES, get_source


def test_handbook_is_empty_stub() -> None:
    assert "handbook" in SOURCES
    batch = get_source("handbook").fetch(limit=5)
    assert batch.source == "handbook"
    assert batch.hearings == []
    assert batch.people == []
    assert batch.meta["status"] == "not_implemented"
    assert "handbook.aph.gov.au" in batch.meta["home"]
    assert "No invented" in batch.meta["note"] or "No fake" in batch.meta["note"]
