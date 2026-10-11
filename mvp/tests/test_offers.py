from fastapi.testclient import TestClient


def test_create_offer_and_list(client: TestClient, segment_id: str, technology_id: str) -> None:
    response = client.post(
        "/offers",
        data={"name": "SUPER Internet Casa 5G", "segment_id": segment_id,
              "technology_id": technology_id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    offer_id = response.headers["location"].rsplit("/", 1)[-1]
    page = client.get("/")
    assert "SUPER Internet Casa 5G" in page.text
    assert f'<a href="/offers/{offer_id}">SUPER Internet Casa 5G</a>' in page.text
    assert "Apri" not in page.text
    assert "Crea Sintesi" in page.text


def test_create_sintesi_from_list(client: TestClient, segment_id: str, technology_id: str) -> None:
    from tests.conftest import create_offer_only

    offer_id = create_offer_only(client, "Offerta Con Sintesi", segment_id, technology_id)
    assert "Crea Sintesi" in client.get("/").text
    create = client.post(f"/offers/{offer_id}/sintesi", follow_redirects=False)
    assert create.status_code == 303
    assert create.headers["location"] == f"/offers/{offer_id}"


def test_open_editor_creates_sintesi_document(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    from tests.conftest import create_offer_only

    offer_id = create_offer_only(client, "Offerta Senza Sintesi", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    assert page.status_code == 200
    assert "Tabelle fisse" in page.text
    assert "Servizio/i e apparecchiature" in page.text


def test_duplicate_name_is_rejected(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    payload = {"name": "Offerta Duplicata", "segment_id": segment_id,
               "technology_id": technology_id}
    assert client.post("/offers", data=payload, follow_redirects=False).status_code == 303
    second = client.post("/offers", data=payload, follow_redirects=False)
    assert second.status_code == 400
    assert "esiste già" in second.text


def test_offer_not_found(client: TestClient) -> None:
    response = client.get("/offers/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_new_offer_page_shows_full_form(client: TestClient) -> None:
    page = client.get("/offers/new")
    assert page.status_code == 200
    assert "Nome offerta" in page.text
    assert "Disponibilit" in page.text          # campo fisso nelle definizioni JSON
    assert '"code": "prezzo"' in page.text      # blocco dinamico Prezzo
    assert "editor.js" in page.text


def test_new_offer_page_has_derived_wiring(client: TestClient) -> None:
    page = client.get("/offers/new")
    assert 'id="offer-name"' in page.text
    assert 'id="technology-id"' in page.text
    assert "data-download=" in page.text
    assert "/static/editor.js" in page.text


def test_editor_pages_link_editor_css(client: TestClient) -> None:
    for path in ("/offers/new",):
        page = client.get(path)
        assert page.status_code == 200
        assert "/static/editor.css" in page.text


def test_create_offer_full_via_api(client, db_session, segment_id, technology_id) -> None:
    from sqlalchemy import select

    from app.models import Offer, OfferDocument, OfferRow, Voce

    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo SIM"))
    payload = {
        "name": "Offerta Full", "segment_id": segment_id, "technology_id": technology_id,
        "fixed": {"disponibilita": "01-01-2026", "servizi": "Fisso fonia e Internet",
                  "traffico_internet": "Illimitato", "traffico_fonia": "Chiamate illimitate",
                  "apparecchiature": "Modem", "durata_minima": "24 mesi",
                  "rinnovo": "Rinnovo automatico", "risoluzione_anticipata": "Costo",
                  "sblocco_apparato": "Non applicabile"},
        "rows": [{"block": "prezzo", "local_id": "r1",
                  "voce_id": str(voce.id), "value": "10 euro"}],
    }
    response = client.post("/api/offers", json=payload)
    assert response.status_code == 201
    offer_id = response.json()["id"]

    assert client.get(f"/offers/{offer_id}").status_code == 200
    assert db_session.scalar(select(Offer).where(Offer.name == "Offerta Full")) is not None
    assert db_session.scalars(select(OfferDocument)).all()
    assert len(db_session.scalars(select(OfferRow)).all()) == 1


def test_create_offer_full_invalid_creates_nothing(client, db_session, segment_id, technology_id):
    from sqlalchemy import select

    from app.models import Offer

    response = client.post("/api/offers", json={
        "name": "Offerta Ko", "segment_id": segment_id, "technology_id": technology_id,
        "fixed": {"inesistente": "x"}, "rows": [],
    })
    assert response.status_code == 404
    assert db_session.scalar(select(Offer).where(Offer.name == "Offerta Ko")) is None
