import uuid

from app.models import SegmentUnitMapping, VersionRelease, VersionSegment
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from intertext_ingest.normalized import NormalizedVersion, ResolvedVersion


def validate_normalized_version(version: NormalizedVersion) -> None:
    if not version.segments:
        raise ValueError(f"Normalized version has no segments: {version.slug}")
    expected_sequences = list(range(1, len(version.segments) + 1))
    actual_sequences = [segment.sequence for segment in version.segments]
    if actual_sequences != expected_sequences:
        raise ValueError(f"Non-contiguous segment ordering in {version.slug}")
    if any(not segment.text.strip() for segment in version.segments):
        raise ValueError(f"Empty segment text in {version.slug}")
    if any(
        segment.language_iso != version.definition.language_iso
        for segment in version.segments
    ):
        raise ValueError(f"Mixed or incorrect segment languages in {version.slug}")
    source_references = [
        (segment.source_reference.scheme, segment.source_reference.label)
        for segment in version.segments
    ]
    if len(source_references) != len(set(source_references)):
        raise ValueError(f"Duplicate source references in {version.slug}")


def validate_resolved_version(version: ResolvedVersion) -> None:
    expected_sequences = list(range(1, len(version.segments) + 1))
    actual_sequences = [item.segment.sequence for item in version.segments]
    if actual_sequences != expected_sequences:
        raise ValueError(f"Non-contiguous resolved ordering in {version.version.slug}")
    missing = [
        item.segment.source_reference.label
        for item in version.segments
        if not item.canonical_targets
    ]
    if missing:
        raise ValueError(
            f"Segments lack canonical targets in {version.version.slug}: "
            + ", ".join(missing[:5])
        )
    if any(not item.identifier.strip() for item in version.segments):
        raise ValueError(f"Empty resolved identifier in {version.version.slug}")


def validate_persisted_release(
    session: Session,
    release_id: str,
    *,
    expected_segment_count: int,
) -> None:
    parsed_release_id = uuid.UUID(release_id)
    release = session.get(VersionRelease, parsed_release_id)
    if release is None:
        raise ValueError(f"Persisted release was not found: {release_id}")
    segment_count = (
        session.scalar(
            select(func.count(VersionSegment.id)).where(
                VersionSegment.version_release_id == parsed_release_id
            )
        )
        or 0
    )
    if segment_count != expected_segment_count:
        raise ValueError(
            f"Persisted segment count mismatch: {segment_count} != "
            f"{expected_segment_count}"
        )
    mapping_count = (
        session.scalar(
            select(func.count(SegmentUnitMapping.id))
            .join(VersionSegment, VersionSegment.id == SegmentUnitMapping.segment_id)
            .where(VersionSegment.version_release_id == parsed_release_id)
        )
        or 0
    )
    if mapping_count < segment_count:
        raise ValueError(
            f"Persisted release has unmapped segments: {mapping_count} mappings for "
            f"{segment_count} segments"
        )
