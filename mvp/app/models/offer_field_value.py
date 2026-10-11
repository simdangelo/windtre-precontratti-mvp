import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OfferFieldValue(Base):
    __tablename__ = "offer_field_values"

    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), primary_key=True
    )
    template_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_fields.id"), primary_key=True
    )
    value_text: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
