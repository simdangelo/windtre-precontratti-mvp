import uuid

from pydantic import BaseModel, Field

from app.models import OfferStatus


class RowIn(BaseModel):
    block: str = Field(min_length=1, max_length=50)
    local_id: str = Field(min_length=1, max_length=36)
    parent_local_id: str | None = None
    voce_id: uuid.UUID
    value: str = Field(default="", max_length=500)


class SintesiSaveRequest(BaseModel):
    fixed: dict[str, str] = Field(default_factory=dict)
    rows: list[RowIn] = Field(default_factory=list)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    technology_id: uuid.UUID | None = None
    status: OfferStatus | None = None
    agcom_code: str = Field(default="", max_length=50)


class FixedFieldRead(BaseModel):
    key: str
    label: str
    value: str
    source_kind: str
    is_required: bool
    block_code: str
    block_title: str


class DerivedFieldRead(BaseModel):
    key: str
    label: str
    value: str


class VoceBrief(BaseModel):
    id: str
    label: str


class BlockRead(BaseModel):
    id: str
    code: str
    title: str
    layout: str
    voci: list[VoceBrief]


class RowRead(BaseModel):
    id: str
    block: str
    parent_row_id: str | None
    voce_id: str
    voce_label: str
    value: str
    sort_order: int


class SintesiDataRead(BaseModel):
    offer_id: str | None
    offer_name: str
    technology_id: str | None
    status: str | None
    agcom_code: str | None
    fixed_fields: list[FixedFieldRead]
    derived_fields: list[DerivedFieldRead]
    blocks: list[BlockRead]
    rows: list[RowRead]
