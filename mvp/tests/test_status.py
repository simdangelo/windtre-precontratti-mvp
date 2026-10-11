import json
import re
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Offer, OfferStatus, Technology
from tests.conftest import create_offer


def _offer(db: Session, offer_id: str) -> Offer:
    offer = db.get(Offer, uuid.UUID(offer_id))
    assert offer is not None
    return offer


def _put(client: TestClient, offer_id: str, payload: dict[str, object]):
    return client.put(f"/api/offers/{offer_id}/sintesi", json=payload)


def test_new_offer_is_nuova(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Stato Nuova", segment_id, technology_id)
    offer = _offer(db_session, offer_id)
    assert offer.status == OfferStatus.NUOVA
    assert offer.agcom_code is None


def test_create_offer_accepts_status_and_code(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    response = client.post("/api/offers", json={
        "name": "Offerta Creata Aperta", "segment_id": segment_id,
        "technology_id": technology_id, "status": "aperta", "agcom_code": "COD001",
        "fixed": {}, "rows": [],
    })
    assert response.status_code == 201
    offer = _offer(db_session, response.json()["id"])
    assert offer.status == OfferStatus.APERTA
    assert offer.agcom_code == "COD001"


def test_status_and_code_are_free_on_save(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Stati Liberi", segment_id, technology_id)
    # APERTA senza codice: consentita
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "aperta",
                            "agcom_code": ""})
    assert _offer(db_session, offer_id).status == OfferStatus.APERTA
    # NUOVA con codice: consentita (nessuna derivazione)
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "nuova",
                            "agcom_code": "COD002"})
    offer = _offer(db_session, offer_id)
    assert offer.status == OfferStatus.NUOVA
    assert offer.agcom_code == "COD002"


def test_chiusa_and_reopen_are_manual(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Chiusa", segment_id, technology_id)
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "chiusa",
                            "agcom_code": "COD777"})
    offer = _offer(db_session, offer_id)
    assert offer.status == OfferStatus.CHIUSA
    assert offer.agcom_code == "COD777"
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "aperta"})
    assert _offer(db_session, offer_id).status == OfferStatus.APERTA


def test_code_can_be_cleared_without_changing_status(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Codice Rimosso", segment_id, technology_id)
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "aperta",
                            "agcom_code": "COD999"})
    response = _put(client, offer_id, {"fixed": {}, "rows": [], "agcom_code": ""})
    assert response.status_code == 200
    offer = _offer(db_session, offer_id)
    assert offer.status == OfferStatus.APERTA
    assert offer.agcom_code is None


def test_agcom_code_too_long_is_rejected(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Codice Lungo", segment_id, technology_id)
    response = _put(client, offer_id, {"fixed": {}, "rows": [], "agcom_code": "X" * 51})
    assert response.status_code == 422


def test_technology_is_editable(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Tecnologia", segment_id, technology_id)
    fttc = db_session.scalar(select(Technology).where(Technology.code == "FTTC"))
    assert fttc is not None
    response = _put(client, offer_id, {"fixed": {}, "rows": [],
                                       "technology_id": str(fttc.id)})
    assert response.status_code == 200
    assert _offer(db_session, offer_id).technology_id == fttc.id
    page = client.get(f"/offers/{offer_id}")
    match = re.search(r'<script[^>]*id="sintesi-json"[^>]*>(.*?)</script>',
                      page.text, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    values = {f["key"]: f["value"] for f in data["fixed_fields"]}
    assert values["velocita_download"] == "200,00 Mbps in Download"


def test_unknown_technology_is_rejected(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Tecnologia Ignota", segment_id, technology_id)
    response = _put(client, offer_id, {"fixed": {}, "rows": [],
                                       "technology_id": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code == 404


def test_editor_json_exposes_status_and_code(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta JSON Stato", segment_id, technology_id)
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "nuova",
                            "agcom_code": "CODJSON"})
    page = client.get(f"/offers/{offer_id}")
    match = re.search(r'<script[^>]*id="sintesi-json"[^>]*>(.*?)</script>',
                      page.text, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    assert data["status"] == "nuova"
    assert data["agcom_code"] == "CODJSON"


def test_offer_name_is_editable(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Nome Vecchio", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    assert 'id="offer-name"' in page.text
    response = _put(client, offer_id, {"fixed": {}, "rows": [],
                                       "name": "Offerta Nome Nuovo"})
    assert response.status_code == 200
    offer = _offer(db_session, offer_id)
    assert offer.name == "Offerta Nome Nuovo"
    assert offer.name_key == "offerta nome nuovo"


def test_duplicate_rename_is_rejected(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    offer_id = create_offer(client, "Offerta Uno", segment_id, technology_id)
    create_offer(client, "Offerta Due", segment_id, technology_id)
    response = _put(client, offer_id, {"fixed": {}, "rows": [], "name": "Offerta Due"})
    assert response.status_code == 422
    assert _offer(db_session, offer_id).name == "Offerta Uno"


def test_empty_rename_is_rejected(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Nome Vuoto", segment_id, technology_id)
    response = _put(client, offer_id, {"fixed": {}, "rows": [], "name": ""})
    assert response.status_code == 422


def test_list_shows_status_tag_and_agcom_chip(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Lista Tag", segment_id, technology_id)
    _put(client, offer_id, {"fixed": {}, "rows": [], "status": "chiusa",
                            "agcom_code": "CODLIST"})
    page = client.get("/")
    assert "status-chiusa" in page.text
    assert "CODLIST" in page.text


def test_editor_shows_status_card_and_agcom_badge(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Badge AGCOM", segment_id, technology_id)
    _put(client, offer_id, {"fixed": {}, "rows": [], "agcom_code": "CODBADGE"})
    page = client.get(f"/offers/{offer_id}")
    assert 'id="offer-status"' in page.text
    assert 'id="agcom-code"' in page.text
    assert 'id="agcom-badge"' in page.text
    assert 'id="technology-badge"' in page.text
    assert "data-badge=" in page.text
    assert "🏷️ CODBADGE" in page.text
    assert "Nessuna voce in questa tabella" in page.text
    assert 'class="req"' in page.text
    assert "<thead" not in page.text
    assert '>Ultima modifica</label>' in page.text
    assert '<div class="meta-value" id="offer-updated-at">' in page.text


def test_new_offer_page_has_status_and_agcom_box(
    client: TestClient,
) -> None:
    page = client.get("/offers/new")
    assert "Stato e codice AGCOM" in page.text
    assert 'id="offer-status"' in page.text
    assert 'id="agcom-code"' in page.text
    assert 'id="agcom-badge" class="agcom-chip" hidden' in page.text
    assert 'class="error-banner"' in page.text
    assert 'class="req"' in page.text
    assert "I campi con * sono obbligatori" in page.text
    assert "Nessuna voce in questa tabella" in page.text
    assert "<thead" not in page.text


def test_static_assets_are_cache_busted(client: TestClient) -> None:
    page = client.get("/offers/new")
    match = re.search(r"/static/editor\.js\?v=\d+", page.text)
    assert match is not None
    js = client.get(match.group(0))
    assert js.status_code == 200
    assert "updateEmptyState" in js.text
    assert "showError" in js.text
    assert "requestSave" in js.text
    assert "Confermi di voler applicare" in js.text
    assert "Modifiche applicate" in js.text
    assert "Riprendi le modifiche" in js.text
    assert "windtre-sintesi-draft" in js.text
    assert "btn danger" in js.text
    assert "btn danger-ghost" in js.text
    assert "salva per generare la Sintesi" in js.text
    assert "Non generare" in js.text
    assert "window.W3Modal" in js.text
    assert 'closest(".modal")' in js.text
    assert "window.prompt" not in js.text
    assert "beforeunload" not in js.text

    modal_match = re.search(r"/static/modal\.js\?v=\d+", page.text)
    assert modal_match is not None
    modal = client.get(modal_match.group(0))
    assert modal.status_code == 200
    assert "openPrompt" in modal.text
    assert "openError" in modal.text
    assert "modal-field-error" in modal.text
    assert "window.W3Modal" in modal.text


def test_brand_links_to_offers_list(client: TestClient) -> None:
    page = client.get("/offers/new")
    assert '<a class="brand" href="/">WIND3 <span>Precontratti</span> - MVP</a>' in page.text
    assert "WINDTRE Sintesi" not in page.text
    assert "— MVP" not in page.text


def test_badge_endpoint_serves_image(client: TestClient, technology_id: str) -> None:
    response = client.get(f"/technologies/{technology_id}/badge")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_badge_endpoint_missing_technology_returns_404(client: TestClient) -> None:
    response = client.get(
        "/technologies/00000000-0000-0000-0000-000000000000/badge"
    )
    assert response.status_code == 404


def test_list_has_delete_button_and_modal(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Eliminabile", segment_id, technology_id)
    page = client.get("/")
    assert 'class="btn small danger-ghost delete-offer"' in page.text
    assert 'class="btn small secondary duplicate-offer"' in page.text
    assert f'data-offer-id="{offer_id}"' in page.text
    assert f'src="/technologies/{technology_id}/badge"' in page.text
    assert re.search(r"/static/modal\.js\?v=\d+", page.text) is not None
    assert re.search(r"/static/offers_list\.js\?v=\d+", page.text) is not None


def test_save_buttons_labels(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Bottoni", segment_id, technology_id)
    editor = client.get(f"/offers/{offer_id}")
    assert 'id="save-btn" class="btn" hidden' in editor.text
    assert "Applica Modifiche" in editor.text
    assert 'id="discard-btn" class="btn danger-ghost" hidden' in editor.text
    assert "Ripristina" in editor.text
    assert "Genera Sintesi (.docx)" in editor.text
    new_page = client.get("/offers/new")
    assert "Crea offerta" in new_page.text


def test_editor_renders_group_separator_between_parents(
    client: TestClient, segment_id: str, technology_id: str, db_session: Session
) -> None:
    from app.models import Voce

    offer_id = create_offer(client, "Offerta Separatore", segment_id, technology_id)
    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    assert voce is not None
    response = _put(client, offer_id, {"fixed": {}, "rows": [
        {"block": "prezzo", "local_id": "p1", "voce_id": str(voce.id), "value": ""},
        {"block": "prezzo", "local_id": "p2", "voce_id": str(voce.id), "value": ""},
    ]})
    assert response.status_code == 200
    page = client.get(f"/offers/{offer_id}")
    assert 'class="group-separator"' in page.text


def test_editor_with_created_flag_is_ok(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Creata Flag", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}?created=1")
    assert page.status_code == 200


def test_nav_active_only_on_list(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Nav", segment_id, technology_id)
    list_page = client.get("/")
    assert 'href="/" class="active"' in list_page.text
    editor_page = client.get(f"/offers/{offer_id}")
    assert 'href="/" class="active"' not in editor_page.text
    new_page = client.get("/offers/new")
    assert 'href="/" class="active"' not in new_page.text


def test_detail_pages_have_back_breadcrumb(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Breadcrumb", segment_id, technology_id)
    editor = client.get(f"/offers/{offer_id}")
    assert 'class="breadcrumb"' in editor.text
    assert '<a href="/">← Offerte</a>' in editor.text
    assert "Offerta Breadcrumb</span>" in editor.text
    new_page = client.get("/offers/new")
    assert 'class="breadcrumb"' in new_page.text
    assert '<a href="/">← Offerte</a>' in new_page.text
    assert "Nuova offerta</span>" in new_page.text
