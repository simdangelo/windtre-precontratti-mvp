import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GeneratedDocument, Offer, OfferDocument, Segment
from app.services import offer as offer_service
from app.services import sintesi as sintesi_service


@dataclass(frozen=True)
class OfferDetail:
    offer: Offer
    segment_name: str
    sintesi: sintesi_service.SintesiData
    current_document: GeneratedDocument | None
    previous_documents: list[GeneratedDocument]
    sintesi_stale: bool


def _naive(value: datetime) -> datetime:
    """SQLite restituisce datetime senza timezone: normalizza per confronti."""
    return value.replace(tzinfo=None) if value.tzinfo else value


def sintesi_is_stale(
    document: OfferDocument, current_document: GeneratedDocument | None
) -> bool:
    if current_document is None:
        return False
    return _naive(document.updated_at) > _naive(current_document.generated_at)


def get_offer_detail(db: Session, offer_id: uuid.UUID) -> OfferDetail:
    offer = offer_service.get_offer(db, offer_id)
    # Il documento Sintesi nasce (get-or-create) al primo accesso, come nell'editor.
    document = offer_service.create_sintesi_document(db, offer_id)
    sintesi = sintesi_service.get_sintesi_data(db, offer_id)
    generated = list(
        db.scalars(
            select(GeneratedDocument)
            .where(GeneratedDocument.offer_document_id == document.id)
            .order_by(GeneratedDocument.generated_at.desc())
        ).all()
    )
    segment = db.get(Segment, offer.segment_id)
    current_document = next((g for g in generated if g.is_current), None)
    return OfferDetail(
        offer=offer,
        segment_name=segment.name if segment else "—",
        sintesi=sintesi,
        current_document=current_document,
        previous_documents=[g for g in generated if not g.is_current],
        sintesi_stale=sintesi_is_stale(document, current_document),
    )
