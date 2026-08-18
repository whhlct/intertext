import uuid

from sqlalchemy import ForeignKey, String, Text as SQLText, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin, TimestampMixin


class Text(Base, MetadataMixin, TimestampMixin):
    __tablename__ = "texts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(SQLText)
    default_reference_scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "reference_schemes.id",
            name="fk_texts_default_reference_scheme_id_reference_schemes",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )

