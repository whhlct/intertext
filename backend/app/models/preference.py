import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin


class PreferredVersion(Base, MetadataMixin):
    __tablename__ = "preferred_versions"
    __table_args__ = (
        UniqueConstraint("text_id", "start_unit_id", "end_unit_id", "role", "priority"),
        Index("ix_preferred_versions_text_role_range", "text_id", "role", "start_unit_id", "end_unit_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("texts.id", ondelete="CASCADE"), nullable=False
    )
    start_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_units.id", ondelete="CASCADE"), nullable=False
    )
    end_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_units.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("text_versions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
