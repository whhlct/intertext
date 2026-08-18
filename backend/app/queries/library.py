import uuid

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.models import Language, Text, TextVersion, VersionRelease


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
