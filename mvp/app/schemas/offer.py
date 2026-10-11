import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Category, OfferStatus
from app.schemas.sintesi import RowIn


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
