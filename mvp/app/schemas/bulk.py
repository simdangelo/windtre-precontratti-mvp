import uuid

from pydantic import BaseModel, Field, model_validator

from app.models import BulkTargetKind


class BulkItemIn(BaseModel):
    target_kind: BulkTargetKind
    template_field_key: str | None = None
    voce_id: uuid.UUID | None = None
    technology_id: uuid.UUID | None = None
    new_value: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_target(self) -> "BulkItemIn":
        if self.target_kind == BulkTargetKind.TEMPLATE_FIELD:
            if not self.template_field_key:
                raise ValueError("template_field_key obbligatorio per i campi fissi")
            if not self.new_value.strip():
                raise ValueError("new_value obbligatorio per i campi fissi")
        if self.target_kind == BulkTargetKind.VOCE:
            if self.voce_id is None:
                raise ValueError("voce_id obbligatorio per le voci")
            if not self.new_value.strip():
                raise ValueError("new_value obbligatorio per le voci")
        if self.target_kind == BulkTargetKind.TECHNOLOGY and self.technology_id is None:
            raise ValueError("technology_id obbligatorio per la tecnologia")
        return self


class BulkRequest(BaseModel):
    offer_ids: list[uuid.UUID] = Field(min_length=1)
    items: list[BulkItemIn] = Field(min_length=1)


class BulkChangePreview(BaseModel):
    label: str
    kind: str
    old_value: str | None
    new_value: str
    outcome: str


class BulkTargetPreview(BaseModel):
    offer_id: uuid.UUID
    offer_name: str
    outcome: str
    changed_items: int
    skipped_items: int
    reason: str | None
    changes: list[BulkChangePreview]


class BulkPreviewResponse(BaseModel):
    operation_id: uuid.UUID
    counts: dict[str, int]
    targets: list[BulkTargetPreview]


class BulkApplyResponse(BaseModel):
    operation_id: uuid.UUID
    counts: dict[str, int]
