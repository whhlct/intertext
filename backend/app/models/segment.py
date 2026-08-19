import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONDocument
from app.models.common import MetadataMixin


class VersionSegment(Base, MetadataMixin):
    __tablename__ = "version_segments"
    __table_args__ = (UniqueConstraint("version_release_id", "sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_release_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("version_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("languages.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text_plain: Mapped[str] = mapped_column(Text, nullable=False)
    content_markup: Mapped[dict[str, Any]] = mapped_column(
        JSONDocument, default=dict, nullable=False
    )
    block_type: Mapped[str | None] = mapped_column(String(100))
    source_identifier: Mapped[str | None] = mapped_column(String(255))


class SegmentUnitMapping(Base, MetadataMixin):
    __tablename__ = "segment_unit_mappings"
    __table_args__ = (
        UniqueConstraint("segment_id", "canonical_unit_id", "sequence"),
        Index("ix_segment_unit_mappings_unit_sequence", "canonical_unit_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("version_segments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mapping_type: Mapped[str] = mapped_column(String(100), nullable=False, default="direct")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    source: Mapped[str | None] = mapped_column(String(255))
