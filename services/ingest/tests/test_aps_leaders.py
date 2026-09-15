from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources import SOURCES, get_source
from aus_gov_ingest.sources.aps_leaders import (
    ENDPOINTS,
    classify_role,
    month_year_to_date,
    occupancy_from_record,
    parse_heading_staff_html,
    parse_treasury_executive_html,
)
from aus_gov_ingest.sources.util import parse_flexible_date

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "aps"


def test_aps_leaders_is_registered() -> None:
    assert "aps_leaders" in SOURCES
    assert ENDPOINTS["directory"].startswith("https://www.directory.gov.au")


def test_month_year_and_iso_dates() -> None:
    assert month_year_to_date("June", "2025").isoformat() == "2025-06-01"
    assert month_year_to_date("August", 2022).isoformat() == "2022-08-01"
    assert month_year_to_date(None, 2025) is None
    assert parse_flexible_date("2025-06-01").isoformat() == "2025-06-01"


def test_classify_role() -> None:
    assert classify_role("Secretary to the Australian Treasury") == "secretary"
    assert classify_role("Deputy Secretary, Fiscal Group") == "deputy"
    assert classify_role("Director-General, Housing Group") == "agency_head"


def test_occupancy_from_record_does_not_invent_dates() -> None:
    item = occupancy_from_record(
        {
            "name": "Stephanie Foster",
            "role_title": "Secretary",
            "role_type": "secretary",
            "agency_slug": "home-affairs",
            "agency_name": "Department of Home Affairs",
            "portfolio": "Home Affairs",
            "source_url": "https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff",
        }
    )
    assert item is not None
    assert item.start_date is None
    assert item.end_date is None
    assert item.source_url.endswith("our-senior-staff")
    assert item.person.slug == "stephanie-foster"


def test_parse_treasury_executive_excerpt() -> None:
    html = (FIXTURES / "treasury_executive.excerpt.html").read_text()
    rows = parse_treasury_executive_html(
        html,
        source_url="https://treasury.gov.au/the-department/about-treasury/our-executive",
    )
    names = {r.person.name for r in rows}
    assert "Jenny Wilkinson" in names
    secretary = next(r for r in rows if r.role_type == "secretary" and r.agency and r.agency.slug == "treasury")
    assert secretary.start_date and secretary.start_date.isoformat() == "2025-06-01"
    assert secretary.end_date is None
    finance = next(r for r in rows if r.agency and r.agency.slug == "finance")
    assert finance.start_date and finance.end_date
    assert finance.end_date >= finance.start_date
    assert any(r.role_type == "deputy" and "Damien White" in r.person.name for r in rows)


def test_parse_home_affairs_excerpt() -> None:
    html = (FIXTURES / "home_affairs_senior_staff.excerpt.html").read_text()
    rows = parse_heading_staff_html(
        html,
        agency_slug="home-affairs",
        agency_name="Department of Home Affairs",
        portfolio="Home Affairs",
        source_url="https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff",
    )
    names = {r.person.name for r in rows}
    assert "Stephanie Foster" in names
    assert "Clare Sharp" in names
    assert all(r.start_date is None and r.end_date is None for r in rows)


def test_aps_leaders_fixture_and_dry_run() -> None:
    src = get_source("aps_leaders", path=str(FIXTURES / "leaders.json"))
    batch = src.fetch()
    assert batch.source == "aps_leaders"
    assert len(batch.person_roles) >= 8
    assert any(pr.role_type == "secretary" for pr in batch.person_roles)
    assert any("Wilkinson" in pr.person.name for pr in batch.person_roles)
    assert any(pr.agency and pr.agency.slug == "home-affairs" for pr in batch.person_roles)
    assert "secretar" in batch.meta["gaps"].lower() or "wayback" in batch.meta["gaps"].lower()

    result = run_ingest("aps_leaders", dry_run=True, source_path=str(FIXTURES / "leaders.json"), limit=4)
    assert result.status == "dry_run"
    assert result.fetched >= 4
    assert result.upserted == 0
    assert result.meta["occupancies"] >= 4
    assert result.meta["leaders_sample"]
