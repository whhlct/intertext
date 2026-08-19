import uuid

from app.models import SegmentUnitMapping, VersionRelease, VersionSegment
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from intertext_ingest.normalized import NormalizedVersion


def validate_normalized_version(
    version: NormalizedVersion,
    *,
    required_reference_keys: tuple[str, ...] = (),
    require_unique_references: bool = False,
) -> None:
    if not version.segments:
        raise ValueError(f"Normalized version has no segments: {version.slug}")
    expected_sequences = list(range(1, len(version.segments) + 1))
    actual_sequences = [segment.sequence for segment in version.segments]
    if actual_sequences != expected_sequences:
        raise ValueError(f"Non-contiguous segment ordering in {version.slug}")
    if any(not segment.text.strip() for segment in version.segments):
        raise ValueError(f"Empty segment text in {version.slug}")
    if any(
        segment.language_iso != version.language_iso for segment in version.segments
    ):
        raise ValueError(f"Mixed or incorrect segment languages in {version.slug}")

    references = [segment.reference.key for segment in version.segments]
    if require_unique_references and len(references) != len(set(references)):
        raise ValueError(f"Duplicate source references in {version.slug}")
    missing = sorted(set(required_reference_keys) - set(references))
    if missing:
        raise ValueError(
            f"Required references missing from {version.slug}: {', '.join(missing)}"
        )
    if version.slug == "kjv":
        leaked_markers = [
            segment.source_reference
            for segment in version.segments
            if "\\w" in segment.text or "strong=" in segment.text
        ]
        if leaked_markers:
            raise ValueError(
                "Strong's/USFM markers leaked into KJV plain text at: "
                + ", ".join(leaked_markers[:5])
            )


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
