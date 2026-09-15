from aus_gov_ingest.people import (
    canonical_slug,
    infer_role,
    names_are_same_person,
    should_skip_person,
    split_name_and_role,
    strip_honorifics,
    unwrap_official_label,
)
from aus_gov_ingest.sources.hansard import _people_from_official


def test_strip_honorifics_and_slug() -> None:
    assert strip_honorifics("Senator the Hon James Paterson") == "James Paterson"
    assert canonical_slug("Senator the Hon James Paterson") == "james-paterson"
    assert canonical_slug("Mr James Paterson") == "james-paterson"
    assert canonical_slug("Ms Jaala Hinchcliffe, Secretary") == "jaala-hinchcliffe"
    assert canonical_slug("Ms Nicola Hinder PSM") == "nicola-hinder"
    assert canonical_slug("Professor Glyn Davis AC") == "glyn-davis"
    assert canonical_slug("Prof. DAVIS") == "davis"


def test_safer_merge() -> None:
    assert names_are_same_person("Senator James Paterson", "Mr James Paterson")
    assert names_are_same_person("Prof. DAVIS", "Professor Glyn Davis AC")
    assert names_are_same_person("Senator Lines", "Senator the Hon Sue Lines")
    assert not names_are_same_person("Senator Paterson", "Senator Scarr")
    assert not names_are_same_person("Jane Smith", "John Smith")


def test_skip_chair_label() -> None:
    assert should_skip_person("CHAIR")
    assert should_skip_person("Witness")
    assert not should_skip_person("Senator Pratt")


def test_unwrap_and_role() -> None:
    assert unwrap_official_label("CHAIR (Senator Pratt)") == "Senator Pratt"
    name, role = split_name_and_role("Ms Jaala Hinchcliffe, Secretary")
    assert name == "Ms Jaala Hinchcliffe"
    assert role == "Secretary"
    assert infer_role("Senator", "Chair") == "chair"
    assert infer_role("Ms", "Secretary") == "official"


def test_people_from_official_attendance() -> None:
    text = """
In Attendance
Senator Lines, President of the Senate
Ms Jaala Hinchcliffe, Secretary
Ms Nicola Hinder PSM, Acting Deputy Secretary
Committee met at 09:02
CHAIR (Senator Pratt): I declare open this hearing
"""
    people = _people_from_official(text)
    slugs = {p.person_slug for p in people}
    assert "jaala-hinchcliffe" in slugs
    assert "nicola-hinder" in slugs
    assert "lines" in slugs
    assert all(not (p.person and p.person.slug.startswith("ms-")) for p in people)
    assert all(not (p.person and p.person.slug.startswith("senator-")) for p in people)
