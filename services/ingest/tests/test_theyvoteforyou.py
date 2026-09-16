from datetime import date
from pathlib import Path

from aus_gov_ingest.people import names_are_same_person
from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.theyvoteforyou import (
    TheyVoteForYouSource,
    division_from_record,
    vote_from_record,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "tvfy"


def test_division_maps_bill_and_votes() -> None:
    item = division_from_record(
        {
            "house": "representatives",
            "date": "2022-11-24",
            "number": 4,
            "name": "National Anti-Corruption Commission Bill 2022 - Consideration in Detail",
            "source_url": "https://theyvoteforyou.org.au/divisions/representatives/2022-11-24/4",
            "bills": [
                {
                    "title": "National Anti-Corruption Commission Bill 2022",
                    "instrument_source_key": "frl:bill:national-anti-corruption-commission-bill-2022",
                }
            ],
            "votes": [
                {"name": "Mark Dreyfus", "vote": "aye", "party": "Australian Labor Party"},
                {"name": "Helen Haines", "vote": "no", "party": "Independent"},
                {"name": "Anthony Albanese", "vote": "absent"},
            ],
        }
    )
    assert item is not None
    assert item.source_key == "tvfy:representatives:2022-11-24:4"
    assert item.divided_on == date(2022, 11, 24)
    assert item.instrument_source_key == "frl:bill:national-anti-corruption-commission-bill-2022"
    assert [v.vote for v in item.votes] == ["aye", "no", "absent"]
    assert item.ayes is None  # do not invent chamber totals


def test_tvfy_yes_maps_to_aye() -> None:
    vote = vote_from_record({"name": "Mark Dreyfus", "vote": "Yes"})
    assert vote is not None
    assert vote.vote == "aye"


def test_tvfy_nested_member_name() -> None:
    vote = vote_from_record(
        {
            "vote": "no",
            "member": {
                "name": {"first": "Helen", "last": "Haines"},
                "party": "Independent",
                "electorate": "Indi",
            },
        }
    )
    assert vote is not None
    assert vote.person_name == "Helen Haines"
    assert vote.electorate == "Indi"


def test_source_does_not_emit_people() -> None:
    batch = TheyVoteForYouSource(path=FIXTURES).fetch()
    assert batch.people == []
    assert batch.person_roles == []
    assert batch.divisions
    assert all(d.votes for d in batch.divisions)
    assert batch.meta["people_emitted"] == 0


def test_vote_resolution_requires_existing_name() -> None:
    """Matching helper used at persist — last names must agree; no invented MP."""
    assert names_are_same_person("Senator the Hon Penny Wong", "Penny Wong")
    assert not names_are_same_person("Mark Dreyfus", "Invented Official")
    assert not names_are_same_person("Helen Haines", "Helen Smith")


def test_upsert_key_stable_across_parses() -> None:
    row = {
        "house": "senate",
        "date": "2022-11-29",
        "number": 2,
        "name": "Example Bill 2022",
    }
    assert division_from_record(row).source_key == division_from_record(row).source_key


def test_tvfy_dry_run() -> None:
    result = run_ingest("theyvoteforyou", dry_run=True, source_path=str(FIXTURES))
    assert result.status == "dry_run"
    assert result.fetched >= 1
    assert result.meta["divisions"] >= 1
    assert result.meta["named_votes"] >= 1
    assert result.upserted == 0
