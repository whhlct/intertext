import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidRequestError, ResourceNotFoundError
from app.queries.library import select_available_versions
from app.queries.reader import (
    select_aligned_segments,
    select_canonical_range,
    select_preferred_roles,
)
from app.schemas.library import LanguageSummary
from app.schemas.reader import (
    ReaderReference,
    ReaderResponse,
    ReaderSegment,
    ReaderText,
    ReaderUnit,
    ReaderVersion,
)
from app.services.references import resolve_reference_range


def parse_version_slugs(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(not part for part in parts):
        raise InvalidRequestError(
            "The versions parameter must be a comma-separated list of version slugs."
        )
    return list(dict.fromkeys(parts))


def get_reader(
    session: Session,
    text_slug: str,
    reference: str,
    requested_versions: str | None,
) -> ReaderResponse:
    resolved = resolve_reference_range(session, text_slug, reference)
    text = resolved.text
    label = resolved.label
    start_unit = resolved.start_unit
    end_unit = resolved.end_unit
    requested_slugs = parse_version_slugs(requested_versions) or []
    version_rows = list(
        session.execute(select_available_versions(text.id, requested_slugs or None))
    )
    if requested_slugs:
        rows_by_slug = {row[0].slug: row for row in version_rows}
        missing = [slug for slug in requested_slugs if slug not in rows_by_slug]
        if missing:
            raise ResourceNotFoundError(
                "Versions with current releases were not found: " + ", ".join(missing)
            )
        version_rows = [rows_by_slug[slug] for slug in requested_slugs]

    units = list(
        session.scalars(
            select_canonical_range(text.id, start_unit.ordinal, end_unit.ordinal)
        )
    )
    if not units:
        raise InvalidRequestError(
            f"Reference '{reference}' contains no canonical units."
        )

    roles_by_version: dict[uuid.UUID, list[str]] = defaultdict(list)
    for version_id, role, _priority in session.execute(
        select_preferred_roles(text.id, start_unit.ordinal, end_unit.ordinal)
    ):
        if role not in roles_by_version[version_id]:
            roles_by_version[version_id].append(role)

    segment_map: dict[uuid.UUID, dict[str, list[ReaderSegment]]] = defaultdict(
        lambda: defaultdict(list)
    )
    if version_rows:
        version_slug_by_release = {
            release.id: version.slug for version, _, release in version_rows
        }
        for unit_id, _version_id, segment, mapping in session.execute(
            select_aligned_segments(
                [unit.id for unit in units],
                [release.id for _, _, release in version_rows],
            )
        ):
            version_slug = version_slug_by_release[segment.version_release_id]
            segment_map[unit_id][version_slug].append(
                ReaderSegment(
                    id=segment.id,
                    sequence=segment.sequence,
                    text=segment.text_plain,
                    content_markup=segment.content_markup,
                    mapping_type=mapping.mapping_type,
                )
            )

    versions = [
        ReaderVersion(
            id=version.id,
            slug=version.slug,
            title=version.title,
            abbreviation=version.abbreviation,
            language=LanguageSummary(
                iso_code=language.iso_code,
                name=language.name,
                native_name=language.native_name,
                script=language.script,
                direction=language.direction,
            ),
            roles=roles_by_version[version.id],
        )
        for version, language, _release in version_rows
    ]
    empty_segments = {version.slug: [] for version, _, _ in version_rows}

    return ReaderResponse(
        text=ReaderText(id=text.id, slug=text.slug, title=text.title),
        reference=ReaderReference(
            label=label.label,
            start=start_unit.internal_key,
            end=end_unit.internal_key,
        ),
        versions=versions,
        units=[
            ReaderUnit(
                id=unit.id,
                key=unit.internal_key,
                label=str(unit.metadata_.get("label", unit.ordinal)),
                ordinal=unit.ordinal,
                segments={
                    **empty_segments,
                    **segment_map.get(unit.id, {}),
                },
            )
            for unit in units
        ],
    )
