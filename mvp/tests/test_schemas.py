import uuid

import pytest
from pydantic import ValidationError

from app.schemas import OfferCreate, RowIn, SintesiSaveRequest, VoceCreate


def test_offer_create_validates_name() -> None:
    with pytest.raises(ValidationError):
        OfferCreate(name="", segment_id=uuid.uuid4())


def test_row_defaults() -> None:
    row = RowIn(block="prezzo", local_id="r1", voce_id=uuid.uuid4())
    assert row.value == ""
    assert row.parent_local_id is None


def test_sintesi_payload() -> None:
    payload = SintesiSaveRequest(
        fixed={"servizi": "Fisso fonia e Internet"},
        rows=[RowIn(block="prezzo", local_id="r1", voce_id=uuid.uuid4())],
    )
    assert payload.fixed["servizi"].startswith("Fisso")


def test_voce_label_not_empty() -> None:
    with pytest.raises(ValidationError):
        VoceCreate(block_id=uuid.uuid4(), label="   ")
