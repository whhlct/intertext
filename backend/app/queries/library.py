import uuid

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.models import (
    CanonicalUnit,
    Language,
    SegmentUnitMapping,
    Text,
    TextVersion,
    VersionRelease,
    VersionSegment,
)


def select_texts() -> Select[tuple[Text]]:
    return select(Text).order_by(Text.title, Text.slug)


def get_text_by_slug(session: Session, text_slug: str) -> Text | None:
    return session.scalar(select(Text).where(Text.slug == text_slug))


def select_available_versions(
    text_id: uuid.UUID, version_slugs: list[str] | None = None
) -> Select[tuple[TextVersion, Language, VersionRelease]]:
    statement = (
        select(TextVersion, Language, VersionRelease)
        .join(Language, Language.id == TextVersion.default_language_id)
        .join(
            VersionRelease,
            and_(
                VersionRelease.version_id == TextVersion.id,
                VersionRelease.is_current.is_(True),
            ),
        )
        .where(TextVersion.text_id == text_id)
    )
    if version_slugs:
        statement = statement.where(TextVersion.slug.in_(version_slugs))
    return statement.order_by(TextVersion.title, TextVersion.slug)


def select_versions(
    text_id: uuid.UUID,
) -> Select[tuple[TextVersion, Language, VersionRelease | None]]:
    return (
        select(TextVersion, Language, VersionRelease)
        .join(Language, Language.id == TextVersion.default_language_id)
        .outerjoin(
            VersionRelease,
            and_(
                VersionRelease.version_id == TextVersion.id,
                VersionRelease.is_current.is_(True),
            ),
        )
        .where(TextVersion.text_id == text_id)
        .order_by(TextVersion.title, TextVersion.slug)
    )


def select_versions_available_in_range(
    text_id: uuid.UUID, start_ordinal: int, end_ordinal: int
) -> Select[tuple[TextVersion, Language, VersionRelease]]:
    has_mapped_content = (
        select(1)
        .select_from(VersionSegment)
        .join(
            SegmentUnitMapping,
            SegmentUnitMapping.segment_id == VersionSegment.id,
        )
        .join(
            CanonicalUnit,
            CanonicalUnit.id == SegmentUnitMapping.canonical_unit_id,
        )
        .where(
            VersionSegment.version_release_id == VersionRelease.id,
            CanonicalUnit.text_id == text_id,
            CanonicalUnit.ordinal.between(start_ordinal, end_ordinal),
        )
        .exists()
    )
    return (
        select(TextVersion, Language, VersionRelease)
        .join(Language, Language.id == TextVersion.default_language_id)
        .join(
            VersionRelease,
            and_(
                VersionRelease.version_id == TextVersion.id,
                VersionRelease.is_current.is_(True),
            ),
        )
        .where(
            TextVersion.text_id == text_id,
            has_mapped_content,
        )
        .order_by(TextVersion.title, TextVersion.slug)
    )
