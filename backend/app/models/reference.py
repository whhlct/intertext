import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin


class ReferenceScheme(Base, MetadataMixin):
    __tablename__ = "reference_schemes"
    __table_args__ = (UniqueConstraint("text_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("texts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class ReferenceLabel(Base, MetadataMixin):
    __tablename__ = "reference_labels"
    __table_args__ = (
        UniqueConstraint("reference_scheme_id", "normalized_label"),
        Index("ix_reference_labels_scheme_range", "reference_scheme_id", "start_unit_id", "end_unit_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reference_scheme_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reference_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_units.id", ondelete="CASCADE"), nullable=False
    )
    end_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_units.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

