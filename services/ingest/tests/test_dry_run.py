from aus_gov_ingest.pipeline import run_ingest


def test_fixture_dry_run_needs_no_database() -> None:
    result = run_ingest("fixture", dry_run=True)
    assert result.status == "dry_run"
    assert result.fetched == 3
    assert result.upserted == 0
    assert result.meta["titles"]
