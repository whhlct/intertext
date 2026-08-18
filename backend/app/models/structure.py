import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin


class StructureNode(Base, MetadataMixin):
    __tablename__ = "structure_nodes"
    __table_args__ = (
        UniqueConstraint("text_id", "parent_id", "ordinal"),
        Index("ix_structure_nodes_text_id_start_end", "text_id", "start_unit_ordinal", "end_unit_ordinal"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("texts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("structure_nodes.id", ondelete="CASCADE"), index=True
    )
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(100))
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str | None] = mapped_column(String(1000))
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    start_unit_ordinal: Mapped[int | None] = mapped_column(Integer)
    end_unit_ordinal: Mapped[int | None] = mapped_column(Integer)


class CanonicalUnit(Base, MetadataMixin):
    __tablename__ = "canonical_units"
    __table_args__ = (
        UniqueConstraint("text_id", "ordinal"),
        UniqueConstraint("text_id", "internal_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("texts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_key: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(100), nullable=False)

