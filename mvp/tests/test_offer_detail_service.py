import uuid

from fastapi.testclient import TestClient

from app.services import detail as detail_service
from tests.conftest import create_offer


def test_get_offer_detail_composes_sintesi(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Detail Service", segment_id, technology_id)

    detail = detail_service.get_offer_detail(db_session, uuid.UUID(offer_id))

    assert detail.offer.name == "Detail Service"
    assert detail.segment_name
    assert detail.sintesi.offer_name == "Detail Service"
    assert detail.sintesi.technology_id is not None
    assert detail.sintesi_stale is False
    assert detail.current_document is None
    assert detail.previous_documents == []


def test_get_offer_detail_stale_after_save(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Detail Stale", segment_id, technology_id)
    assert client.post(f"/api/offers/{offer_id}/generate").status_code == 201

    detail = detail_service.get_offer_detail(db_session, uuid.UUID(offer_id))
    assert detail.current_document is not None
    assert detail.sintesi_stale is False

    assert client.put(
        f"/api/offers/{offer_id}/sintesi",
        json={"fixed": {"servizi": "Modificato"}, "rows": []},
    ).status_code == 200

    detail = detail_service.get_offer_detail(db_session, uuid.UUID(offer_id))
    assert detail.sintesi_stale is True
    assert detail.previous_documents == []
