from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from intertext_ingest.datasets import DatasetDefinition
from intertext_ingest.normalized import (
    ImportResult,
    NormalizedSegment,
    NormalizedVersion,
    ParsedSource,
    VersionDefinition,
)
from intertext_ingest.persistence.text_version import TextVersionPersistence
from intertext_ingest.validation.text_version import (
    validate_normalized_version,
    validate_persisted_release,
    validate_resolved_version,
)


class IngestionPipeline:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory
        self.persistence = TextVersionPersistence()

    def run(
        self,
        dataset: DatasetDefinition,
        *,
        raw_root: Path,
        refresh: bool = False,
    ) -> ImportResult:
        acquired = dataset.source.acquire(raw_root, refresh=refresh)
        parsed = dataset.parser.parse(acquired)
        normalized = self._normalize(parsed, dataset.version)
        validate_normalized_version(normalized)
        resolved = dataset.corpus_mapper.resolve(normalized)
        validate_resolved_version(resolved)
        dataset.corpus_validator.validate(resolved)

        with self.session_factory() as session:
            try:
                mapping = dataset.corpus_mapper.materialize(session, resolved)
                result = self.persistence.persist(
                    session,
                    dataset.name,
                    resolved,
                    mapping,
                    preferred_role=dataset.preferred_role,
                )
                session.flush()
                validate_persisted_release(
                    session,
                    result.release_id,
                    expected_segment_count=len(resolved.segments),
                )
                session.commit()
            except Exception:
                session.rollback()
                raise
        return result

    @staticmethod
    def _normalize(
        parsed: ParsedSource, definition: VersionDefinition
    ) -> NormalizedVersion:
        return NormalizedVersion(
            definition=definition,
            source=parsed.source,
            parser_version=parsed.parser_version,
            segments=tuple(
                NormalizedSegment(
                    sequence=segment.sequence,
                    language_iso=definition.language_iso,
                    text=segment.text,
                    source_reference=segment.source_reference,
                    content_markup=segment.content_markup,
                    metadata=segment.metadata,
                    tokens=segment.tokens,
                )
                for segment in parsed.segments
            ),
        )
