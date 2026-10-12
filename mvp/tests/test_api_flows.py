from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Voce


def _voce_id(db_session, label: str) -> str:
    voce = db_session.scalar(select(Voce).where(Voce.label == label))
    assert voce is not None
    return str(voce.id)


def test_full_lifecycle_via_api_only(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    # 1. Crea offerta (con Sintesi) via API
    created = client.post("/api/offers", json={
        "name": "Ciclo API",
        "segment_id": segment_id,
        "technology_id": technology_id,
        "fixed": {"servizi": "Fisso fonia e Internet"},
        "rows": [],
    })
    assert created.status_code == 201
    offer_id = created.json()["id"]

    # 2. Elenco
    listing = client.get("/api/offers")
    assert listing.status_code == 200
    assert any(item["id"] == offer_id for item in listing.json())

    # 3. Dettaglio iniziale
    detail = client.get(f"/api/offers/{offer_id}").json()
    assert detail["offer"]["name"] == "Ciclo API"
    assert detail["current_document"] is None
    assert detail["sintesi_stale"] is False
    assert detail["sintesi"]["technology_id"] == technology_id

    # 4. Salva Sintesi (anagrafica + campi + righe)
    voce_id = _voce_id(db_session, "Costo mensile")
    saved = client.put(f"/api/offers/{offer_id}/sintesi", json={
        "fixed": {"servizi": "Aggiornato"},
        "rows": [{"block": "prezzo", "local_id": "p1", "voce_id": voce_id,
                  "value": "19,99 euro/mese"}],
        "name": "Ciclo API",
        "status": "aperta",
        "agcom_code": "AG-1",
    })
    assert saved.status_code == 200

    # 5. Genera DOCX
    generated = client.post(f"/api/offers/{offer_id}/generate")
    assert generated.status_code == 201
    document_id = generated.json()["document_id"]

    # 6. Dettaglio con documento corrente e URL
    detail = client.get(f"/api/offers/{offer_id}").json()
    assert detail["current_document"]["id"] == document_id
    assert detail["current_document"]["is_current"] is True
    assert detail["current_document"]["download_url"] == (
        f"/api/documents/{document_id}/download"
    )
    assert detail["sintesi_stale"] is False
    assert detail["sintesi"]["status"] == "aperta"

    # 7. Download
    downloaded = client.get(f"/api/documents/{document_id}/download")
    assert downloaded.status_code == 200
    assert downloaded.content[:2] == b"PK"

    # 8. Duplica
    duplicated = client.post(
        f"/api/offers/{offer_id}/duplicate", json={"name": "Ciclo API bis"}
    )
    assert duplicated.status_code == 201
    duplicate_id = duplicated.json()["id"]

    # 9. Massiva: anteprima e applica su entrambe
    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id, duplicate_id],
        "items": [{"target_kind": "template_field",
                   "template_field_key": "servizi", "new_value": "Massiva"}],
    })
    assert preview.status_code == 200
    operation_id = preview.json()["operation_id"]
    applied = client.post(f"/api/bulk/{operation_id}/apply")
    assert applied.status_code == 200

    updated = client.get(f"/api/offers/{offer_id}").json()
    servizi = next(
        field for field in updated["sintesi"]["fixed_fields"]
        if field["key"] == "servizi"
    )
    assert servizi["value"] == "Massiva"

    # 10. Elimina e verifica 404
    assert client.delete(f"/api/offers/{offer_id}").status_code == 204
    assert client.get(f"/api/offers/{offer_id}").status_code == 404
