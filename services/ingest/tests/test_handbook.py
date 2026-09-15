from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources import SOURCES, get_source
from aus_gov_ingest.sources.handbook import ENDPOINTS, HandbookSource, entry_from_individual, parse_individuals_odata

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "handbook"


def test_handbook_is_registered() -> None:
    assert "handbook" in SOURCES
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


def test_handbook_parses_committed_fixture() -> None:
    batch = HandbookSource(path=FIXTURES).fetch(limit=3)
    assert batch.source == "handbook"
    assert batch.meta["status"] == "ok"
    assert len(batch.people) >= 2
    assert len(batch.handbook_entries) >= 2
    names = " ".join(p.name for p in batch.people)
    assert "Albanese" in names or "Abdo" in names
    albanese = next(e for e in batch.handbook_entries if e.handbook_key == "R36")
    assert albanese.party and "Labor" in albanese.party
    assert any(r.role_kind == "ministry" for r in albanese.roles)
    assert any(t.electorate == "Grayndler" for t in albanese.tenure)
    assert "handbook.aph.gov.au" in batch.meta["home"]
    assert "secretar" in batch.meta["gaps"].lower()
    assert "individuals" in batch.meta["endpoints"]


def test_handbook_dry_run_uses_fixture_path() -> None:
    result = run_ingest("handbook", dry_run=True, source_path=str(FIXTURES), limit=2)
    assert result.status == "dry_run"
    assert result.fetched >= 2
    assert result.upserted == 0
    assert result.meta["handbook_entries"] >= 2
    assert result.meta["handbook_roles"] >= 1


def test_entry_from_individual_maps_chamber() -> None:
    entry = entry_from_individual(
        {
            "PHID": "00AOU",
            "GivenName": "Penelope",
            "MiddleNames": "",
            "FamilyName": "WONG",
            "DisplayName": "WONG, the Hon. Penelope Ying-Yen",
            "Party": "Australian Labor Party",
            "Electorate": "",
            "SenateState": "South Australia",
            "MPorSenator": ["Senator"],
            "ElectorateService": [],
            "PartyParliamentaryService": [
                {
                    "RoSType": "Parliamentary Service",
                    "Value": "WONG",
                    "DateStart": "2002-07-01",
                    "DateEnd": "1900-01-01",
                    "SecondaryService": [
                        {
                            "RoSType": "Parties Represented",
                            "Value": "Australian Labor Party",
                            "DateStart": "2002-07-01",
                            "DateEnd": "1900-01-01",
                        }
                    ],
                }
            ],
            "RepresentedParliaments": [47, 48],
        },
        ministries=[
            {
                "PHID": "00AOU",
                "Role": "Minister",
                "Prep": "for",
                "Entity": "Foreign Affairs",
                "RDateStart": "2022-05-23",
                "RDateEnd": "",
                "Ministry": "Albanese Ministry",
            }
        ],
    )
    assert entry is not None
    assert entry.chamber == "Senate"
    assert entry.person.slug == "penelope-wong"
    assert any(r.role_kind == "ministry" and "Foreign Affairs" in r.role_title for r in entry.roles)
    assert any(t.chamber == "Senate" for t in entry.tenure)


def test_get_source_handbook_path() -> None:
    src = get_source("handbook", path=str(FIXTURES))
    assert src.name == "handbook"
