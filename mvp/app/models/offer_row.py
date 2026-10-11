import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OfferRow(Base):
    __tablename__ = "offer_rows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    parent_row_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_rows.id"), nullable=True
    )
    voce_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("voci.id"), index=True)
    value_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
