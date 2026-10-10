from uuid import UUID, uuid4
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

# SQLAlchemy 2.0 ORM Imports
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Numeric, Date, DateTime, ForeignKey, JSON, Uuid

# Pydantic v2 Imports for Request/Response Schemas
from pydantic import BaseModel, Field, EmailStr, field_validator


# ============================================================================
# PART 1: SQLAlchemy 2.0 ORM Models
# Designed for Google Cloud Spanner (PostgreSQL Dialect) & Portable SQL Engine
# ============================================================================

class Base(DeclarativeBase):
    """Declarative Base class for all ORM entities."""
    pass


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    offers: Mapped[List["Offer"]] = relationship("Offer", back_populates="segment")
    user_roles: Mapped[List["UserSegmentRole"]] = relationship("UserSegmentRole", back_populates="segment")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    segment_roles: Mapped[List["UserSegmentRole"]] = relationship("UserSegmentRole", back_populates="user")
    actions: Mapped[List["OfferStateHistory"]] = relationship("OfferStateHistory", back_populates="actor")


class UserSegmentRole(Base):
    __tablename__ = "user_segment_roles"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    segment_id: Mapped[str] = mapped_column(String(50), ForeignKey("segments.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False) # 'editor', 'viewer', 'admin'

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="segment_roles")
    segment: Mapped["Segment"] = relationship("Segment", back_populates="user_roles")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    segment_id: Mapped[str] = mapped_column(String(50), ForeignKey("segments.id", ondelete="RESTRICT"), nullable=False)
    commercial_name: Mapped[str] = mapped_column(String(255), nullable=False)
    technology_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'FTTH', 'FTTC', 'FWA', '5G'
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    po_code: Mapped[Optional[str]] = mapped_column(String(50)) # Very Mobile unique key POXXXXXX
    current_agcom_code: Mapped[Optional[str]] = mapped_column(String(50)) # 10-char or 36-char (UUID) code from AGCOM
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NUOVA") # 'NUOVA', 'APERTA', 'CHIUSA'
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[Optional[date]] = mapped_column(Date)
    custom_filename_sintesi: Mapped[Optional[str]] = mapped_column(String(255)) # User defined filename for Sintesi document
    custom_filename_trasparenza: Mapped[Optional[str]] = mapped_column(String(255)) # User defined filename for Trasparenza document
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="credito_residuo") # 'credito_residuo' or 'abbonamento'
    activation_price_gia_clienti: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    activation_price_nuovi_nativi: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    activation_price_nuovi_portabilita: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    segment: Mapped["Segment"] = relationship("Segment", back_populates="offers")
    dynamic_tables: Mapped[List["DynamicTable"]] = relationship("DynamicTable", back_populates="offer", cascade="all, delete-orphan")
    history: Mapped[List["OfferStateHistory"]] = relationship("OfferStateHistory", back_populates="offer", cascade="all, delete-orphan")


class OfferStateHistory(Base):
    __tablename__ = "offer_state_history"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    agcom_code_used: Mapped[Optional[str]] = mapped_column(String(10))
    changed_by: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    docx_gcs_uri: Mapped[Optional[str]] = mapped_column(String(512))
    xlsx_gcs_uri: Mapped[Optional[str]] = mapped_column(String(512))
    sintesi_pdf_gcs_uri: Mapped[Optional[str]] = mapped_column(String(512))
    trasparenza_pdf_gcs_uri: Mapped[Optional[str]] = mapped_column(String(512))

    # Relationships
    offer: Mapped["Offer"] = relationship("Offer", back_populates="history")
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="actions")


class DynamicTable(Base):
    __tablename__ = "dynamic_tables"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    offer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    table_identifier: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'PREZZO', 'COSTI', 'SERVIZI'
    sequence_order: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    structural_content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False) # Maps to Cloud Spanner JSON data type
    note_links: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON) # Footnotes JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    offer: Mapped["Offer"] = relationship("Offer", back_populates="dynamic_tables")


class GlobalConfig(Base):
    __tablename__ = "global_configs"

    config_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    config_value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# PART 2: Pydantic v2 Schemas (FastAPI Validation & Serialization)
# ============================================================================

from typing import Literal

class ChildRowSchema(BaseModel):
    id: str = Field(..., description="Unique element subfield ID")
    type: Literal["figlio"] = Field("figlio", description="Field identifier type")
    label: str = Field(..., min_length=1, description="Subfield descriptive label")
    value: Optional[str] = Field(None, description="Compiled value string")


class ParentRowSchema(BaseModel):
    id: str = Field(..., description="Unique element field ID")
    type: Literal["padre"] = Field("padre", description="Field identifier type")
    label: str = Field(..., min_length=1, description="Field descriptive label")
    value: Optional[str] = Field(None, description="Direct value of parent (e.g. 'ND' or pricing)")
    children: List[ChildRowSchema] = Field(default_factory=list, description="Array of child subfields")


class DynamicTableContentSchema(BaseModel):
    max_rows_limit: int = Field(15, ge=1, le=50, description="Enforced maximum row boundary")
    rows: List[ParentRowSchema] = Field(..., description="Hierarchical Parent-Child rows")
    note_links: Optional[Dict[str, Any]] = Field(default=None, description="Footnotes or custom notes rich-text")

    @field_validator("rows")
    @classmethod
    def validate_total_rows_boundary(cls, rows: List[ParentRowSchema], info) -> List[ParentRowSchema]:
        # Count all rendered rows: every Padre + every non-omitted Figlio counts toward the layout capacity
        total_rendered_rows = 0
        for r in rows:
            if r.value and r.value != "":
                total_rendered_rows += 1
            for child in r.children:
                if child.value and child.value != "":
                    total_rendered_rows += 1
                    
        # Grab limit context if possible, or fallback
        limit = info.context.get("max_rows_limit", 15) if info.context else 15
        if total_rendered_rows > limit:
            raise ValueError(f"Le righe totali compilate ({total_rendered_rows}) superano il limite imposto di {limit} per questo segmento.")
        return rows


# Offer Base & Creation Schemas
class OfferBase(BaseModel):
    commercial_name: str = Field(..., min_length=2, max_length=255)
    technology_type: str = Field(..., description="FTTH, FTTC, FWA, 5G, or 4G")
    base_price: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2)
    po_code: Optional[str] = Field(None, pattern=r"^PO\d+$", description="Unique PO code for Very Mobile, e.g. PO123456")
    date_start: date
    date_end: Optional[date] = None
    custom_filename_sintesi: Optional[str] = Field(None, max_length=255, description="Custom filename for Sintesi")
    custom_filename_trasparenza: Optional[str] = Field(None, max_length=255, description="Custom filename for Trasparenza")
    payment_method: str = Field("credito_residuo", description="credito_residuo or abbonamento")
    activation_price_gia_clienti: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    activation_price_nuovi_nativi: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    activation_price_nuovi_portabilita: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    current_agcom_code: Optional[str] = Field(None, min_length=10, max_length=50, description="Valid 10-character alphanumeric code or 36-character UUID AGCOM code")

    @field_validator("current_agcom_code", mode="before")
    @classmethod
    def empty_agcom_to_none(cls, v):
        if v is not None and isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("date_end")
    @classmethod
    def validate_logical_dates(cls, date_end: Optional[date], info) -> Optional[date]:
        start = info.data.get("date_start")
        if start and date_end and date_end < start:
            raise ValueError("La data di fine sottoscrivibilità non può essere antecedente alla data di inizio.")
        return date_end


class OfferCreate(OfferBase):
    segment_id: str = Field(..., description="Ownership segment code")


class OfferUpdate(BaseModel):
    commercial_name: Optional[str] = None
    technology_type: Optional[str] = None
    base_price: Optional[Decimal] = None
    po_code: Optional[str] = None
    current_agcom_code: Optional[str] = Field(None, min_length=10, max_length=50, description="Valid 10-character alphanumeric code or 36-character UUID AGCOM code")
    status: Optional[str] = Field(None, pattern=r"^(NUOVA|APERTA|CHIUSA)$")
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    custom_filename_sintesi: Optional[str] = None
    custom_filename_trasparenza: Optional[str] = None
    payment_method: Optional[str] = None
    activation_price_gia_clienti: Optional[Decimal] = None
    activation_price_nuovi_nativi: Optional[Decimal] = None
    activation_price_nuovi_portabilita: Optional[Decimal] = None

    @field_validator("current_agcom_code", mode="before")
    @classmethod
    def empty_agcom_to_none(cls, v):
        if v is not None and isinstance(v, str) and not v.strip():
            return None
        return v


class OfferResponse(OfferBase):
    id: UUID
    segment_id: str
    current_agcom_code: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfferBulkUpdate(BaseModel):
    offer_ids: List[UUID] = Field(..., description="List of offer UUIDs to bulk-update")
    fields: OfferUpdate = Field(..., description="The fields to update on the selected offers")


class PlaceholderItem(BaseModel):
    key: str = Field(..., description="Nome univoco del segnaposto (es. base_price, nome_offerta)")
    description: str = Field(..., description="Descrizione del segnaposto e suo utilizzo")
    category: str = Field(..., description="Categoria logica (es. Prezzi, Offerta, Tecnico, Regolatorio, Note)")


class OfferDuplicateRequest(BaseModel):
    commercial_name: Optional[str] = Field(None, description="Nuovo nome commerciale dell'offerta (default: '{nome offerta} Copia')")
    target_status: Optional[str] = Field("NUOVA", pattern=r"^(NUOVA|APERTA|CHIUSA)$", description="Stato iniziale dell'offerta duplicata (default: 'NUOVA' / draft)")


