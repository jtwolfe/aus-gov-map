from datetime import date

from aus_gov_ingest.models import QuestionOnNoticeIn
from aus_gov_ingest.qon_hearing import (
    HearingCandidate,
    apply_hearing_match,
    committees_match,
    match_qon_to_hearing,
    portfolios_match,
)
from aus_gov_ingest.sources.qon import question_from_eqon


def _qon(**kwargs) -> QuestionOnNoticeIn:
    defaults = dict(
        source_key="qon:eqon:test",
        portfolio="Home Affairs",
        committee_name="Legal and Constitutional Affairs",
        asked_on=date(2025, 3, 27),
    )
    defaults.update(kwargs)
    return QuestionOnNoticeIn(**defaults)


def _hearing(**kwargs) -> HearingCandidate:
    defaults = dict(
        source_key="hansard:committees/estimate/28779",
        held_on=date(2025, 3, 27),
        title="Legal and Constitutional Affairs Legislation Committee — Estimates",
        portfolio="Home Affairs",
        committee_name="Legal and Constitutional Affairs",
        hearing_type="estimates",
        hearing_id="11111111-1111-1111-1111-111111111111",
    )
    defaults.update(kwargs)
    return HearingCandidate(**defaults)


def test_committees_and_portfolios_normalize() -> None:
    assert committees_match("Legal and Constitutional Affairs", "Senate Legal and Constitutional Affairs Legislation Committee")
    assert portfolios_match("Health, Disability and Ageing", "Health")
    assert not committees_match("Community Affairs", "Finance and Public Administration")
    assert not portfolios_match("Home Affairs", "Finance")


def test_unique_committee_date_portfolio_matches() -> None:
    match = match_qon_to_hearing(_qon(), [_hearing()])
    assert match is not None
    assert match.hearing_source_key == "hansard:committees/estimate/28779"
    assert match.confidence >= 0.75
    assert "committee" in match.reason
    assert "portfolio" in match.reason


def test_does_not_match_wrong_committee_on_same_day() -> None:
    other = _hearing(
        source_key="hansard:committees/estimate/28778",
        title="Finance and Public Administration Legislation Committee — Estimates",
        committee_name="Finance and Public Administration",
        portfolio="Parliamentary Departments",
    )
    match = match_qon_to_hearing(_qon(), [other])
    assert match is None


def test_skips_when_two_hearings_tie() -> None:
    a = _hearing(source_key="hansard:committees/estimate/aaa")
    b = _hearing(source_key="hansard:committees/estimate/bbb")
    assert match_qon_to_hearing(_qon(), [a, b]) is None


def test_date_outside_window_is_not_linked() -> None:
    far = _hearing(held_on=date(2025, 10, 8))
    assert match_qon_to_hearing(_qon(asked_on=date(2025, 3, 27)), [far]) is None


def test_fixture_hearing_source_key_wins() -> None:
    qon = _qon(hearing_source_key="hansard:committees/estimate/29000")
    hearings = [
        _hearing(),
        _hearing(
            source_key="hansard:committees/estimate/29000",
            held_on=date(2025, 10, 9),
            committee_name="Community Affairs",
            portfolio="Health, Disability and Ageing",
        ),
    ]
    match = match_qon_to_hearing(qon, hearings)
    assert match is not None
    assert match.source == "qon_fixture"
    assert match.hearing_source_key == "hansard:committees/estimate/29000"
    attached = apply_hearing_match(qon, match)
    assert attached.metadata["hearing_match"]["confidence"] >= 0.9


def test_eqon_row_reads_fixture_hearing_key() -> None:
    item = question_from_eqon(
        {
            "Id": 1,
            "Number": 4,
            "PortfolioQuestionNumber": "CA25-OFFICIAL",
            "AskedDate": "2025-10-09",
            "Committee": "Community Affairs",
            "Portfolio": "Health, Disability and Ageing",
            "Agency": "Department of Health, Disability and Ageing",
            "Status": "Unanswered",
            "_hearing_source_key": "hansard:committees/estimate/29000",
            "QuestionText": "How many specialised campaigns has Medicare run in the last four years?",
        }
    )
    assert item is not None
    assert item.hearing_source_key == "hansard:committees/estimate/29000"
    assert item.committee_name == "Community Affairs"


def test_official_ton_fixtures_name_hearing_keys() -> None:
    from pathlib import Path

    from aus_gov_ingest.pipeline import run_ingest

    qon_dir = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "qon"
    expected = {
        "CA25-29000.json": "hansard:committees/estimate/29000",
        "FPA25-28778.json": "hansard:committees/estimate/28778",
        "LCA25-28779.json": "hansard:committees/estimate/28779",
        "EE25-29001.json": "hansard:committees/estimate/29001",
    }
    for name, key in expected.items():
        payload = (qon_dir / name).read_text(encoding="utf-8")
        assert f'"_hearing_source_key": "{key}"' in payload
    result = run_ingest("qon", dry_run=True, source_path=str(qon_dir), limit=80)
    assert result.status == "dry_run"
    assert result.meta.get("qons_with_hearing_key", 0) >= 4
