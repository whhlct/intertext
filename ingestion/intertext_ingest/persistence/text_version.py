from app.models import (
    CanonicalUnit,
    Language,
    PreferredVersion,
    SegmentUnitMapping,
    Text,
    TextVersion,
    VersionRelease,
    VersionSegment,
)
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from intertext_ingest.corpora.base import CanonicalMappingResult
from intertext_ingest.normalized import ImportResult, ResolvedVersion


class TextVersionPersistence:
    IMPORTER_VERSION = "intertext-ingest-1"

    def persist(
        self,
        session: Session,
        dataset: str,
        resolved: ResolvedVersion,
        mapping: CanonicalMappingResult,
        *,
        preferred_role: str | None = None,
    ) -> ImportResult:
        version = resolved.version
        definition = version.definition
        language = session.scalar(
            select(Language).where(Language.iso_code == definition.language_iso)
        )
        if language is None:
            language = Language(
                iso_code=definition.language_iso,
                name=definition.language_name,
                native_name=definition.language_native_name,
                script=definition.script,
                direction=definition.direction,
            )
            session.add(language)
            session.flush()

        conceptual_text = session.get(Text, mapping.text_id)
        if conceptual_text is None:
            raise ValueError(f"Mapped conceptual text was not found: {mapping.text_id}")
        text_version = session.scalar(
            select(TextVersion).where(
                TextVersion.text_id == mapping.text_id,
                TextVersion.slug == definition.slug,
            )
        )
        if text_version is None:
            text_version = TextVersion(
                text_id=mapping.text_id,
                slug=definition.slug,
                title=definition.title,
                abbreviation=definition.abbreviation,
                default_language_id=language.id,
                reference_scheme_id=conceptual_text.default_reference_scheme_id,
                version_type=definition.version_type,
            )
            session.add(text_version)
            session.flush()
        text_version.title = definition.title
        text_version.abbreviation = definition.abbreviation
        text_version.default_language_id = language.id
        text_version.reference_scheme_id = conceptual_text.default_reference_scheme_id
        text_version.version_type = definition.version_type
        text_version.publisher = definition.publisher
        text_version.source_name = version.source.provider
        text_version.license = version.source.license
        text_version.rights_statement = definition.rights_statement
        text_version.source_url = version.source.source_locator

        existing_release = session.scalar(
            select(VersionRelease).where(
                VersionRelease.version_id == text_version.id,
                VersionRelease.source_sha256 == version.source.sha256,
            )
        )
        if existing_release is not None:
            segment_count = (
                session.scalar(
                    select(func.count(VersionSegment.id)).where(
                        VersionSegment.version_release_id == existing_release.id
                    )
                )
                or 0
            )
            mapping_count = (
                session.scalar(
                    select(func.count(SegmentUnitMapping.id))
                    .join(
                        VersionSegment,
                        VersionSegment.id == SegmentUnitMapping.segment_id,
                    )
                    .where(VersionSegment.version_release_id == existing_release.id)
                )
                or 0
            )
            return ImportResult(
                dataset=dataset,
                created=False,
                release_id=str(existing_release.id),
                source_sha256=version.source.sha256,
                segment_count=segment_count,
                mapping_count=mapping_count,
            )

        session.execute(
            update(VersionRelease)
            .where(VersionRelease.version_id == text_version.id)
            .values(is_current=False)
        )
        release_label_base = (
            version.source.textual_version or version.source.source_revision
        )
        release = VersionRelease(
            version_id=text_version.id,
            version_label=f"{release_label_base}-{version.source.sha256[:12]}"[:255],
            source_sha256=version.source.sha256,
            is_current=True,
            metadata_={
                "source": version.source.as_dict(),
                "importer_version": self.IMPORTER_VERSION,
                "parser_versions": [version.parser_version],
            },
        )
        session.add(release)
        session.flush()

        stored_segments: list[tuple[VersionSegment, tuple]] = []
        for resolved_segment in resolved.segments:
            segment = resolved_segment.segment
            unit_ids = mapping.unit_ids_by_segment.get(segment.sequence)
            if not unit_ids:
                raise ValueError(
                    f"No canonical mapping for segment: {resolved_segment.identifier}"
                )
            stored_segment = VersionSegment(
                version_release_id=release.id,
                language_id=language.id,
                sequence=segment.sequence,
                text_plain=segment.text,
                content_markup=segment.content_markup,
                source_identifier=resolved_segment.identifier,
                metadata_=segment.metadata,
            )
            session.add(stored_segment)
            stored_segments.append((stored_segment, unit_ids))
        session.flush()

        mapping_count = 0
        for stored_segment, unit_ids in stored_segments:
            for sequence, unit_id in enumerate(unit_ids):
                session.add(
                    SegmentUnitMapping(
                        segment_id=stored_segment.id,
                        canonical_unit_id=unit_id,
                        sequence=sequence,
                        mapping_type="direct" if len(unit_ids) == 1 else "spans",
                        source=self.IMPORTER_VERSION,
                    )
                )
                mapping_count += 1

        if preferred_role is not None:
            self._set_preferred_version(
                session,
                mapping.text_id,
                text_version,
                mapping.unit_ids_by_segment,
                preferred_role,
            )
        return ImportResult(
            dataset=dataset,
            created=True,
            release_id=str(release.id),
            source_sha256=version.source.sha256,
            segment_count=len(stored_segments),
            mapping_count=mapping_count,
        )

    @staticmethod
    def _set_preferred_version(
        session: Session,
        text_id,
        text_version: TextVersion,
        unit_ids_by_segment: dict,
        role: str,
    ) -> None:
        unit_ids = [unit_id for ids in unit_ids_by_segment.values() for unit_id in ids]
        units = list(
            session.scalars(select(CanonicalUnit).where(CanonicalUnit.id.in_(unit_ids)))
        )
        start_unit = min(units, key=lambda unit: unit.ordinal)
        end_unit = max(units, key=lambda unit: unit.ordinal)
        preferred = session.scalar(
            select(PreferredVersion).where(
                PreferredVersion.text_id == text_id,
                PreferredVersion.version_id == text_version.id,
                PreferredVersion.role == role,
                PreferredVersion.priority == 0,
            )
        )
        if preferred is None:
            preferred = PreferredVersion(
                text_id=text_id,
                start_unit_id=start_unit.id,
                end_unit_id=end_unit.id,
                version_id=text_version.id,
                role=role,
                priority=0,
                notes="Configured by the ingestion pipeline from source coverage.",
            )
            session.add(preferred)
        else:
            preferred.start_unit_id = start_unit.id
            preferred.end_unit_id = end_unit.id
