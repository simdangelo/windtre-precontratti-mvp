from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import TemplateBlock


def _block(db_session, code: str):
    return db_session.scalar(select(TemplateBlock).where(TemplateBlock.code == code))


def _prezzo_block(db_session):
    return _block(db_session, "prezzo")


def _costi_block(db_session):
    return _block(db_session, "costi")


def test_create_voce(client: TestClient, db_session) -> None:
    response = client.post("/api/voci",
                           json={"block_id": str(_prezzo_block(db_session).id),
                                 "label": "Costo eSIM"})
    assert response.status_code == 201
    assert response.json()["label"] == "Costo eSIM"
    assert response.json()["code"] == "costo_esim"


def test_duplicate_voce_is_rejected(client: TestClient, db_session) -> None:
    block_id = str(_prezzo_block(db_session).id)
    first = client.post("/api/voci", json={"block_id": block_id, "label": "Costo rete"})
    second = client.post("/api/voci", json={"block_id": block_id, "label": "Costo rete"})
    assert first.status_code == 201
    assert second.status_code == 422
    assert "esiste già" in second.json()["detail"]


def test_duplicate_voce_is_case_insensitive(client: TestClient, db_session) -> None:
    block_id = str(_prezzo_block(db_session).id)
    first = client.post("/api/voci", json={"block_id": block_id, "label": "Rata Fibra"})
    assert first.status_code == 201
    for label in ("RATA FIBRA", "rata fibra", "  Rata Fibra  "):
        response = client.post("/api/voci", json={"block_id": block_id, "label": label})
        assert response.status_code == 422, label
        assert "esiste già" in response.json()["detail"]


def test_duplicate_against_seed_voce(client: TestClient, db_session) -> None:
    block_id = str(_costi_block(db_session).id)
    response = client.post("/api/voci", json={"block_id": block_id, "label": "MODEM"})
    assert response.status_code == 422
    assert "Modem" in response.json()["detail"]


def test_same_label_allowed_in_other_block(client: TestClient, db_session) -> None:
    prezzo_id = str(_prezzo_block(db_session).id)
    costi_id = str(_costi_block(db_session).id)
    duplicate = client.post("/api/voci",
                            json={"block_id": prezzo_id, "label": "Costo mensile"})
    assert duplicate.status_code == 422
    other_block = client.post("/api/voci",
                              json={"block_id": costi_id, "label": "Costo mensile"})
    assert other_block.status_code == 201
