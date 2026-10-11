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
