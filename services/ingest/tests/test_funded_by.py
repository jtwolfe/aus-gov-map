from datetime import date

from aus_gov_ingest.funded_by import agencies_match, match_funded_by, title_contained
from aus_gov_ingest.models import InstrumentIn
from aus_gov_ingest.pipeline import run_ingest


def _program() -> InstrumentIn:
    return InstrumentIn(
        source_key="budget:2025-26:program-1-2-child-care-subsidy:department-of-educat",
        title="Program 1.2: Child Care Subsidy",
        kind="program",
        status="sourced",
        agency_name="Department of Education",
        identifiers={"year": "2025-26"},
    )


def _contract(**kwargs) -> InstrumentIn:
    defaults = dict(
        source_key="austender:CN4195346",
        title="Provision of Detection and Targeting services for Child Care Subsidy (CCS) Integrity Risks.",
        kind="contract",
        status="sourced",
        agency_name="Department of Education",
        commenced_on=date(2025, 10, 1),
        ended_on=date(2027, 6, 30),
        identifiers={"CN": "CN4195346"},
    )
    defaults.update(kwargs)
    return InstrumentIn(**defaults)


def test_title_and_agency_helpers() -> None:
    assert title_contained(
        "Provision of Detection and Targeting services for Child Care Subsidy (CCS) Integrity Risks.",
        "Program 1.2: Child Care Subsidy",
    )
    assert agencies_match("Department of Education", "Department of Education")
    assert not title_contained("Postal services", "Program 1.2: Child Care Subsidy")
    assert not title_contained("A short", "Hi")


def test_sourced_title_agency_period_match() -> None:
    matches = match_funded_by([_contract()], [_program()])
    assert len(matches) == 1
    assert matches[0].funder_source_key.endswith("child-care-subsidy:department-of-educat")
    assert matches[0].confidence >= 0.8
    assert matches[0].reason == "title+agency+period"


def test_skips_weak_title_or_wrong_agency() -> None:
    other_agency = _contract(agency_name="Australian Taxation Office")
    assert match_funded_by([other_agency], [_program()]) == []
    weak = _contract(title="Advisory services")
    assert match_funded_by([weak], [_program()]) == []


def test_skips_ambiguous_funders() -> None:
    twin = InstrumentIn(
        source_key="budget:2025-26:program-1-2-child-care-subsidy:other",
        title="Program 1.2: Child Care Subsidy",
        kind="program",
        status="sourced",
        agency_name="Department of Education",
        identifiers={"year": "2025-26"},
    )
    assert match_funded_by([_contract()], [_program(), twin]) == []


def test_explicit_fixture_key() -> None:
    contract = _contract(
        title="Unrelated wording",
        identifiers={
            "CN": "CN4195346",
            "funded_by_source_key": _program().source_key,
        },
    )
    matches = match_funded_by([contract], [_program()])
    assert len(matches) == 1
    assert matches[0].reason == "fixture_funded_by_source_key"


def test_austender_dry_run_emits_funded_by_when_pbs_fixture_matches() -> None:
    from pathlib import Path

    austender = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "austender"
    result = run_ingest("austender", dry_run=True, source_path=str(austender), limit=10)
    assert result.status == "dry_run"
    assert result.meta.get("funded_by_links", 0) >= 1
