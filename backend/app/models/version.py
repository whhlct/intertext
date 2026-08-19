import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin, TimestampMixin


class TextVersion(Base, MetadataMixin, TimestampMixin):
    __tablename__ = "text_versions"
    __table_args__ = (UniqueConstraint("text_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("texts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(50))
    default_language_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("languages.id", ondelete="RESTRICT"), nullable=False
    )
    reference_scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("reference_schemes.id", ondelete="SET NULL")
    )
    version_type: Mapped[str] = mapped_column(String(100), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    source_name: Mapped[str | None] = mapped_column(String(255))
    license: Mapped[str | None] = mapped_column(String(255))
    rights_statement: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)


class VersionRelease(Base, MetadataMixin):
    __tablename__ = "version_releases"
    __table_args__ = (
        UniqueConstraint("version_id", "version_label"),
        Index(
            "uq_version_releases_current_version",
            "version_id",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("text_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

