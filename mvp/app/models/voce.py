import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Voce(Base):
    __tablename__ = "voci"
    __table_args__ = (
        UniqueConstraint("block_id", "code", name="uq_voce_block_code"),
        UniqueConstraint("block_id", "label", name="uq_voce_block_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
