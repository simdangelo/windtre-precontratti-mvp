import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import BulkStatus, BulkTargetKind, Outcome, enum_col


class BulkOperation(Base):
    __tablename__ = "bulk_operations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[BulkStatus] = mapped_column(
        enum_col(BulkStatus, "bulk_status"), default=BulkStatus.ANTEPRIMA
    )
    offers_selected_count: Mapped[int] = mapped_column(Integer, default=0)
    offers_changed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BulkOperationItem(Base):
    __tablename__ = "bulk_operation_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bulk_operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bulk_operations.id"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    target_kind: Mapped[BulkTargetKind] = mapped_column(
        enum_col(BulkTargetKind, "bulk_target_kind"), nullable=False
    )
    template_field_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("template_fields.id"), nullable=True
    )
    voce_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voci.id"), nullable=True)
    technology_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technologies.id"), nullable=True
    )
    new_value_text: Mapped[str] = mapped_column(String(500))


class BulkOperationTarget(Base):
    __tablename__ = "bulk_operation_targets"

    bulk_operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bulk_operations.id"), primary_key=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), primary_key=True)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offer_documents.id"))
    outcome: Mapped[Outcome] = mapped_column(enum_col(Outcome, "outcome"), nullable=False)
    changed_items: Mapped[int] = mapped_column(Integer, default=0)
    skipped_items: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
