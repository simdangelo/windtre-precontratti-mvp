from fastapi.testclient import TestClient

from tests.conftest import create_offer


def test_editor_shows_definitions_and_voci(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Editor", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    assert page.status_code == 200
    assert "Servizio/i e apparecchiature" in page.text
    assert "Prezzo" in page.text
    assert "Costi" in page.text
    assert "Costo mensile" in page.text


def test_editor_shows_derived_values(client, segment_id, technology_id) -> None:
    import json
    import re

    offer_id = create_offer(client, "Offerta Derivati", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    match = re.search(r'<script[^>]*id="sintesi-json"[^>]*>(.*?)</script>', page.text, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    values = {f["key"]: f["value"] for f in data["fixed_fields"]}
    assert values["nome_offerta"] == "Offerta Derivati"
    assert values["velocita_download"] == "300,00 Mbps in Download"
    assert values["velocita_upload"] == "50,00 Mbps in Upload"


def test_save_and_read_sintesi(client, segment_id, technology_id, db_session) -> None:
    from sqlalchemy import select

    from app.models import OfferRow, Voce

    offer_id = create_offer(client, "Offerta Save", segment_id, technology_id)
    voce_padre = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    voce_figlio = db_session.scalar(select(Voce).where(Voce.label == "Per i già clienti"))
    payload = {
        "fixed": {"disponibilita": "06-10-2025", "servizi": "Fisso fonia e Internet",
                  "traffico_internet": "Illimitato", "traffico_fonia": "Chiamate illimitate",
                  "apparecchiature": "Modem Wi-Fi 7", "durata_minima": "24 mesi",
                  "rinnovo": "Rinnovo automatico", "risoluzione_anticipata": "Costo previsto",
                  "sblocco_apparato": "Non applicabile"},
        "rows": [
            {"block": "prezzo", "local_id": "p1", "voce_id": str(voce_padre.id), "value": ""},
            {"block": "prezzo", "local_id": "p2", "parent_local_id": "p1",
             "voce_id": str(voce_figlio.id), "value": "20,99 euro/mese"},
        ],
    }
    assert client.put(f"/api/offers/{offer_id}/sintesi", json=payload).status_code == 200
    page = client.get(f"/offers/{offer_id}")
    assert "20,99 euro/mese" in page.text
    rows = db_session.scalars(select(OfferRow)).all()
    assert len(rows) == 2
    assert any(r.parent_row_id is not None for r in rows)


def test_save_rejects_unknown_field(client, segment_id, technology_id) -> None:
    offer_id = create_offer(client, "Offerta Invalid", segment_id, technology_id)
    response = client.put(f"/api/offers/{offer_id}/sintesi",
                          json={"fixed": {"inesistente": "x"}, "rows": []})
    assert response.status_code == 404
