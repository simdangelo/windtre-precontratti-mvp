import uuid
from datetime import UTC, datetime
from pathlib import Path

from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage, RichText
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    BlockKind,
    GeneratedDocument,
    Layout,
    OfferFieldValue,
    OfferRow,
    SourceKind,
    Technology,
    TemplateBlock,
    TemplateField,
    Voce,
)
from app.services import offer as offer_service
from app.services.exceptions import GenerationError
from app.services.formatting import format_speed


def build_context(db: Session, offer_id: uuid.UUID) -> dict[str, object]:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)
    technology = db.get(Technology, offer.technology_id) if offer.technology_id else None

    template_blocks = db.scalars(
        select(TemplateBlock).where(TemplateBlock.template_id == doc.template_id)
    ).all()
    block_ids = [b.id for b in template_blocks]
    fields = db.scalars(
        select(TemplateField).where(
            TemplateField.block_id.in_(block_ids), TemplateField.is_active.is_(True)
        )
    ).all()
    values = {
        v.template_field_id: v.value_text
        for v in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    campo: dict[str, str] = {}
    for field in fields:
        if field.source_kind == SourceKind.OFFER_NAME:
            campo[field.key] = offer.name
        elif field.source_kind == SourceKind.TECHNOLOGY:
            if technology is None:
                campo[field.key] = ""
            elif "download" in field.key:
                campo[field.key] = format_speed(technology.max_download_mbps, "Download")
            else:
                campo[field.key] = format_speed(technology.max_upload_mbps, "Upload")
        else:
            campo[field.key] = values.get(field.id, "")
    context: dict[str, object] = {
        "campo": campo,
        "bollino": technology.badge_path if technology and technology.badge_path else "",
    }

    blocks = db.scalars(
        select(TemplateBlock)
        .where(
            TemplateBlock.template_id == doc.template_id,
            TemplateBlock.kind == BlockKind.TABELLA_DINAMICA,
        )
        .order_by(TemplateBlock.sort_order)
    ).all()
    voci = {v.id: v for v in db.scalars(select(Voce)).all()}

    for block in blocks:
        rows = db.scalars(
            select(OfferRow)
            .where(OfferRow.offer_document_id == doc.id, OfferRow.block_id == block.id)
            .order_by(OfferRow.sort_order, OfferRow.id)
        ).all()
        children: dict[uuid.UUID, list[OfferRow]] = {}
        parents: list[OfferRow] = []
        for row in rows:
            if row.parent_row_id:
                children.setdefault(row.parent_row_id, []).append(row)
            else:
                parents.append(row)

        rendered: list[dict[str, object]] = []
        if block.layout == Layout.TWO_COL:
            for parent in parents:
                rendered.append(
                    {"etichetta": RichText(voci[parent.voce_id].label, bold=True),
                     "valore": parent.value_text or ""}
                )
                for child in children.get(parent.id, []):
                    rendered.append(
                        {"etichetta": RichText(voci[child.voce_id].label),
                         "valore": child.value_text or ""}
                    )
        else:
            for parent in parents:
                rendered.append({"testo": RichText(voci[parent.voce_id].label, bold=True)})
                if parent.value_text:
                    rendered.append({"testo": RichText(parent.value_text)})
                for child in children.get(parent.id, []):
                    rendered.append({"testo": RichText(voci[child.voce_id].label)})
                    if child.value_text:
                        rendered.append({"testo": RichText(child.value_text)})
        context[block.code] = {"righe": rendered}
    return context


def _naive(value: datetime) -> datetime:
    """SQLite restituisce datetime senza timezone: normalizza per confronti."""
    return value.replace(tzinfo=None) if value.tzinfo else value


def render_sintesi(
    db: Session, offer_id: uuid.UUID, force: bool = False
) -> tuple[GeneratedDocument, bool]:
    """Genera il DOCX. Se la Sintesi corrente è già aggiornata (nessuna
    modifica successiva) non crea un nuovo file, salvo `force=True`.
    Ritorna (documento, generato_nuovo)."""
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)
    template_path = Path(settings.word_template_path)
    if not template_path.is_file():
        raise GenerationError(f"Template Word non trovato: {template_path}")

    current = db.scalar(
        select(GeneratedDocument)
        .where(
            GeneratedDocument.offer_document_id == doc.id,
            GeneratedDocument.is_current.is_(True),
        )
        .order_by(GeneratedDocument.generated_at.desc())
    )
    if (
        not force
        and current is not None
        and _naive(current.generated_at) >= _naive(doc.updated_at)
    ):
        return current, False

    context = build_context(db, offer_id)
    try:
        template = DocxTemplate(str(template_path))
        badge_path = context.get("bollino")
        if isinstance(badge_path, str) and badge_path:
            if Path(badge_path).is_file():
                context["bollino"] = InlineImage(
                    template, badge_path, width=Cm(0.53), height=Cm(0.53)
                )
            else:
                context["bollino"] = ""
        template.render(context)
    except Exception as exc:
        raise GenerationError(f"Errore nel rendering: {exc}") from exc

    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in offer.name).strip("_")
    file_path = settings.generated_dir / f"{safe_name}_sintesi_{timestamp}.docx"
    template.save(str(file_path))

    for previous in db.scalars(
        select(GeneratedDocument).where(
            GeneratedDocument.offer_document_id == doc.id,
            GeneratedDocument.is_current.is_(True),
        )
    ).all():
        previous.is_current = False

    generated = GeneratedDocument(
        offer_document_id=doc.id, template_id=doc.template_id,
        file_type="docx", file_path=str(file_path), is_current=True,
    )
    db.add(generated)
    db.commit()
    db.refresh(generated)
    return generated, True
