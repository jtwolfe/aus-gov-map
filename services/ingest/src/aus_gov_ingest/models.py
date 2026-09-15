from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PersonRole = Literal["chair", "senator", "minister", "official", "witness", "appeared"]
HearingType = Literal["estimates", "committee", "other"]


class CommitteeIn(BaseModel):
    id: UUID | None = None
    slug: str
    name: str
    chamber: str = "Senate"
    kind: str = "legislation"
    aph_url: str | None = None


class PersonIn(BaseModel):
    id: UUID | None = None
    slug: str
    name: str
    role_title: str | None = None
    party: str | None = None
    portfolio: str | None = None
    organisation: str | None = None
    aph_url: str | None = None
    bio: str | None = None


class AppearanceIn(BaseModel):
    person: PersonIn | None = None
    person_id: UUID | None = None
    person_slug: str | None = None
    role: PersonRole = "appeared"


class TopicIn(BaseModel):
    id: UUID | None = None
    slug: str
    name: str


class DocumentIn(BaseModel):
    id: UUID | None = None
    title: str
    doc_type: str = "hansard"
    source_url: str | None = None
    source_key: str
    content_text: str | None = None
    published_at: date | None = None
    license_note: str | None = None


class HearingIn(BaseModel):
    id: UUID | None = None
    slug: str
    title: str
    hearing_type: HearingType = "estimates"
    portfolio: str | None = None
    held_on: date | None = None
    location: str | None = "Parliament House, Canberra"
    source: str
    source_url: str | None = None
    source_key: str
    status: str = "published"
    summary: str | None = None
    committee: CommitteeIn | None = None
    committee_id: UUID | None = None
    people: list[AppearanceIn] = Field(default_factory=list)
    topics: list[TopicIn] = Field(default_factory=list)
    documents: list[DocumentIn] = Field(default_factory=list)


class BoardIn(BaseModel):
    id: UUID | None = None
    slug: str
    title: str
    description: str | None = None


class PinIn(BaseModel):
    id: UUID | None = None
    board_slug: str | None = None
    board_id: UUID | None = None
    pin_type: str
    target_id: UUID
    note: str | None = None


class SourceBatch(BaseModel):
    source: str
    hearings: list[HearingIn] = Field(default_factory=list)
    people: list[PersonIn] = Field(default_factory=list)
    committees: list[CommitteeIn] = Field(default_factory=list)
    topics: list[TopicIn] = Field(default_factory=list)
    boards: list[BoardIn] = Field(default_factory=list)
    pins: list[PinIn] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
