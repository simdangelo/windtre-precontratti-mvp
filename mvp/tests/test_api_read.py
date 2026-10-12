import json
import re
import uuid

from fastapi.testclient import TestClient

from app.models import Technology
from app.schemas import SintesiDataRead
from app.services import sintesi as sintesi_service
from tests.conftest import create_offer, create_offer_only


def test_sintesi_data_read_mirrors_json_keys(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Schema Mirror", segment_id, technology_id)
    data = sintesi_service.get_sintesi_data(db_session, uuid.UUID(offer_id))
    payload = sintesi_service.sintesi_to_json(data)

    read = SintesiDataRead.model_validate(payload)

    assert set(read.model_dump().keys()) == set(payload.keys())
    assert set(read.fixed_fields[0].model_dump().keys()) == set(
        payload["fixed_fields"][0].keys()
    )
    assert set(read.blocks[0].model_dump().keys()) == set(payload["blocks"][0].keys())
    assert set(read.blocks[0].voci[0].model_dump().keys()) == set(
        payload["blocks"][0]["voci"][0].keys()
    )


def test_api_list_offers(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Api Lista", segment_id, technology_id)

    response = client.get("/api/offers")

    assert response.status_code == 200
    body = response.json()
    entry = next(item for item in body if item["id"] == offer_id)
    assert entry["name"] == "Api Lista"
    assert entry["category"] == "fisse"
    assert entry["status"] == "nuova"
    assert entry["has_sintesi"] is True
    assert entry["technology"]["id"] == technology_id
    assert entry["technology"]["name"]
    assert entry["technology"]["badge_url"] == f"/api/technologies/{technology_id}/badge"
    assert entry["updated_at"]


def _embedded_sintesi_json(client: TestClient, offer_id: str) -> dict:
    html = client.get(f"/offers/{offer_id}").text
    match = re.search(
        r'<script type="application/json" id="sintesi-json">(.*?)</script>',
        html,
        re.S,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_api_offer_detail(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Api Dettaglio", segment_id, technology_id)

    response = client.get(f"/api/offers/{offer_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["offer"]["id"] == offer_id
    assert body["offer"]["name"] == "Api Dettaglio"
    assert body["segment_name"]
    assert body["current_document"] is None
    assert body["previous_documents"] == []
    assert body["sintesi_stale"] is False
    assert body["sintesi"]["technology_id"] == technology_id


def test_api_offer_detail_sintesi_keys_match_embedded_json(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Api Anti Drift", segment_id, technology_id)

    api_body = client.get(f"/api/offers/{offer_id}").json()
    embedded = _embedded_sintesi_json(client, offer_id)

    assert set(api_body["sintesi"].keys()) == set(embedded.keys())


def test_api_offer_detail_unknown_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/offers/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_api_sintesi_template(client: TestClient) -> None:
    response = client.get("/api/sintesi/template")

    assert response.status_code == 200
    body = response.json()
    assert body["offer_id"] is None
    assert body["offer_name"] == ""
    assert body["rows"] == []
    assert len(body["fixed_fields"]) > 0
    assert len(body["blocks"]) > 0
    assert all(block["voci"] for block in body["blocks"])


def test_api_technologies(client: TestClient, technology_id: str) -> None:
    response = client.get("/api/technologies")

    assert response.status_code == 200
    body = response.json()
    tech = next(item for item in body if item["id"] == technology_id)
    assert tech["code"] == "FWA"
    assert tech["name"]
    assert isinstance(tech["max_download_mbps"], int)
    assert isinstance(tech["max_upload_mbps"], int)
    assert tech["badge_url"] == f"/api/technologies/{technology_id}/badge"


def test_api_segments(client: TestClient, segment_id: str) -> None:
    response = client.get("/api/segments")

    assert response.status_code == 200
    body = response.json()
    segment = next(item for item in body if item["id"] == segment_id)
    assert segment["code"] == "W3_FIX_CB_CNS"
    assert segment["name"]


def test_api_technology_badge(client: TestClient, technology_id: str) -> None:
    response = client.get(f"/api/technologies/{technology_id}/badge")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_api_technology_badge_unknown_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/technologies/{uuid.uuid4()}/badge")
    assert response.status_code == 404


def test_api_technology_without_badge(
    client: TestClient, db_session, technology_id: str
) -> None:
    technology = Technology(code="NO_BADGE_API", name="Senza bollino API",
                            badge_path=None, max_download_mbps=1, max_upload_mbps=1)
    db_session.add(technology)
    db_session.commit()

    listing = client.get("/api/technologies").json()
    entry = next(item for item in listing if item["id"] == str(technology.id))
    assert entry["badge_url"] is None

    assert client.get(f"/api/technologies/{technology.id}/badge").status_code == 404


def test_api_document_download(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Api Download", segment_id, technology_id)
    generated = client.post(f"/api/offers/{offer_id}/generate")
    assert generated.status_code == 201
    document_id = generated.json()["document_id"]

    response = client.get(f"/api/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.content[:2] == b"PK"


def test_api_document_download_unknown_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/documents/{uuid.uuid4()}/download")
    assert response.status_code == 404


def test_api_create_sintesi_document(
    client: TestClient, db_session, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer_only(client, "Api Crea Sintesi", segment_id, technology_id)

    first = client.post(f"/api/offers/{offer_id}/sintesi")
    assert first.status_code == 201
    assert first.json()["offer_id"] == offer_id
    assert first.json()["doc_type"] == "sintesi"

    second = client.post(f"/api/offers/{offer_id}/sintesi")
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_api_create_sintesi_unknown_offer_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/offers/{uuid.uuid4()}/sintesi")
    assert response.status_code == 404


def test_openapi_schema_exposes_only_api_paths(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    paths = list(schema["paths"].keys())
    assert paths
    assert all(path.startswith("/api") for path in paths)
    assert "/openapi.json" not in paths
