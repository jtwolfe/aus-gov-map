from pathlib import Path

from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources.agencies import AgenciesSource

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "agencies.json"


def test_agencies_seed_fixture() -> None:
    batch = AgenciesSource(path=FIXTURES).fetch()
    slugs = {a.slug for a in batch.agencies}
    assert "finance" in slugs
    assert "prime-minister-cabinet" in slugs
    assert "home-affairs" in slugs
    assert all(a.name for a in batch.agencies)
    assert batch.meta["gaps"]
    assert "secretar" in batch.meta["gaps"].lower()


def test_agencies_dry_run() -> None:
    result = run_ingest("agencies", dry_run=True, source_path=str(FIXTURES))
    assert result.status == "dry_run"
    assert result.fetched >= 16
    assert result.upserted == 0
