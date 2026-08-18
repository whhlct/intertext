import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    CanonicalUnit,
    PreferredVersion,
    ReferenceLabel,
    ReferenceScheme,
    SegmentUnitMapping,
    Text,
    TextVersion,
    VersionRelease,
    VersionSegment,
)


def resolve_reference_label(
    session: Session, text: Text, normalized_label: str
) -> ReferenceLabel | None:
    statement = (
        select(ReferenceLabel)
        .join(
            ReferenceScheme,
            ReferenceScheme.id == ReferenceLabel.reference_scheme_id,
        )
        .where(
            ReferenceScheme.text_id == text.id,
            ReferenceLabel.normalized_label == normalized_label,
        )
    )
    if text.default_reference_scheme_id is not None:
        statement = statement.where(
            ReferenceScheme.id == text.default_reference_scheme_id
        )
    return session.scalar(statement.order_by(ReferenceLabel.sort_order).limit(1))


def select_canonical_range(
    text_id: uuid.UUID, start_ordinal: int, end_ordinal: int
) -> Select[tuple[CanonicalUnit]]:
    return (
        select(CanonicalUnit)
        .where(
            CanonicalUnit.text_id == text_id,
            CanonicalUnit.ordinal.between(start_ordinal, end_ordinal),
        )
        .order_by(CanonicalUnit.ordinal)
    )


def select_preferred_roles(
    text_id: uuid.UUID, start_ordinal: int, end_ordinal: int
) -> Select[tuple[uuid.UUID, str, int]]:
    preferred_start = aliased(CanonicalUnit)
    preferred_end = aliased(CanonicalUnit)
    return (
        select(
            PreferredVersion.version_id,
            PreferredVersion.role,
            PreferredVersion.priority,
        )
        .join(preferred_start, preferred_start.id == PreferredVersion.start_unit_id)
        .join(preferred_end, preferred_end.id == PreferredVersion.end_unit_id)
        .where(
            PreferredVersion.text_id == text_id,
            preferred_start.ordinal <= start_ordinal,
            preferred_end.ordinal >= end_ordinal,
        )
        .order_by(PreferredVersion.priority, PreferredVersion.role)
    )


def select_aligned_segments(
    unit_ids: list[uuid.UUID], release_ids: list[uuid.UUID]
) -> Select[tuple[uuid.UUID, uuid.UUID, VersionSegment, SegmentUnitMapping]]:
    return (
        select(
            SegmentUnitMapping.canonical_unit_id,
            TextVersion.id,
            VersionSegment,
            SegmentUnitMapping,
        )
        .join(
            VersionSegment,
            VersionSegment.id == SegmentUnitMapping.segment_id,
        )
        .join(
            VersionRelease,
            VersionRelease.id == VersionSegment.version_release_id,
        )
        .join(TextVersion, TextVersion.id == VersionRelease.version_id)
        .where(
            SegmentUnitMapping.canonical_unit_id.in_(unit_ids),
            VersionRelease.id.in_(release_ids),
        )
        .order_by(
            SegmentUnitMapping.canonical_unit_id,
            TextVersion.id,
            VersionSegment.sequence,
            SegmentUnitMapping.sequence,
        )
    )


def get_unit(session: Session, unit_id: uuid.UUID) -> CanonicalUnit | None:
    return session.get(CanonicalUnit, unit_id)
