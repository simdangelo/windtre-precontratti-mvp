import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import BlockKind, Layout, enum_col


class TemplateBlock(Base):
    __tablename__ = "template_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_templates.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[BlockKind] = mapped_column(enum_col(BlockKind, "block_kind"), nullable=False)
    layout: Mapped[Layout | None] = mapped_column(enum_col(Layout, "layout", 16), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer)
