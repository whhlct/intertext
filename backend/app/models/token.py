import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import MetadataMixin


class EnrichmentImport(Base, MetadataMixin):
    __tablename__ = "enrichment_imports"
    __table_args__ = (
        UniqueConstraint(
            "target_version_release_id",
            "enrichment_type",
            "source_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    target_version_release_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("version_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrichment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_revision: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Lexeme(Base, MetadataMixin):
    __tablename__ = "lexemes"
    __table_args__ = (UniqueConstraint("language_id", "lemma"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    language_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("languages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lemma: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_lemma: Mapped[str | None] = mapped_column(Text)
    transliteration: Mapped[str | None] = mapped_column(Text)
    part_of_speech: Mapped[str | None] = mapped_column(String(100))


class Token(Base, MetadataMixin):
    __tablename__ = "tokens"
    __table_args__ = (
        UniqueConstraint("segment_id", "token_index"),
        Index("ix_tokens_segment_word_index", "segment_id", "is_word", "token_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("version_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_index: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[str | None] = mapped_column(Text)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    language_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("languages.id", ondelete="RESTRICT"), nullable=False
    )
    lexeme_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lexemes.id", ondelete="SET NULL")
    )
    lexeme: Mapped[Lexeme | None] = relationship()
    is_word: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_punctuation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class TokenGloss(Base, MetadataMixin):
    __tablename__ = "token_glosses"
    __table_args__ = (
        UniqueConstraint(
            "token_id",
            "target_language_id",
            "gloss_type",
            "source",
            "enrichment_import_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_language_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("languages.id", ondelete="RESTRICT"), nullable=False
    )
    enrichment_import_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("enrichment_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gloss: Mapped[str] = mapped_column(Text, nullable=False)
    gloss_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
