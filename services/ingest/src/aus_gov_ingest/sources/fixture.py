from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from aus_gov_ingest.config import settings
from aus_gov_ingest.models import (
    AppearanceIn,
    BoardIn,
    CommitteeIn,
    DocumentIn,
    HearingIn,
    PersonIn,
    PinIn,
    SourceBatch,
    TopicIn,
)


class FixtureSource:
    name = "fixture"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.fixture_path()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        raw = json.loads(self.path.read_text())
        committees = {c["id"]: CommitteeIn.model_validate(c) for c in raw["committees"]}
        people = {p["id"]: PersonIn.model_validate(p) for p in raw["people"]}
        topics = {t["slug"]: TopicIn.model_validate(t) for t in raw["topics"]}
        docs_by_hearing: dict[str, list[DocumentIn]] = {}
        for doc in raw["documents"]:
            docs_by_hearing.setdefault(doc["hearing_id"], []).append(DocumentIn.model_validate(doc))

        hearings: list[HearingIn] = []
        for row in raw["hearings"]:
            if incremental_keys and row["source_key"] in incremental_keys:
                continue
            appearances = []
            for link in row.get("people", []):
                person = people.get(link["person_id"])
                appearances.append(
                    AppearanceIn(
                        person=person,
                        person_id=UUID(link["person_id"]),
                        person_slug=person.slug if person else None,
                        role=link.get("role", "appeared"),
                    )
                )
            hearing_topics = [
                topics[slug] for slug in row.get("topic_slugs", []) if slug in topics
            ]
            hearings.append(
                HearingIn(
                    id=UUID(row["id"]),
                    slug=row["slug"],
                    title=row["title"],
                    hearing_type=row["hearing_type"],
                    portfolio=row.get("portfolio"),
                    held_on=row.get("held_on"),
                    location=row.get("location"),
                    source=row["source"],
                    source_url=row.get("source_url"),
                    source_key=row["source_key"],
                    status=row.get("status", "published"),
                    summary=row.get("summary"),
                    committee=committees.get(row["committee_id"]),
                    committee_id=UUID(row["committee_id"]),
                    people=appearances,
                    topics=hearing_topics,
                    documents=docs_by_hearing.get(row["id"], []),
                )
            )
            if limit and len(hearings) >= limit:
                break

        return SourceBatch(
            source="fixture",
            hearings=hearings,
            people=list(people.values()),
            committees=list(committees.values()),
            topics=list(topics.values()),
            boards=[BoardIn.model_validate(b) for b in raw.get("boards", [])],
            pins=[PinIn.model_validate(p) for p in raw.get("pins", [])],
            meta={"path": str(self.path), "license_note": raw.get("license_note")},
        )
