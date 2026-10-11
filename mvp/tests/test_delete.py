import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BulkOperation,
    BulkOperationTarget,
    GeneratedDocument,
    Offer,
    OfferDocument,
    OfferFieldValue,
    OfferRow,
    Voce,
)
from tests.conftest import create_offer


def test_delete_offer_removes_everything(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Da Eliminare", segment_id, technology_id)
    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    assert voce is not None
    saved = client.put(f"/api/offers/{offer_id}/sintesi", json={
        "fixed": {"disponibilita": "01-01-2026"},
        "rows": [{"block": "prezzo", "local_id": "p1",
                  "voce_id": str(voce.id), "value": "5"}],
    })
    assert saved.status_code == 200
    generated = client.post(f"/api/offers/{offer_id}/generate")
    assert generated.status_code == 201
    file_path = generated.json()["file_path"]
    assert Path(file_path).is_file()

    deleted = client.delete(f"/api/offers/{offer_id}")
    assert deleted.status_code == 204

    db_session.expire_all()
    offer_uuid = uuid.UUID(offer_id)
    assert db_session.get(Offer, offer_uuid) is None
    assert list(db_session.scalars(select(OfferDocument)).all()) == []
    assert list(db_session.scalars(select(OfferRow)).all()) == []
    assert list(db_session.scalars(select(OfferFieldValue)).all()) == []
    assert list(db_session.scalars(select(GeneratedDocument)).all()) == []
    assert not Path(file_path).exists()


def test_delete_offer_frees_name(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Riciclabile", segment_id, technology_id)
    assert client.delete(f"/api/offers/{offer_id}").status_code == 204
    again = create_offer(client, "Offerta Riciclabile", segment_id, technology_id)
    assert again != offer_id


def test_delete_missing_offer_returns_404(client: TestClient) -> None:
    response = client.delete("/api/offers/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_removes_bulk_targets(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta In Massiva", segment_id, technology_id)
    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    assert voce is not None
    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "voce", "voce_id": str(voce.id),
                   "new_value": "9 euro"}],
    })
    assert preview.status_code == 200
    operation_id = uuid.UUID(preview.json()["operation_id"])

    assert client.delete(f"/api/offers/{offer_id}").status_code == 204

    db_session.expire_all()
    assert db_session.get(BulkOperation, operation_id) is not None
    targets = list(db_session.scalars(
        select(BulkOperationTarget).where(
            BulkOperationTarget.bulk_operation_id == operation_id
        )
    ).all())
    assert targets == []
