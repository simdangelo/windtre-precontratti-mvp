import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import templates
from app.database import get_db
from app.models import Offer
from app.schemas import OfferCreate
from app.services import catalog as catalog_service
from app.services import detail as detail_service
from app.services import offer as offer_service
from app.services import sintesi as sintesi_service
from app.services.exceptions import DuplicateNameError

router = APIRouter()


def _sintesi_json(data: sintesi_service.SintesiData) -> str:
    return json.dumps(sintesi_service.sintesi_to_json(data)).replace("<", "\\u003c")


@router.get("/", response_class=HTMLResponse)
def offers_list(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "offers_list.html",
        {"overviews": offer_service.list_offers_overview(db), "title": "Offerte",
         "active": "offers"},
    )


@router.get("/bulk", response_class=HTMLResponse)
def bulk_page(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    offers = list(db.scalars(select(Offer).order_by(Offer.name)).all())
    data = sintesi_service.get_sintesi_template_data(db)
    return templates.TemplateResponse(
        request, "bulk.html",
        {"offers": offers, "data": data,
         "technologies": catalog_service.list_technologies(db),
         "title": "Modifica massiva", "active": "bulk"},
    )


@router.post("/offers/{offer_id}/sintesi")
def sintesi_create(
    offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> RedirectResponse:
    offer_service.create_sintesi_document(db, offer_id)
    return RedirectResponse(url=f"/offers/{offer_id}", status_code=303)


@router.get("/offers/new", response_class=HTMLResponse)
def offer_new(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    data = sintesi_service.get_sintesi_template_data(db)
    return templates.TemplateResponse(
        request, "offer_new.html",
        {"segments": catalog_service.list_segments(db),
         "technologies": catalog_service.list_technologies(db),
         "data": data, "sintesi_json": _sintesi_json(data),
         "title": "Nuova offerta"},
    )


@router.get("/offers/{offer_id}", response_class=HTMLResponse)
def offer_detail(
    request: Request, offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    detail = detail_service.get_offer_detail(db, offer_id)
    offer = detail.offer
    return templates.TemplateResponse(
        request, "offer_detail.html",
        {"data": detail.sintesi, "category": offer.category,
         "segment_name": detail.segment_name,
         "technologies": catalog_service.list_technologies(db),
         "updated_at": offer.updated_at,
         "current_doc": detail.current_document,
         "previous_docs": detail.previous_documents,
         "sintesi_stale": detail.sintesi_stale,
         "sintesi_json": _sintesi_json(detail.sintesi),
         "title": offer.name},
    )


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


@router.post("/offers")
def offer_create(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str, Form()],
    segment_id: Annotated[uuid.UUID, Form()],
    technology_id: Annotated[uuid.UUID | None, Form()] = None,
) -> Response:
    try:
        offer = offer_service.create_offer(
            db, OfferCreate(name=name, segment_id=segment_id, technology_id=technology_id)
        )
    except DuplicateNameError as exc:
        data = sintesi_service.get_sintesi_template_data(db)
        return templates.TemplateResponse(
            request, "offer_new.html",
            {"segments": catalog_service.list_segments(db),
             "technologies": catalog_service.list_technologies(db),
             "data": data, "sintesi_json": _sintesi_json(data),
             "title": "Nuova offerta", "active": "offers", "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/offers/{offer.id}", status_code=303)
