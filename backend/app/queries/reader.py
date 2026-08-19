import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import aliased

from app.models import (
    CanonicalUnit,
    EnrichmentImport,
    Language,
    PreferredVersion,
    SegmentUnitMapping,
    TextVersion,
    Token,
    TokenGloss,
    VersionRelease,
    VersionSegment,
)


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


def select_segment_tokens(segment_ids: list[uuid.UUID]) -> Select:
    return (
        select(Token, TokenGloss, Language, EnrichmentImport)
        .outerjoin(TokenGloss, TokenGloss.token_id == Token.id)
        .outerjoin(Language, Language.id == TokenGloss.target_language_id)
        .outerjoin(
            EnrichmentImport,
            EnrichmentImport.id == TokenGloss.enrichment_import_id,
        )
        .where(Token.segment_id.in_(segment_ids), Token.is_word.is_(True))
        .order_by(
            Token.segment_id,
            Token.token_index,
            EnrichmentImport.imported_at.desc(),
        )
    )
