import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BulkApplyResponse,
    BulkChangePreview,
    BulkPreviewResponse,
    BulkRequest,
    BulkTargetPreview,
    OfferCreateFull,
    OfferDuplicateRequest,
    SintesiSaveRequest,
    VoceCreate,
)
from app.services import bulk as bulk_service
from app.services import generation as generation_service
from app.services import offer as offer_service
from app.services import sintesi as sintesi_service
from app.services import voce as voce_service

router = APIRouter()


def _bulk_counts(states: list[bulk_service.TargetState]) -> dict[str, int]:
    return {
        "offerte_modificate": sum(1 for s in states if s.changed_items),
        "offerte_invariate": sum(
            1 for s in states if not s.changed_items and not s.skipped_items
        ),
        "offerte_saltate": sum(
            1 for s in states if not s.changed_items and s.skipped_items
        ),
        "valori_modificati": sum(s.changed_items for s in states),
        "voci_saltate": sum(s.skipped_items for s in states),
    }


@router.post("/bulk/preview")
def bulk_preview(
    data: BulkRequest, db: Annotated[Session, Depends(get_db)]
) -> BulkPreviewResponse:
    operation, states = bulk_service.preview_bulk(db, data)
    return BulkPreviewResponse(
        operation_id=operation.id,
        counts=_bulk_counts(states),
        targets=[
            BulkTargetPreview(
                offer_id=s.offer.id,
                offer_name=s.offer.name,
                outcome=s.outcome.value,
                changed_items=s.changed_items,
                skipped_items=s.skipped_items,
                reason=s.reason,
                changes=[
                    BulkChangePreview(
                        label=change.label,
                        kind=change.kind,
                        old_value=change.old_value,
                        new_value=change.new_value,
                        outcome=change.outcome,
                    )
                    for change in s.changes
                ],
            )
            for s in states
        ],
    )


@router.post("/bulk/{operation_id}/apply")
def bulk_apply(
    operation_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> BulkApplyResponse:
    counts = bulk_service.apply_bulk(db, operation_id)
    return BulkApplyResponse(operation_id=operation_id, counts=counts)


@router.post("/offers", status_code=status.HTTP_201_CREATED)
def create_offer_full(
    data: OfferCreateFull, db: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    offer = sintesi_service.create_offer_with_sintesi(db, data)
    return {"id": str(offer.id)}


@router.put("/offers/{offer_id}/sintesi")
def save_sintesi(
    offer_id: uuid.UUID, data: SintesiSaveRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    sintesi_service.save_sintesi(db, offer_id, data)
    return {"status": "ok"}


@router.post("/offers/{offer_id}/generate", status_code=status.HTTP_201_CREATED)
def generate(
    offer_id: uuid.UUID,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    force: bool = False,
) -> dict[str, object]:
    document, created = generation_service.render_sintesi(db, offer_id, force=force)
    if not created:
        response.status_code = status.HTTP_200_OK
    return {
        "document_id": str(document.id),
        "file_path": document.file_path,
        "generated": created,
    }


@router.post("/voci", status_code=status.HTTP_201_CREATED)
def create_voce(data: VoceCreate, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    voce = voce_service.create_voce(db, data)
    return {"id": str(voce.id), "label": voce.label, "code": voce.code}


@router.delete("/offers/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offer(offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> None:
    offer_service.delete_offer(db, offer_id)


@router.post("/offers/{offer_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_offer(
    offer_id: uuid.UUID,
    data: OfferDuplicateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    offer = offer_service.duplicate_offer(db, offer_id, data.name)
    return {"id": str(offer.id), "name": offer.name}
