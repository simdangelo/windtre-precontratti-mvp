import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Category, OfferStatus
from app.schemas.sintesi import RowIn, SintesiDataRead


class OfferCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    segment_id: uuid.UUID
    technology_id: uuid.UUID | None = None
    category: Category = Category.FISSE
    status: OfferStatus = OfferStatus.NUOVA
    agcom_code: str = Field(default="", max_length=50)


class OfferCreateFull(OfferCreate):
    fixed: dict[str, str] = Field(default_factory=dict)
    rows: list[RowIn] = Field(default_factory=list)


class OfferDuplicateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    segment_id: uuid.UUID
    technology_id: uuid.UUID | None
    status: OfferStatus
    agcom_code: str | None
    updated_at: datetime


class SegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class TechnologyRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    max_download_mbps: int
    max_upload_mbps: int
    badge_url: str | None


class TechnologyBrief(BaseModel):
    id: uuid.UUID
    name: str
    badge_url: str | None


class OfferSummary(BaseModel):
    id: uuid.UUID
    name: str
    category: Category
    status: OfferStatus
    agcom_code: str | None
    updated_at: datetime


class OfferOverviewRead(BaseModel):
    id: uuid.UUID
    name: str
    category: Category
    status: OfferStatus
    agcom_code: str | None
    has_sintesi: bool
    technology: TechnologyBrief | None
    updated_at: datetime


class GeneratedDocumentRead(BaseModel):
    id: uuid.UUID
    file_name: str
    generated_at: datetime
    is_current: bool
    download_url: str


class OfferDocumentRead(BaseModel):
    id: uuid.UUID
    offer_id: uuid.UUID
    doc_type: str
    status: str
    updated_at: datetime


class OfferDetailRead(BaseModel):
    offer: OfferSummary
    segment_name: str
    sintesi: SintesiDataRead
    current_document: GeneratedDocumentRead | None
    previous_documents: list[GeneratedDocumentRead]
    sintesi_stale: bool
