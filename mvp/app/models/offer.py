import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import Category, OfferStatus, enum_col


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[Category] = mapped_column(enum_col(Category, "category"), nullable=False)
    segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("segments.id"))
    technology_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technologies.id"), nullable=True
    )
    status: Mapped[OfferStatus] = mapped_column(
        enum_col(OfferStatus, "offer_status"), nullable=False, default=OfferStatus.NUOVA
    )
    agcom_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
