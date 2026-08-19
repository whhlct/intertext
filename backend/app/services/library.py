from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.queries.library import get_text_by_slug, select_texts, select_versions
from app.schemas.library import LanguageSummary, TextSummary, VersionSummary


def list_texts(session: Session) -> list[TextSummary]:
    return [
        TextSummary(
            id=text.id,
            slug=text.slug,
            title=text.title,
            description=text.description,
        )
        for text in session.scalars(select_texts())
    ]


def list_versions(session: Session, text_slug: str) -> list[VersionSummary]:
    text = get_text_by_slug(session, text_slug)
    if text is None:
        raise ResourceNotFoundError(f"Text '{text_slug}' was not found.")

    return [
        VersionSummary(
            id=version.id,
            slug=version.slug,
            title=version.title,
            abbreviation=version.abbreviation,
            version_type=version.version_type,
            language=LanguageSummary(
                iso_code=language.iso_code,
                name=language.name,
                native_name=language.native_name,
                script=language.script,
                direction=language.direction,
            ),
            current_release_id=release.id if release is not None else None,
        )
        for version, language, release in session.execute(
            select_versions(text.id)
        )
    ]
