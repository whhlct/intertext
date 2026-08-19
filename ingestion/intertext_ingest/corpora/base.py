import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from intertext_ingest.normalized import NormalizedVersion, ResolvedVersion


@dataclass(frozen=True)
class CanonicalMappingResult:
    text_id: uuid.UUID
    unit_ids_by_segment: dict[int, tuple[uuid.UUID, ...]]


class CorpusMapper(Protocol):
    def resolve(self, version: NormalizedVersion) -> ResolvedVersion: ...

    def materialize(
        self, session: Session, version: ResolvedVersion
    ) -> CanonicalMappingResult: ...


class CorpusValidator(Protocol):
    def validate(self, version: ResolvedVersion) -> None: ...
