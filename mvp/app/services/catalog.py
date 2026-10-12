import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GeneratedDocument, Segment, Technology
from app.services.exceptions import DocumentNotFoundError, TechnologyNotFoundError

PNG_MEDIA_TYPE = "image/png"
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def list_technologies(db: Session) -> list[Technology]:
    return list(db.scalars(select(Technology).order_by(Technology.name)).all())


def list_segments(db: Session) -> list[Segment]:
    return list(db.scalars(select(Segment).order_by(Segment.name)).all())


def _badge_file(technology: Technology) -> Path | None:
    if not technology.badge_path:
        return None
    path = Path(technology.badge_path)
    return path if path.is_file() else None


def get_technology_badge_path(db: Session, technology_id: uuid.UUID) -> Path:
    technology = db.get(Technology, technology_id)
    if technology is None or not technology.badge_path:
        raise TechnologyNotFoundError("Bollino non disponibile per la tecnologia")
    path = Path(technology.badge_path)
    if not path.is_file():
        raise TechnologyNotFoundError("File del bollino non trovato")
    return path


def has_badge(technology: Technology) -> bool:
    return _badge_file(technology) is not None


def get_generated_document_path(db: Session, document_id: uuid.UUID) -> Path:
    document = db.get(GeneratedDocument, document_id)
    if document is None:
        raise DocumentNotFoundError("Documento non trovato")
    path = Path(document.file_path)
    if not path.is_file():
        raise DocumentNotFoundError("File del documento non trovato")
    return path
