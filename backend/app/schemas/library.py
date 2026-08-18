import uuid

from pydantic import BaseModel


class TextSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str | None


class LanguageSummary(BaseModel):
    iso_code: str
    name: str
    native_name: str | None
    script: str | None
    direction: str


class VersionSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    abbreviation: str | None
    version_type: str
    language: LanguageSummary
    current_release_id: uuid.UUID | None

