import uuid

from pydantic import BaseModel, Field, field_validator


class VoceCreate(BaseModel):
    block_id: uuid.UUID
    label: str = Field(min_length=1, max_length=200)

    @field_validator("label")
    @classmethod
    def strip_and_check(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label vuota")
        return value
