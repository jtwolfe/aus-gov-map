from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PersonRole = Literal["chair", "senator", "minister", "official", "witness", "appeared"]
HearingType = Literal["estimates", "committee", "other"]
QonStatus = Literal["open", "answered", "overdue", "unknown"]
InstrumentKind = Literal["bill", "program", "contract", "grant", "other"]
SegmentKind = Literal[
    "portfolio_header",
    "agency_header",
    "speaker_turn",
    "taken_on_notice",
    "other",
]


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
    segments: list["HearingSegmentIn"] = Field(default_factory=list)


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


class AgencyIn(BaseModel):
    slug: str
    name: str
    short_code: str | None = None
    portfolio: str | None = None
    kind: str = "department"
    source_url: str | None = None
    notes: str | None = None


class HandbookRoleIn(BaseModel):
    role_title: str
    role_kind: str | None = None
    started_on: date | None = None
    ended_on: date | None = None
    notes: str | None = None


class HandbookTenureIn(BaseModel):
    chamber: str | None = None
    electorate: str | None = None
    parliament_number: int | None = None
    started_on: date | None = None
    ended_on: date | None = None


class HandbookEntryIn(BaseModel):
    handbook_key: str
    person: PersonIn
    display_name: str
    chamber: str | None = None
    electorate: str | None = None
    party: str | None = None
    aph_url: str | None = None
    roles: list[HandbookRoleIn] = Field(default_factory=list)
    tenure: list[HandbookTenureIn] = Field(default_factory=list)


class QuestionOnNoticeIn(BaseModel):
    source_key: str
    qon_number: str | None = None
    portfolio_question_number: str | None = None
    portfolio: str | None = None
    agency_slug: str | None = None
    agency_name: str | None = None
    asked_by: str | None = None
    asked_on: date | None = None
    due_on: date | None = None
    answered_on: date | None = None
    status: QonStatus = "unknown"
    question_text: str | None = None
    answer_text: str | None = None
    source_url: str | None = None
    hearing_source_key: str | None = None
    committee_name: str | None = None
    estimates_round: str | None = None
    metadata: dict = Field(default_factory=dict)


class InstrumentIn(BaseModel):
    source_key: str
    title: str
    kind: InstrumentKind = "other"
    status: str = "proposed"
    confidence: float = 0.3
    source_chunk_key: str | None = None
    hearing_source_key: str | None = None
    evidence_text: str | None = None
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)


class HearingSegmentIn(BaseModel):
    kind: SegmentKind
    speaker_name: str | None = None
    portfolio: str | None = None
    agency: str | None = None
    content: str
    char_start: int | None = None
    char_end: int | None = None
    metadata: dict = Field(default_factory=dict)


class SourceBatch(BaseModel):
    source: str
    hearings: list[HearingIn] = Field(default_factory=list)
    people: list[PersonIn] = Field(default_factory=list)
    committees: list[CommitteeIn] = Field(default_factory=list)
    topics: list[TopicIn] = Field(default_factory=list)
    boards: list[BoardIn] = Field(default_factory=list)
    pins: list[PinIn] = Field(default_factory=list)
    agencies: list[AgencyIn] = Field(default_factory=list)
    handbook_entries: list[HandbookEntryIn] = Field(default_factory=list)
    questions: list[QuestionOnNoticeIn] = Field(default_factory=list)
    instruments: list[InstrumentIn] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


HearingIn.model_rebuild()
SourceBatch.model_rebuild()
