from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Offer, OfferFieldValue, OfferRow, Technology, TemplateBlock, Voce
from tests.conftest import create_offer


def _voce(db_session, block_code: str, label: str) -> str:
    block = db_session.scalar(select(TemplateBlock).where(TemplateBlock.code == block_code))
    voce = db_session.scalar(select(Voce).where(Voce.block_id == block.id, Voce.label == label))
    assert voce is not None
    return str(voce.id)


def _set_sintesi(
    client, offer_id: str, fixed: dict[str, str], voce_value: str | None,
    db_session,
) -> None:
    rows = []
    if voce_value is not None:
        rows = [{"block": "prezzo", "local_id": "x1",
                 "voce_id": _voce(db_session, "prezzo", "Costo SIM"),
                 "value": voce_value}]
    response = client.put(f"/api/offers/{offer_id}/sintesi",
                          json={"fixed": fixed, "rows": rows})
    assert response.status_code == 200


def test_bulk_multi_preview_and_apply(
    client: TestClient, db_session, segment_id, technology_id
) -> None:
    offer_a = create_offer(client, "Bulk Multi A", segment_id, technology_id)
    offer_b = create_offer(client, "Bulk Multi B", segment_id, technology_id)
    _set_sintesi(client, offer_a, {"disponibilita": "01-01-2026"}, "10 euro", db_session)
    _set_sintesi(client, offer_b, {}, "12 euro", db_session)

    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_a, offer_b],
        "items": [
            {"target_kind": "template_field", "template_field_key": "durata_minima",
             "new_value": "24 mesi"},
            {"target_kind": "voce", "voce_id": _voce(db_session, "prezzo", "Costo SIM"),
             "new_value": "12 euro"},
        ],
    })
    assert preview.status_code == 200
    body = preview.json()
    targets = {t["offer_name"]: t for t in body["targets"]}
    assert targets["Bulk Multi A"]["outcome"] == "da_modificare"
    assert targets["Bulk Multi A"]["changed_items"] == 2
    assert targets["Bulk Multi B"]["changed_items"] == 1
    assert body["counts"]["offerte_modificate"] == 2
    assert body["counts"]["valori_modificati"] == 3

    apply = client.post(f"/api/bulk/{body['operation_id']}/apply")
    assert apply.status_code == 200
    counts = apply.json()["counts"]
    assert counts["offerte_modificate"] == 2
    assert counts["valori_modificati"] == 3

    durata_values = list(db_session.scalars(
        select(OfferFieldValue).where(OfferFieldValue.value_text == "24 mesi")
    ).all())
    assert len(durata_values) == 2
    sim_rows = list(db_session.scalars(
        select(OfferRow).where(OfferRow.value_text == "12 euro")
    ).all())
    assert len(sim_rows) == 2


def test_bulk_voce_absent_is_skipped(
    client: TestClient, db_session, segment_id, technology_id
) -> None:
    offer_present = create_offer(client, "Bulk Voce Presente", segment_id, technology_id)
    offer_absent = create_offer(client, "Bulk Voce Assente", segment_id, technology_id)
    _set_sintesi(client, offer_present, {}, "10 euro", db_session)
    _set_sintesi(client, offer_absent, {}, None, db_session)

    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_present, offer_absent],
        "items": [{"target_kind": "voce",
                   "voce_id": _voce(db_session, "prezzo", "Costo SIM"),
                   "new_value": "9 euro"}],
    })
    assert preview.status_code == 200
    body = preview.json()
    targets = {t["offer_name"]: t for t in body["targets"]}
    assert targets["Bulk Voce Presente"]["outcome"] == "da_modificare"
    assert targets["Bulk Voce Assente"]["outcome"] == "saltata_assente"
    assert targets["Bulk Voce Assente"]["skipped_items"] == 1
    assert body["counts"]["offerte_saltate"] == 1
    assert body["counts"]["voci_saltate"] == 1

    apply = client.post(f"/api/bulk/{body['operation_id']}/apply")
    assert apply.status_code == 200
    counts = apply.json()["counts"]
    assert counts["offerte_modificate"] == 1
    assert counts["offerte_saltate"] == 1
    assert counts["voci_saltate"] == 1

    updated = list(db_session.scalars(
        select(OfferRow).where(OfferRow.value_text == "9 euro")
    ).all())
    assert len(updated) == 1


def test_bulk_fixed_field_empty_value_is_filled(
    client: TestClient, db_session, segment_id, technology_id
) -> None:
    offer_id = create_offer(client, "Bulk Campo Vuoto", segment_id, technology_id)
    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "template_field",
                   "template_field_key": "durata_minima", "new_value": "24 mesi"}],
    })
    assert preview.status_code == 200
    body = preview.json()
    change = body["targets"][0]["changes"][0]
    assert change["old_value"] is None
    assert change["outcome"] == "modificato"

    apply = client.post(f"/api/bulk/{body['operation_id']}/apply")
    assert apply.status_code == 200
    assert apply.json()["counts"]["valori_modificati"] == 1
    values = list(db_session.scalars(
        select(OfferFieldValue).where(OfferFieldValue.value_text == "24 mesi")
    ).all())
    assert len(values) == 1


def test_bulk_preview_validations(
    client: TestClient, segment_id, technology_id, db_session
) -> None:
    offer_id = create_offer(client, "Bulk Validazioni", segment_id, technology_id)
    empty_items = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id], "items": [],
    })
    assert empty_items.status_code == 422

    bad_field = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "template_field",
                   "template_field_key": "campo_inesistente", "new_value": "x"}],
    })
    assert bad_field.status_code == 404

    bad_voce = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "voce",
                   "voce_id": "00000000-0000-0000-0000-000000000000",
                   "new_value": "x"}],
    })
    assert bad_voce.status_code == 404


def test_bulk_technology_changes_offers(
    client: TestClient, db_session, segment_id, technology_id
) -> None:
    offer_a = create_offer(client, "Bulk Tecnologia A", segment_id, technology_id)
    offer_b = create_offer(client, "Bulk Tecnologia B", segment_id, technology_id)
    fttc = db_session.scalar(select(Technology).where(Technology.code == "FTTC"))
    assert fttc is not None

    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_a, offer_b],
        "items": [{"target_kind": "technology", "technology_id": str(fttc.id)}],
    })
    assert preview.status_code == 200
    body = preview.json()
    assert body["counts"]["offerte_modificate"] == 2
    change = body["targets"][0]["changes"][0]
    assert change["label"] == "Tecnologia"
    assert change["outcome"] == "modificato"

    apply = client.post(f"/api/bulk/{body['operation_id']}/apply")
    assert apply.status_code == 200
    counts = apply.json()["counts"]
    assert counts["offerte_modificate"] == 2
    assert counts["valori_modificati"] == 2

    db_session.expire_all()
    import uuid as uuid_module

    for offer_id in (offer_a, offer_b):
        offer = db_session.get(Offer, uuid_module.UUID(offer_id))
        assert offer is not None
        assert offer.technology_id == fttc.id


def test_bulk_technology_same_is_unchanged(
    client: TestClient, db_session, segment_id, technology_id
) -> None:
    offer_id = create_offer(client, "Bulk Tecnologia Uguale", segment_id, technology_id)
    preview = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "technology", "technology_id": technology_id}],
    })
    assert preview.status_code == 200
    body = preview.json()
    assert body["targets"][0]["outcome"] == "invariata"
    assert body["counts"]["offerte_invariate"] == 1


def test_bulk_unknown_technology_returns_404(
    client: TestClient, segment_id, technology_id
) -> None:
    offer_id = create_offer(client, "Bulk Tecnologia Ignota", segment_id, technology_id)
    response = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "technology",
                   "technology_id": "00000000-0000-0000-0000-000000000000"}],
    })
    assert response.status_code == 404


def test_bulk_page_confirm_spinner_and_preview_reset(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    create_offer(client, "Bulk Pagina", segment_id, technology_id)
    page = client.get("/bulk")
    assert page.status_code == 200
    assert 'id="apply-spinner"' in page.text
    assert "Applicare le modifiche?" in page.text
    assert "Le modifiche massive sono state applicate correttamente." in page.text
    assert "Modifiche cambiate: clicca di nuovo Anteprima." in page.text
    assert "window.location.reload" not in page.text
    assert "2. Cosa modificare" in page.text
    assert 'class="group-divider"' in page.text
    assert "Tabelle fisse" in page.text
    assert "Tabelle dinamiche" in page.text
    assert 'class="bulk-derived"' in page.text
    assert "data-download=" in page.text
    assert 'class="group-hint"' in page.text
    assert "Derivata dalla tecnologia" not in page.text


def test_bulk_apply_twice_is_rejected(
    client: TestClient, segment_id, technology_id, db_session
) -> None:
    offer_id = create_offer(client, "Bulk Doppia", segment_id, technology_id)
    _set_sintesi(client, offer_id, {}, "10 euro", db_session)
    body = client.post("/api/bulk/preview", json={
        "offer_ids": [offer_id],
        "items": [{"target_kind": "voce",
                   "voce_id": _voce(db_session, "prezzo", "Costo SIM"),
                   "new_value": "11 euro"}],
    }).json()
    assert client.post(f"/api/bulk/{body['operation_id']}/apply").status_code == 200
    assert client.post(f"/api/bulk/{body['operation_id']}/apply").status_code == 422
