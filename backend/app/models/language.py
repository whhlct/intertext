import uuid

from sqlalchemy import CheckConstraint, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MetadataMixin


class Language(Base, MetadataMixin):
    __tablename__ = "languages"
    __table_args__ = (
        CheckConstraint("direction IN ('ltr', 'rtl')", name="direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    iso_code: Mapped[str] = mapped_column(String(35), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(255))
    script: Mapped[str | None] = mapped_column(String(100))
    direction: Mapped[str] = mapped_column(String(3), nullable=False, default="ltr")

