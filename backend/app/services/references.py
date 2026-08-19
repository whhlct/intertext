import unicodedata
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidRequestError, ResourceNotFoundError
from app.models import CanonicalUnit, ReferenceLabel, ReferenceScheme, Text
from app.queries.library import get_text_by_slug
from app.queries.references import get_unit, resolve_reference_label
from app.schemas.references import CanonicalRangeEndpoint, ReferenceResolution


@dataclass(frozen=True)
class ResolvedReferenceRange:
    text: Text
    label: ReferenceLabel
    scheme: ReferenceScheme
    start_unit: CanonicalUnit
    end_unit: CanonicalUnit
    input: str
    normalized_input: str


def normalize_reference(reference: str) -> str:
    normalized = unicodedata.normalize("NFKC", reference)
    return " ".join(normalized.casefold().split())


def resolve_reference_range(
    session: Session, text_slug: str, reference: str
) -> ResolvedReferenceRange:
    text = get_text_by_slug(session, text_slug)
    if text is None:
        raise ResourceNotFoundError(f"Text '{text_slug}' was not found.")

    normalized_reference = normalize_reference(reference)
    label = resolve_reference_label(session, text, normalized_reference)
    if label is None:
        raise ResourceNotFoundError(
            f"Reference '{reference}' was not found in text '{text_slug}'."
        )

    start_unit = get_unit(session, label.start_unit_id)
    end_unit = get_unit(session, label.end_unit_id)
    scheme = session.get(ReferenceScheme, label.reference_scheme_id)
    if (
        start_unit is None
        or end_unit is None
        or scheme is None
        or scheme.text_id != text.id
        or start_unit.text_id != text.id
        or end_unit.text_id != text.id
        or start_unit.ordinal > end_unit.ordinal
    ):
        raise InvalidRequestError(
            f"Reference '{reference}' has an invalid canonical range."
        )

    return ResolvedReferenceRange(
        text=text,
        label=label,
        scheme=scheme,
        start_unit=start_unit,
        end_unit=end_unit,
        input=reference,
        normalized_input=normalized_reference,
    )


def get_reference_resolution(
    session: Session, text_slug: str, reference: str
) -> ReferenceResolution:
    resolved = resolve_reference_range(session, text_slug, reference)
    return ReferenceResolution(
        text_slug=resolved.text.slug,
        input=resolved.input,
        normalized_reference=resolved.normalized_input,
        label=resolved.label.label,
        reference_scheme=resolved.scheme.name,
        start=CanonicalRangeEndpoint(
            id=resolved.start_unit.id,
            key=resolved.start_unit.internal_key,
            ordinal=resolved.start_unit.ordinal,
        ),
        end=CanonicalRangeEndpoint(
            id=resolved.end_unit.id,
            key=resolved.end_unit.internal_key,
            ordinal=resolved.end_unit.ordinal,
        ),
    )
