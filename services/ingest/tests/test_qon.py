import json
from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.qon import (
    QonSource,
    map_qon_status,
    qon_number_needles,
    qon_numbers_in_text,
    question_from_eqon,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "qon"


def test_qon_parses_real_detail_fixture() -> None:
    raw = json.loads((FIXTURES / "SE25-0096.json").read_text())
    item = question_from_eqon(raw)
    assert item is not None
    assert item.portfolio_question_number == "SE25-0096"
    assert item.portfolio == "Home Affairs"
    assert item.status == "answered"
    assert item.asked_by and "Chandler" in item.asked_by
    assert item.asked_on and item.asked_on.isoformat() == "2025-10-08"
    assert "Nauru" in (item.question_text or "") or "NZYQ" in (item.question_text or "")


def test_qon_source_fixture_directory_is_thick() -> None:
    batch = QonSource(path=FIXTURES).fetch()
    assert batch.source == "qon"
    assert len(batch.questions) >= 20
    assert batch.meta["by_portfolio"]
    statuses = {q.status for q in batch.questions}
    assert statuses <= {"open", "answered", "overdue", "unknown", "refused"}
    assert "SE25-0096" in {q.portfolio_question_number for q in batch.questions}
    portfolios = {q.portfolio for q in batch.questions if q.portfolio}
    assert len(portfolios) >= 4


def test_qon_dry_run() -> None:
    result = run_ingest("qon", dry_run=True, source_path=str(FIXTURES), limit=12)
    assert result.status == "dry_run"
    assert result.fetched >= 12
    assert result.meta["questions"] >= 12


def test_status_mapping() -> None:
    assert map_qon_status({"Status": "Answered", "Answered": False, "Overdue": "No"}) == "answered"
    assert map_qon_status({"Status": "Unanswered", "Overdue": "Yes"}) == "overdue"
    assert map_qon_status({"Status": "Unanswered", "Overdue": "No"}) == "open"
    assert map_qon_status({"Status": "Withdrawn"}) == "unknown"


def test_qon_number_detection_for_claim_promotion() -> None:
    assert "SE25-0096" in qon_numbers_in_text("We will take SE25-0096 on notice.")
    item = question_from_eqon(json.loads((FIXTURES / "SE25-0096.json").read_text()))
    assert item is not None
    needles = qon_number_needles(item)
    assert "SE25-0096" in needles
