import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.library import LanguageSummary


class ReaderText(BaseModel):
    id: uuid.UUID
    slug: str
    title: str


class ReaderReference(BaseModel):
    label: str
    start: str
    end: str


class ReaderVersion(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    abbreviation: str | None
    language: LanguageSummary
    roles: list[str] = Field(default_factory=list)


class ReaderTokenGloss(BaseModel):
    gloss: str
    gloss_type: str
    source: str
    language: LanguageSummary


class ReaderToken(BaseModel):
    id: uuid.UUID
    index: int
    surface: str
    normalized: str | None
    char_start: int | None
    char_end: int | None
    glosses: list[ReaderTokenGloss] = Field(default_factory=list)


class ReaderSegment(BaseModel):
    id: uuid.UUID
    sequence: int
    text: str
    content_markup: dict[str, Any]
    mapping_type: str
    tokens: list[ReaderToken] = Field(default_factory=list)


class ReaderUnit(BaseModel):
    id: uuid.UUID
    key: str
    label: str
    ordinal: int
    segments: dict[str, list[ReaderSegment]]


class ReaderResponse(BaseModel):
    text: ReaderText
    reference: ReaderReference
    versions: list[ReaderVersion]
    units: list[ReaderUnit]
