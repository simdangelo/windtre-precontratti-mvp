import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    GeneratedDocument,
    Offer,
    OfferDocument,
    OfferFieldValue,
    OfferRow,
    OfferStatus,
    Voce,
)
from tests.conftest import create_offer, create_offer_only


def test_duplicate_offer_copies_sintesi(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    source_id = create_offer(client, "Offerta Sorgente", segment_id, technology_id)
    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    figlio = db_session.scalar(select(Voce).where(Voce.label == "Per i già clienti"))
    assert voce is not None
    assert figlio is not None
    saved = client.put(f"/api/offers/{source_id}/sintesi", json={
        "fixed": {"disponibilita": "01-01-2026"},
        "rows": [
            {"block": "prezzo", "local_id": "p1", "voce_id": str(voce.id), "value": ""},
            {"block": "prezzo", "local_id": "p2", "parent_local_id": "p1",
             "voce_id": str(figlio.id), "value": "10 euro"},
        ],
        "status": "chiusa", "agcom_code": "COD9",
    })
    assert saved.status_code == 200
    generated = client.post(f"/api/offers/{source_id}/generate")
    assert generated.status_code == 201

    response = client.post(f"/api/offers/{source_id}/duplicate",
                           json={"name": "Offerta Copia"})
    assert response.status_code == 201
    assert response.json()["name"] == "Offerta Copia"
    new_id = response.json()["id"]

    db_session.expire_all()
    source = db_session.get(Offer, uuid.UUID(source_id))
    copy = db_session.get(Offer, uuid.UUID(new_id))
    assert source is not None
    assert copy is not None
    assert copy.status == OfferStatus.NUOVA
    assert copy.agcom_code is None
    assert copy.segment_id == source.segment_id
    assert copy.technology_id == source.technology_id

    new_doc = db_session.scalar(
        select(OfferDocument).where(OfferDocument.offer_id == copy.id)
    )
    assert new_doc is not None
    values = list(db_session.scalars(
        select(OfferFieldValue).where(
            OfferFieldValue.offer_document_id == new_doc.id
        )
    ).all())
    assert [value.value_text for value in values] == ["01-01-2026"]

    rows = list(db_session.scalars(
        select(OfferRow).where(OfferRow.offer_document_id == new_doc.id)
    ).all())
    assert len(rows) == 2
    parent = next(row for row in rows if row.parent_row_id is None)
    child = next(row for row in rows if row.parent_row_id is not None)
    assert child.parent_row_id == parent.id
    assert child.value_text == "10 euro"

    assert db_session.scalar(
        select(GeneratedDocument).where(
            GeneratedDocument.offer_document_id == new_doc.id
        )
    ) is None


def test_duplicate_name_conflict(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    source_id = create_offer(client, "Offerta Alfa", segment_id, technology_id)
    create_offer(client, "Offerta Beta", segment_id, technology_id)
    response = client.post(f"/api/offers/{source_id}/duplicate",
                           json={"name": "Offerta Beta"})
    assert response.status_code == 422
    assert "esiste già" in response.json()["detail"]
    case = client.post(f"/api/offers/{source_id}/duplicate",
                       json={"name": "  OFFERTA BETA "})
    assert case.status_code == 422


def test_duplicate_missing_offer_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/offers/00000000-0000-0000-0000-000000000000/duplicate",
        json={"name": "Copia"},
    )
    assert response.status_code == 404


def test_duplicate_without_sintesi_has_no_document(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    source_id = create_offer_only(
        client, "Offerta Senza Documento", segment_id, technology_id
    )
    response = client.post(f"/api/offers/{source_id}/duplicate",
                           json={"name": "Copia Senza Documento"})
    assert response.status_code == 201
    db_session.expire_all()
    copy = db_session.get(Offer, uuid.UUID(response.json()["id"]))
    assert copy is not None
    assert db_session.scalar(
        select(OfferDocument).where(OfferDocument.offer_id == copy.id)
    ) is None
