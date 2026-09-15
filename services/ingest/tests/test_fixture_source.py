from aus_gov_ingest.sources.fixture import FixtureSource


def test_fixture_source_loads_hearings() -> None:
    batch = FixtureSource().fetch()
    assert batch.source == "fixture"
    assert len(batch.hearings) == 3
    assert any(h.hearing_type == "estimates" for h in batch.hearings)
    assert batch.hearings[0].documents
    assert batch.people
    slugs = {h.slug for h in batch.hearings}
    assert "fpa-supp-estimates-2025-10-07" in slugs


def test_limit() -> None:
    batch = FixtureSource().fetch(limit=1)
    assert len(batch.hearings) == 1
