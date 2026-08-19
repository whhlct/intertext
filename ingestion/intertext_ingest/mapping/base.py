import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from intertext_ingest.normalized import NormalizedSegment


@dataclass(frozen=True)
class CanonicalMappingResult:
    text_id: uuid.UUID
    unit_ids_by_reference: dict[str, tuple[uuid.UUID, ...]]


class CanonicalMapper(Protocol):
    def map_segments(
        self, session: Session, segments: tuple[NormalizedSegment, ...]
    ) -> CanonicalMappingResult: ...
