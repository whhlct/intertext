from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from intertext_ingest.datasets import DatasetDefinition
from intertext_ingest.mapping.bible import BibleCanonicalMapper
from intertext_ingest.normalized import ImportResult
from intertext_ingest.persistence.text_version import TextVersionPersistence
from intertext_ingest.validation.text_version import (
    validate_normalized_version,
    validate_persisted_release,
)


class IngestionPipeline:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory
        self.persistence = TextVersionPersistence(BibleCanonicalMapper())

    def run(
        self,
        dataset: DatasetDefinition,
        *,
        raw_root: Path,
        refresh: bool = False,
    ) -> ImportResult:
        acquired = dataset.source.acquire(raw_root, refresh=refresh)
        normalized = dataset.parser.parse(acquired)
        validate_normalized_version(
            normalized,
            required_reference_keys=dataset.required_reference_keys,
            require_unique_references=dataset.require_unique_references,
        )

        with self.session_factory() as session:
            try:
                result = self.persistence.persist(
                    session,
                    dataset.name,
                    normalized,
                    preferred_role=dataset.preferred_role,
                )
                session.flush()
                validate_persisted_release(
                    session,
                    result.release_id,
                    expected_segment_count=len(normalized.segments),
                )
                session.commit()
            except Exception:
                session.rollback()
                raise
        return result
