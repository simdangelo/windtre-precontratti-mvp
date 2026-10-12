import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedDocument, Technology
from app.schemas import (
    BulkApplyResponse,
    BulkChangePreview,
    BulkPreviewResponse,
    BulkRequest,
    BulkTargetPreview,
    GeneratedDocumentRead,
    OfferCreateFull,
    OfferDetailRead,
    OfferDocumentRead,
    OfferDuplicateRequest,
    OfferOverviewRead,
    OfferSummary,
    SegmentRead,
    SintesiDataRead,
    SintesiSaveRequest,
    TechnologyBrief,
    TechnologyRead,
    VoceCreate,
)
from app.services import bulk as bulk_service
from app.services import catalog as catalog_service
from app.services import detail as detail_service
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


def _badge_url(technology: Technology | None) -> str | None:
    if technology is None or not catalog_service.has_badge(technology):
        return None
    return f"/api/technologies/{technology.id}/badge"


def _technology_brief(technology: Technology) -> TechnologyBrief:
    return TechnologyBrief(
        id=technology.id, name=technology.name, badge_url=_badge_url(technology)
    )


def _generated_document_read(document: GeneratedDocument) -> GeneratedDocumentRead:
    return GeneratedDocumentRead(
        id=document.id,
        file_name=Path(document.file_path).name,
        generated_at=document.generated_at,
        is_current=document.is_current,
        download_url=f"/api/documents/{document.id}/download",
    )


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


@router.get("/offers", response_model=list[OfferOverviewRead])
def list_offers(db: Annotated[Session, Depends(get_db)]) -> list[OfferOverviewRead]:
    return [
        OfferOverviewRead(
            id=overview.offer.id,
            name=overview.offer.name,
            category=overview.offer.category,
            status=overview.offer.status,
            agcom_code=overview.offer.agcom_code,
            has_sintesi=overview.has_sintesi,
            technology=(
                None if overview.technology is None
                else _technology_brief(overview.technology)
            ),
            updated_at=overview.offer.updated_at,
        )
        for overview in offer_service.list_offers_overview(db)
    ]


@router.get("/offers/{offer_id}", response_model=OfferDetailRead)
def get_offer_detail(
    offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> OfferDetailRead:
    # Nota: get-or-create del documento Sintesi (stesso comportamento dell'editor).
    detail = detail_service.get_offer_detail(db, offer_id)
    offer = detail.offer
    return OfferDetailRead(
        offer=OfferSummary(
            id=offer.id,
            name=offer.name,
            category=offer.category,
            status=offer.status,
            agcom_code=offer.agcom_code,
            updated_at=offer.updated_at,
        ),
        segment_name=detail.segment_name,
        sintesi=SintesiDataRead.model_validate(
            sintesi_service.sintesi_to_json(detail.sintesi)
        ),
        current_document=(
            None if detail.current_document is None
            else _generated_document_read(detail.current_document)
        ),
        previous_documents=[
            _generated_document_read(document)
            for document in detail.previous_documents
        ],
        sintesi_stale=detail.sintesi_stale,
    )


@router.get("/sintesi/template", response_model=SintesiDataRead)
def sintesi_template(db: Annotated[Session, Depends(get_db)]) -> SintesiDataRead:
    data = sintesi_service.get_sintesi_template_data(db)
    return SintesiDataRead.model_validate(sintesi_service.sintesi_to_json(data))


@router.get("/technologies", response_model=list[TechnologyRead])
def list_technologies(db: Annotated[Session, Depends(get_db)]) -> list[TechnologyRead]:
    return [
        TechnologyRead(
            id=technology.id,
            code=technology.code,
            name=technology.name,
            max_download_mbps=technology.max_download_mbps,
            max_upload_mbps=technology.max_upload_mbps,
            badge_url=_badge_url(technology),
        )
        for technology in catalog_service.list_technologies(db)
    ]


@router.get("/segments", response_model=list[SegmentRead])
def list_segments(db: Annotated[Session, Depends(get_db)]) -> list[SegmentRead]:
    return [
        SegmentRead.model_validate(segment)
        for segment in catalog_service.list_segments(db)
    ]


@router.get("/technologies/{technology_id}/badge")
def technology_badge(
    technology_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    path = catalog_service.get_technology_badge_path(db, technology_id)
    return FileResponse(
        path, media_type=catalog_service.PNG_MEDIA_TYPE, filename=path.name
    )


@router.get("/documents/{document_id}/download")
def document_download(
    document_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    path = catalog_service.get_generated_document_path(db, document_id)
    return FileResponse(
        path, media_type=catalog_service.DOCX_MEDIA_TYPE, filename=path.name
    )


@router.post(
    "/offers/{offer_id}/sintesi",
    status_code=status.HTTP_201_CREATED,
    response_model=OfferDocumentRead,
)
def create_sintesi_document(
    offer_id: uuid.UUID,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> OfferDocumentRead:
    existing = offer_service.find_sintesi_document(db, offer_id)
    document = offer_service.create_sintesi_document(db, offer_id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
    return OfferDocumentRead(
        id=document.id,
        offer_id=document.offer_id,
        doc_type=document.doc_type,
        status=document.status,
        updated_at=document.updated_at,
    )
