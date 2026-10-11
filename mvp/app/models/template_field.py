import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import SourceKind, enum_col


class TemplateField(Base):
    __tablename__ = "template_fields"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(200))
    source_kind: Mapped[SourceKind] = mapped_column(
        enum_col(SourceKind, "source_kind"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)
