import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BulkOperationTarget,
    Category,
    DocType,
    DocumentTemplate,
    GeneratedDocument,
    Offer,
    OfferDocument,
    OfferFieldValue,
    OfferRow,
    OfferStatus,
    Segment,
    Technology,
)
from app.schemas import OfferCreate
from app.services.exceptions import (
    DocumentNotFoundError,
    DuplicateNameError,
    OfferNotFoundError,
    TemplateNotFoundError,
)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def create_offer(db: Session, data: OfferCreate) -> Offer:
    if db.get(Segment, data.segment_id) is None:
        raise OfferNotFoundError("Segmento inesistente")
    if data.technology_id and db.get(Technology, data.technology_id) is None:
        raise OfferNotFoundError("Tecnologia inesistente")

    name_key = normalize_name(data.name)
    if db.scalar(select(Offer).where(Offer.name_key == name_key)):
        raise DuplicateNameError(f"Un'offerta con nome '{data.name}' esiste già")

    offer = Offer(name=data.name.strip(), name_key=name_key, category=data.category,
                  segment_id=data.segment_id, technology_id=data.technology_id,
                  status=data.status, agcom_code=data.agcom_code.strip() or None)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def rename_offer(db: Session, offer: Offer, new_name: str) -> None:
    cleaned = new_name.strip()
    name_key = normalize_name(cleaned)
    existing = db.scalar(select(Offer).where(Offer.name_key == name_key))
    if existing is not None and existing.id != offer.id:
        raise DuplicateNameError(f"Un'offerta con nome '{cleaned}' esiste già")
    offer.name = cleaned
    offer.name_key = name_key


def duplicate_offer(db: Session, offer_id: uuid.UUID, new_name: str) -> Offer:
    """Duplica anagrafica e Sintesi; la copia nasce NUOVA e senza codice AGCOM."""
    source = get_offer(db, offer_id)
    cleaned = new_name.strip()
    name_key = normalize_name(cleaned)
    if db.scalar(select(Offer).where(Offer.name_key == name_key)):
        raise DuplicateNameError(f"Un'offerta con nome '{cleaned}' esiste già")

    copy = Offer(
        name=cleaned, name_key=name_key, category=source.category,
        segment_id=source.segment_id, technology_id=source.technology_id,
        status=OfferStatus.NUOVA, agcom_code=None,
    )
    db.add(copy)
    db.flush()

    source_doc = db.scalar(
        select(OfferDocument).where(
            OfferDocument.offer_id == source.id,
            OfferDocument.doc_type == DocType.SINTESI,
        )
    )
    if source_doc is not None:
        new_doc = OfferDocument(
            offer_id=copy.id, doc_type=DocType.SINTESI, template_id=source_doc.template_id
        )
        db.add(new_doc)
        db.flush()
        for value in db.scalars(
            select(OfferFieldValue).where(
                OfferFieldValue.offer_document_id == source_doc.id
            )
        ).all():
            db.add(OfferFieldValue(
                offer_document_id=new_doc.id,
                template_field_id=value.template_field_id,
                value_text=value.value_text,
            ))
        rows = db.scalars(
            select(OfferRow)
            .where(OfferRow.offer_document_id == source_doc.id)
            .order_by(OfferRow.sort_order)
        ).all()
        mapping: dict[uuid.UUID, uuid.UUID] = {}
        for row in rows:
            if row.parent_row_id is None:
                new_row = OfferRow(
                    offer_document_id=new_doc.id, block_id=row.block_id,
                    voce_id=row.voce_id, value_text=row.value_text,
                    sort_order=row.sort_order,
                )
                db.add(new_row)
                db.flush()
                mapping[row.id] = new_row.id
        for row in rows:
            if row.parent_row_id is not None:
                db.add(OfferRow(
                    offer_document_id=new_doc.id, block_id=row.block_id,
                    parent_row_id=mapping[row.parent_row_id], voce_id=row.voce_id,
                    value_text=row.value_text, sort_order=row.sort_order,
                ))
    db.commit()
    db.refresh(copy)
    return copy


def delete_offer(db: Session, offer_id: uuid.UUID) -> None:
    """Eliminazione definitiva: documenti, valori, righe, file registrati e
    target delle massive. Il nome dell'offerta torna disponibile."""
    offer = get_offer(db, offer_id)
    documents = list(
        db.scalars(select(OfferDocument).where(OfferDocument.offer_id == offer.id)).all()
    )
    document_ids = [document.id for document in documents]
    if document_ids:
        generated = list(
            db.scalars(
                select(GeneratedDocument).where(
                    GeneratedDocument.offer_document_id.in_(document_ids)
                )
            ).all()
        )
        for item in generated:
            path = Path(item.file_path)
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass
            db.delete(item)
        for value in db.scalars(
            select(OfferFieldValue).where(
                OfferFieldValue.offer_document_id.in_(document_ids)
            )
        ).all():
            db.delete(value)
        for row in db.scalars(
            select(OfferRow).where(OfferRow.offer_document_id.in_(document_ids))
        ).all():
            db.delete(row)
        for document in documents:
            db.delete(document)
    for target in db.scalars(
        select(BulkOperationTarget).where(BulkOperationTarget.offer_id == offer.id)
    ).all():
        db.delete(target)
    db.delete(offer)
    db.commit()


def find_sintesi_document(db: Session, offer_id: uuid.UUID) -> OfferDocument | None:
    offer = get_offer(db, offer_id)
    return db.scalar(
        select(OfferDocument).where(
            OfferDocument.offer_id == offer.id, OfferDocument.doc_type == DocType.SINTESI
        )
    )


def create_sintesi_document(db: Session, offer_id: uuid.UUID) -> OfferDocument:
    """Crea (on the fly) il documento Sintesi a DB, se non esiste."""
    offer = get_offer(db, offer_id)
    existing = find_sintesi_document(db, offer_id)
    if existing is not None:
        return existing
    template = db.scalar(
        select(DocumentTemplate).where(
            DocumentTemplate.doc_type == DocType.SINTESI,
            DocumentTemplate.category == Category.FISSE,
            DocumentTemplate.is_active.is_(True),
        )
    )
    if template is None:
        raise TemplateNotFoundError("Nessun template SINTESI attivo per la categoria FISSE")
    doc = OfferDocument(offer_id=offer.id, doc_type=DocType.SINTESI, template_id=template.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@dataclass(frozen=True)
class OfferOverview:
    offer: Offer
    has_sintesi: bool
    technology: Technology | None = None


def list_offers_overview(db: Session) -> list[OfferOverview]:
    offers = list(db.scalars(select(Offer).order_by(Offer.name)).all())
    technologies = {t.id: t for t in db.scalars(select(Technology)).all()}
    doc_offer_ids = set(
        db.scalars(
            select(OfferDocument.offer_id).where(OfferDocument.doc_type == DocType.SINTESI)
        ).all()
    )
    return [
        OfferOverview(
            offer=o,
            has_sintesi=o.id in doc_offer_ids,
            technology=technologies.get(o.technology_id) if o.technology_id else None,
        )
        for o in offers
    ]


def list_offers(db: Session) -> list[Offer]:
    return list(db.scalars(select(Offer).order_by(Offer.name)).all())


def get_offer(db: Session, offer_id: uuid.UUID) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise OfferNotFoundError(f"Offerta {offer_id} non trovata")
    return offer


def get_sintesi_document(db: Session, offer_id: uuid.UUID) -> OfferDocument:
    offer = get_offer(db, offer_id)
    doc = db.scalar(
        select(OfferDocument).where(
            OfferDocument.offer_id == offer.id, OfferDocument.doc_type == DocType.SINTESI
        )
    )
    if doc is None:
        raise DocumentNotFoundError(f"Documento Sintesi assente per l'offerta {offer.name}")
    return doc


def touch(db: Session, offer: Offer, doc: OfferDocument) -> None:
    offer.updated_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
