import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import DocType, enum_col


class OfferDocument(Base):
    __tablename__ = "offer_documents"
    __table_args__ = (
        UniqueConstraint("offer_id", "doc_type", name="uq_offer_document_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), index=True)
    doc_type: Mapped[DocType] = mapped_column(enum_col(DocType, "doc_type"), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_templates.id"))
    status: Mapped[str] = mapped_column(String(32), default="bozza")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
