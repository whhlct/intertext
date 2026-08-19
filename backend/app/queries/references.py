import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CanonicalUnit, ReferenceLabel, ReferenceScheme, Text


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


def get_unit(session: Session, unit_id: uuid.UUID) -> CanonicalUnit | None:
    return session.get(CanonicalUnit, unit_id)
