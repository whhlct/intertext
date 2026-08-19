import uuid

from pydantic import BaseModel


class CanonicalRangeEndpoint(BaseModel):
    id: uuid.UUID
    key: str
    ordinal: int


class ReferenceResolution(BaseModel):
    text_slug: str
    input: str
    normalized_reference: str
    label: str
    reference_scheme: str
    start: CanonicalRangeEndpoint
    end: CanonicalRangeEndpoint
