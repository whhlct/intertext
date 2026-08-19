"""add token and gloss enrichment tables

Revision ID: b17d2c91e4af
Revises: d49034f5c5da
Create Date: 2026-08-18 23:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b17d2c91e4af"
down_revision: str | None = "d49034f5c5da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_document = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
    )
    op.create_table(
        "enrichment_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_version_release_id", sa.Uuid(), nullable=False),
        sa.Column("enrichment_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_revision", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", json_document, nullable=False),
        sa.ForeignKeyConstraint(
            ["target_version_release_id"],
            ["version_releases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_version_release_id",
            "enrichment_type",
            "source_sha256",
        ),
    )
    op.create_index(
        op.f("ix_enrichment_imports_target_version_release_id"),
        "enrichment_imports",
        ["target_version_release_id"],
    )
    op.create_table(
        "lexemes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("language_id", sa.Uuid(), nullable=False),
        sa.Column("lemma", sa.Text(), nullable=False),
        sa.Column("normalized_lemma", sa.Text(), nullable=True),
        sa.Column("transliteration", sa.Text(), nullable=True),
        sa.Column("part_of_speech", sa.String(length=100), nullable=True),
        sa.Column("metadata", json_document, nullable=False),
        sa.ForeignKeyConstraint(
            ["language_id"], ["languages.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("language_id", "lemma"),
    )
    op.create_index(op.f("ix_lexemes_language_id"), "lexemes", ["language_id"])
    op.create_table(
        "tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("token_index", sa.Integer(), nullable=False),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("normalized", sa.Text(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("language_id", sa.Uuid(), nullable=False),
        sa.Column("lexeme_id", sa.Uuid(), nullable=True),
        sa.Column("is_word", sa.Boolean(), nullable=False),
        sa.Column("is_punctuation", sa.Boolean(), nullable=False),
        sa.Column("metadata", json_document, nullable=False),
        sa.ForeignKeyConstraint(
            ["language_id"], ["languages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lexeme_id"], ["lexemes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["segment_id"], ["version_segments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("segment_id", "token_index"),
    )
    op.create_index(op.f("ix_tokens_segment_id"), "tokens", ["segment_id"])
    op.create_index(
        "ix_tokens_segment_word_index",
        "tokens",
        ["segment_id", "is_word", "token_index"],
    )
    op.create_table(
        "token_glosses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("target_language_id", sa.Uuid(), nullable=False),
        sa.Column("enrichment_import_id", sa.Uuid(), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=False),
        sa.Column("gloss_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("metadata", json_document, nullable=False),
        sa.ForeignKeyConstraint(
            ["enrichment_import_id"],
            ["enrichment_imports.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_language_id"], ["languages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["token_id"], ["tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_id",
            "target_language_id",
            "gloss_type",
            "source",
            "enrichment_import_id",
        ),
    )
    op.create_index(
        op.f("ix_token_glosses_enrichment_import_id"),
        "token_glosses",
        ["enrichment_import_id"],
    )
    op.create_index(
        op.f("ix_token_glosses_token_id"), "token_glosses", ["token_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_token_glosses_token_id"), table_name="token_glosses")
    op.drop_index(
        op.f("ix_token_glosses_enrichment_import_id"),
        table_name="token_glosses",
    )
    op.drop_table("token_glosses")
    op.drop_index("ix_tokens_segment_word_index", table_name="tokens")
    op.drop_index(op.f("ix_tokens_segment_id"), table_name="tokens")
    op.drop_table("tokens")
    op.drop_index(op.f("ix_lexemes_language_id"), table_name="lexemes")
    op.drop_table("lexemes")
    op.drop_index(
        op.f("ix_enrichment_imports_target_version_release_id"),
        table_name="enrichment_imports",
    )
    op.drop_table("enrichment_imports")
