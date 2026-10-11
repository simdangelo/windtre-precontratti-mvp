import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_templates.id"))
    file_type: Mapped[str] = mapped_column(String(16), default="docx")
    file_path: Mapped[str] = mapped_column(String(500))
    is_current: Mapped[bool] = mapped_column(default=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
