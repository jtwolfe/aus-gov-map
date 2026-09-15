from aus_gov_ingest.sources import SOURCES, get_source
from aus_gov_ingest.sources.handbook import ENDPOINTS, parse_individuals_odata


def test_handbook_is_registered_empty_stub() -> None:
    assert "handbook" in SOURCES
    batch = get_source("handbook").fetch(limit=5)
    assert batch.source == "handbook"
    assert batch.hearings == []
    assert batch.people == []
    assert batch.meta["status"] == "not_implemented"
    assert "handbook.aph.gov.au" in batch.meta["home"]
    assert "No invented" in batch.meta["note"] or "invent officials" in batch.meta["note"]
    assert "individuals" in batch.meta["endpoints"]
    assert ENDPOINTS["ministry_records"].startswith("https://handbookapi.aph.gov.au")


def test_parse_individuals_odata_maps_only_complete_rows() -> None:
    payload = {
        "value": [
            {
                "PHID": "TEST-PHID-1",
                "DisplayName": "Example, Senator A",
                "Party": "Independent",
                "SenateState": "TAS",
                "Electorate": None,
            },
            {"PHID": None, "DisplayName": "Missing id"},
            {"DisplayName": "", "PHID": "x"},
        ]
    }
    people = parse_individuals_odata(payload)
    assert len(people) == 1
    assert people[0].name == "Example, Senator A"
    assert people[0].party == "Independent"
    assert people[0].slug
