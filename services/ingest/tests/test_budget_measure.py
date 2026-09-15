from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.budget_measure import (
    BudgetMeasureSource,
    instrument_from_budget_row,
    parse_bp2_paragraphs,
    parse_pbs_csv,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "budget"


def test_parse_pbs_csv_excerpt() -> None:
    text = (FIXTURES / "pbs_2025-26_programs.excerpt.csv").read_text(encoding="utf-8")
    rows = parse_pbs_csv(text)
    titles = {r["title"] for r in rows}
    assert any("Child Care Subsidy" in t for t in titles)
    assert any("Housing Assistance" in t for t in titles)
    ccs = next(r for r in rows if "Child Care Subsidy" in r["title"])
    assert ccs["agency_name"] == "Department of Education"
    assert ccs["kind"] == "program"
    assert ccs["year_amounts"]["2025-26"] == 16242013


def test_parse_bp2_paragraphs_extracts_named_measures() -> None:
    paragraphs = [
        "AGRICULTURE, FISHERIES AND FORESTRY",
        "Department of Agriculture, Fisheries and Forestry",
        "Securing the Future of Agricultural Trade(b)",
        "-",
        "-9.6",
        "-",
        "-",
        "-",
        "Portfolio total",
        "-",
        "-9.6",
        "-",
        "-",
        "-",
        "EDUCATION",
        "Department of Education",
        "National Student Ombudsman – cost recovery",
        "-",
        "-",
        "10.9",
        "11.1",
        "11.2",
    ]
    rows = parse_bp2_paragraphs(paragraphs, year="2026-27")
    titles = [r["title"] for r in rows]
    assert "Securing the Future of Agricultural Trade" in titles
    assert "National Student Ombudsman – cost recovery" in titles
    assert all(r["kind"] == "measure" for r in rows)
    agri = next(r for r in rows if r["title"].startswith("Securing"))
    assert agri["agency_name"] == "Department of Agriculture, Fisheries and Forestry"
    assert agri["year_amounts"]["2026-27"] == -9.6


def test_instrument_from_budget_row_measure() -> None:
    item = instrument_from_budget_row(
        {
            "title": "Water Reform – continuing funding",
            "kind": "measure",
            "portfolio": "Climate Change",
            "agency_name": "Department of Climate Change, Energy, the Environment and Water",
            "year": "2026-27",
            "year_amounts": {"2026-27": 1.4},
            "source_url": "https://budget.gov.au/content/bp2/index.htm",
            "citation": "BP2 2026–27",
        }
    )
    assert item is not None
    assert item.kind == "measure"
    assert item.amount_aud == 1.4
    assert item.source_url and "budget.gov.au" in item.source_url
    assert item.status == "sourced"


def test_budget_source_fixture_directory() -> None:
    batch = BudgetMeasureSource(path=FIXTURES).fetch(limit=8)
    assert batch.source == "budget_measure"
    assert batch.instruments
    kinds = {i.kind for i in batch.instruments}
    assert "measure" in kinds
    assert "program" in kinds
    assert all(i.source_url for i in batch.instruments)


def test_budget_dry_run() -> None:
    result = run_ingest("budget_measure", dry_run=True, source_path=str(FIXTURES), limit=5)
    assert result.status == "dry_run"
    assert result.fetched >= 3
    assert result.meta["instruments"] >= 3
    assert result.upserted == 0
