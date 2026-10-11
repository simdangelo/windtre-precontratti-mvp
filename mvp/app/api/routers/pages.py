import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import templates
from app.database import get_db
from app.models import (
    GeneratedDocument,
    Offer,
    Segment,
    Technology,
)
from app.schemas import OfferCreate
from app.services import offer as offer_service
from app.services import sintesi as sintesi_service
from app.services.exceptions import (
    DocumentNotFoundError,
    DuplicateNameError,
    TechnologyNotFoundError,
)

router = APIRouter()


def _sintesi_json(data: sintesi_service.SintesiData) -> str:
    return json.dumps(sintesi_service.sintesi_to_json(data)).replace("<", "\\u003c")


def _naive(value: datetime) -> datetime:
    """SQLite restituisce datetime senza timezone: normalizza per confronti."""
    return value.replace(tzinfo=None) if value.tzinfo else value


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
         "technologies": db.scalars(select(Technology).order_by(Technology.name)).all(),
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
        {"segments": db.scalars(select(Segment)).all(),
         "technologies": db.scalars(select(Technology)).all(),
         "data": data, "sintesi_json": _sintesi_json(data),
         "title": "Nuova offerta"},
    )


@router.get("/offers/{offer_id}", response_class=HTMLResponse)
def offer_detail(
    request: Request, offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    offer = offer_service.get_offer(db, offer_id)
    # Il documento Sintesi nasce (get-or-create) al primo accesso all'editor;
    # il tasto "Crea Sintesi" in elenco resta per la creazione esplicita.
    doc = offer_service.create_sintesi_document(db, offer_id)
    data = sintesi_service.get_sintesi_data(db, offer_id)
    generated_docs = list(
        db.scalars(
            select(GeneratedDocument)
            .where(GeneratedDocument.offer_document_id == doc.id)
            .order_by(GeneratedDocument.generated_at.desc())
        ).all()
    )
    segment = db.get(Segment, offer.segment_id)
    current_doc = next((g for g in generated_docs if g.is_current), None)
    previous_docs = [g for g in generated_docs if not g.is_current]
    sintesi_stale = (
        current_doc is not None
        and _naive(doc.updated_at) > _naive(current_doc.generated_at)
    )
    return templates.TemplateResponse(
        request, "offer_detail.html",
        {"data": data, "category": offer.category,
         "segment_name": segment.name if segment else "—",
         "technologies": db.scalars(select(Technology)).all(),
         "updated_at": offer.updated_at,
         "current_doc": current_doc,
         "previous_docs": previous_docs,
         "sintesi_stale": sintesi_stale,
         "sintesi_json": _sintesi_json(data),
         "title": offer.name},
    )


@router.get("/technologies/{technology_id}/badge")
def technology_badge(
    technology_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    technology = db.get(Technology, technology_id)
    if technology is None or not technology.badge_path:
        raise TechnologyNotFoundError("Bollino non disponibile per la tecnologia")
    path = Path(technology.badge_path)
    if not path.is_file():
        raise TechnologyNotFoundError("File del bollino non trovato")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.get("/documents/{document_id}/download")
def document_download(
    document_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    document = db.get(GeneratedDocument, document_id)
    if document is None:
        raise DocumentNotFoundError("Documento non trovato")
    return FileResponse(
        document.file_path,
        media_type=("application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"),
        filename=document.file_path.rsplit("/", 1)[-1],
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
            {"segments": db.scalars(select(Segment)).all(),
             "technologies": db.scalars(select(Technology)).all(),
             "data": data, "sintesi_json": _sintesi_json(data),
             "title": "Nuova offerta", "active": "offers", "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/offers/{offer.id}", status_code=303)
