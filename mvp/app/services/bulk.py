import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BulkOperation,
    BulkOperationItem,
    BulkOperationTarget,
    BulkStatus,
    BulkTargetKind,
    Offer,
    OfferFieldValue,
    OfferRow,
    Outcome,
    SourceKind,
    Technology,
    TemplateField,
    Voce,
)
from app.schemas import BulkItemIn, BulkRequest
from app.services import offer as offer_service
from app.services.exceptions import (
    BulkOperationNotFoundError,
    DomainValidationError,
    FieldNotFoundError,
    TechnologyNotFoundError,
    VoceNotFoundError,
)

ITEM_CHANGED = "modificato"
ITEM_UNCHANGED = "invariato"
ITEM_SKIPPED = "saltato"


@dataclass(frozen=True)
class ItemState:
    label: str
    kind: str
    old_value: str | None
    new_value: str
    outcome: str


@dataclass(frozen=True)
class TargetState:
    offer: Offer
    offer_document_id: uuid.UUID
    outcome: Outcome
    changed_items: int
    skipped_items: int
    reason: str | None
    changes: list[ItemState] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedItem:
    target_kind: BulkTargetKind
    template_field: TemplateField | None
    voce: Voce | None
    technology: Technology | None
    new_value: str


def _resolve_item(db: Session, item: BulkItemIn) -> ResolvedItem:
    if item.target_kind == BulkTargetKind.TEMPLATE_FIELD:
        field_def = db.scalar(
            select(TemplateField).where(TemplateField.key == item.template_field_key)
        )
        if field_def is None or field_def.source_kind != SourceKind.INPUT:
            raise FieldNotFoundError(f"Campo '{item.template_field_key}' non modificabile")
        return ResolvedItem(item.target_kind, field_def, None, None, item.new_value)
    if item.target_kind == BulkTargetKind.TECHNOLOGY:
        technology = db.get(Technology, item.technology_id)
        if technology is None:
            raise TechnologyNotFoundError(f"Tecnologia {item.technology_id} inesistente")
        return ResolvedItem(item.target_kind, None, None, technology, item.new_value)
    voce = db.get(Voce, item.voce_id)
    if voce is None or not voce.is_active:
        raise VoceNotFoundError(f"Voce {item.voce_id} inesistente")
    return ResolvedItem(item.target_kind, None, voce, None, item.new_value)


def _evaluate_item(
    db: Session, item: ResolvedItem, offer: Offer, document_id: uuid.UUID
) -> ItemState:
    if item.template_field is not None:
        field_def = item.template_field
        value = db.scalar(
            select(OfferFieldValue).where(
                OfferFieldValue.offer_document_id == document_id,
                OfferFieldValue.template_field_id == field_def.id,
            )
        )
        if value is None or value.value_text != item.new_value:
            old = value.value_text if value is not None else None
            return ItemState(field_def.label, "Campo", old, item.new_value, ITEM_CHANGED)
        return ItemState(
            field_def.label, "Campo", value.value_text, item.new_value, ITEM_UNCHANGED
        )

    if item.technology is not None:
        technology = item.technology
        current = db.get(Technology, offer.technology_id) if offer.technology_id else None
        if current is not None and current.id == technology.id:
            return ItemState(
                "Tecnologia", "Tecnologia", current.name, technology.name, ITEM_UNCHANGED
            )
        return ItemState(
            "Tecnologia", "Tecnologia",
            current.name if current is not None else None,
            technology.name, ITEM_CHANGED,
        )

    voce = item.voce
    assert voce is not None
    rows = db.scalars(
        select(OfferRow).where(
            OfferRow.offer_document_id == document_id,
            OfferRow.voce_id == voce.id,
        )
    ).all()
    if not rows:
        return ItemState(voce.label, "Voce", None, item.new_value, ITEM_SKIPPED)
    if all(row.value_text == item.new_value for row in rows):
        return ItemState(voce.label, "Voce", item.new_value, item.new_value, ITEM_UNCHANGED)
    old = next(
        row.value_text for row in rows if row.value_text != item.new_value
    )
    return ItemState(voce.label, "Voce", old, item.new_value, ITEM_CHANGED)


def _evaluate(
    db: Session, items: list[ResolvedItem], offer: Offer, document_id: uuid.UUID
) -> TargetState:
    changes = [_evaluate_item(db, item, offer, document_id) for item in items]
    changed = sum(1 for change in changes if change.outcome == ITEM_CHANGED)
    skipped = sum(1 for change in changes if change.outcome == ITEM_SKIPPED)
    if changed:
        outcome = Outcome.DA_MODIFICARE
    elif skipped:
        outcome = Outcome.SALTATA_ASSENTE
    else:
        outcome = Outcome.INVARIATA
    parts: list[str] = []
    if changed:
        parts.append(f"{changed} da modificare")
    if skipped:
        parts.append(f"{skipped} saltate (voce assente)")
    reason = ", ".join(parts) if parts else None
    return TargetState(offer, document_id, outcome, changed, skipped, reason, changes)


def preview_bulk(db: Session, req: BulkRequest) -> tuple[BulkOperation, list[TargetState]]:
    items = [_resolve_item(db, item) for item in req.items]

    states: list[TargetState] = []
    for offer_id in req.offer_ids:
        offer = offer_service.get_offer(db, offer_id)
        doc = offer_service.get_sintesi_document(db, offer_id)
        states.append(_evaluate(db, items, offer, doc.id))

    operation = BulkOperation(
        status=BulkStatus.ANTEPRIMA,
        offers_selected_count=len(req.offer_ids),
        offers_changed_count=sum(1 for state in states if state.changed_items),
    )
    db.add(operation)
    db.flush()
    for order, item in enumerate(items):
        db.add(BulkOperationItem(
            bulk_operation_id=operation.id,
            sort_order=order,
            target_kind=item.target_kind,
            template_field_id=item.template_field.id if item.template_field else None,
            voce_id=item.voce.id if item.voce else None,
            technology_id=item.technology.id if item.technology else None,
            new_value_text=item.new_value,
        ))
    for state in states:
        db.add(BulkOperationTarget(
            bulk_operation_id=operation.id, offer_id=state.offer.id,
            offer_document_id=state.offer_document_id, outcome=state.outcome,
            changed_items=state.changed_items, skipped_items=state.skipped_items,
            reason=state.reason,
        ))
    db.commit()
    db.refresh(operation)
    return operation, states


def apply_bulk(db: Session, operation_id: uuid.UUID) -> dict[str, int]:
    operation = db.get(BulkOperation, operation_id)
    if operation is None:
        raise BulkOperationNotFoundError("Operazione massiva non trovata")
    if operation.status != BulkStatus.ANTEPRIMA:
        raise DomainValidationError("Operazione già applicata o annullata")

    items = list(db.scalars(
        select(BulkOperationItem)
        .where(BulkOperationItem.bulk_operation_id == operation.id)
        .order_by(BulkOperationItem.sort_order)
    ).all())
    targets = list(db.scalars(
        select(BulkOperationTarget).where(
            BulkOperationTarget.bulk_operation_id == operation.id
        )
    ).all())

    counts = {
        "offerte_modificate": 0,
        "offerte_invariate": 0,
        "offerte_saltate": 0,
        "valori_modificati": 0,
        "voci_saltate": 0,
    }

    for target in targets:
        if target.outcome == Outcome.INVARIATA:
            counts["offerte_invariate"] += 1
            continue
        if target.outcome == Outcome.SALTATA_ASSENTE:
            counts["offerte_saltate"] += 1
            counts["voci_saltate"] += target.skipped_items
            continue

        offer = db.get(Offer, target.offer_id)
        changed_here = 0
        for item in items:
            if item.target_kind == BulkTargetKind.TEMPLATE_FIELD:
                value = db.scalar(
                    select(OfferFieldValue).where(
                        OfferFieldValue.offer_document_id == target.offer_document_id,
                        OfferFieldValue.template_field_id == item.template_field_id,
                    )
                )
                if value is None:
                    db.add(OfferFieldValue(
                        offer_document_id=target.offer_document_id,
                        template_field_id=item.template_field_id,
                        value_text=item.new_value_text,
                    ))
                    changed_here += 1
                    counts["valori_modificati"] += 1
                elif value.value_text != item.new_value_text:
                    value.value_text = item.new_value_text
                    changed_here += 1
                    counts["valori_modificati"] += 1
            elif item.target_kind == BulkTargetKind.TECHNOLOGY:
                if offer is not None and offer.technology_id != item.technology_id:
                    offer.technology_id = item.technology_id
                    changed_here += 1
                    counts["valori_modificati"] += 1
            else:
                rows = db.scalars(
                    select(OfferRow).where(
                        OfferRow.offer_document_id == target.offer_document_id,
                        OfferRow.voce_id == item.voce_id,
                    )
                ).all()
                if not rows:
                    counts["voci_saltate"] += 1
                    continue
                updated = False
                for row in rows:
                    if row.value_text != item.new_value_text:
                        row.value_text = item.new_value_text
                        updated = True
                if updated:
                    changed_here += 1
                    counts["valori_modificati"] += 1

        if changed_here:
            target.outcome = Outcome.APPLICATA
            counts["offerte_modificate"] += 1
            if offer is not None:
                offer.updated_at = datetime.now(UTC)

    operation.status = BulkStatus.APPLICATA
    operation.applied_at = datetime.now(UTC)
    operation.offers_changed_count = counts["offerte_modificate"]
    db.commit()
    return counts
