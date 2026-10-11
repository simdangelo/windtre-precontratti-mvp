import uuid
from dataclasses import dataclass, field, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BlockKind,
    Category,
    DocType,
    DocumentTemplate,
    Layout,
    Offer,
    OfferFieldValue,
    OfferRow,
    OfferStatus,
    SourceKind,
    Technology,
    TemplateBlock,
    TemplateField,
    Voce,
)
from app.schemas import OfferCreateFull, RowIn, SintesiSaveRequest
from app.services import offer as offer_service
from app.services.exceptions import (
    BlockNotFoundError,
    FieldNotFoundError,
    InvalidRowError,
    OfferNotFoundError,
    TemplateNotFoundError,
    VoceNotFoundError,
)
from app.services.formatting import format_speed


@dataclass(frozen=True)
class FixedField:
    key: str
    label: str
    value_text: str
    source_kind: str
    is_required: bool
    block_code: str
    block_title: str


@dataclass(frozen=True)
class DynamicBlock:
    id: uuid.UUID
    code: str
    title: str
    layout: str


@dataclass(frozen=True)
class RowData:
    id: uuid.UUID
    block_code: str
    parent_row_id: uuid.UUID | None
    voce_id: uuid.UUID
    voce_label: str
    value_text: str
    sort_order: int


@dataclass(frozen=True)
class SintesiData:
    offer_id: uuid.UUID | None
    offer_name: str
    fixed_fields: list[FixedField] = field(default_factory=list)
    dynamic_blocks: list[DynamicBlock] = field(default_factory=list)
    rows: list[RowData] = field(default_factory=list)
    voci: dict[str, list[Voce]] = field(default_factory=dict)
    technology_id: uuid.UUID | None = None
    offer_status: str = OfferStatus.NUOVA.value
    agcom_code: str | None = None

    @property
    def fixed_groups(self) -> list[tuple[str, str, list[FixedField]]]:
        groups: list[tuple[str, str, list[FixedField]]] = []
        by_block: dict[str, list[FixedField]] = {}
        for fixed in self.fixed_fields:
            if fixed.block_code not in by_block:
                by_block[fixed.block_code] = []
                groups.append((fixed.block_code, fixed.block_title, by_block[fixed.block_code]))
            by_block[fixed.block_code].append(fixed)
        return groups


def _definitions(
    db: Session, template_id: uuid.UUID, values: dict[uuid.UUID, str]
) -> tuple[list[FixedField], list[DynamicBlock], dict[str, list[Voce]], dict[uuid.UUID, str]]:
    blocks = list(
        db.scalars(
            select(TemplateBlock)
            .where(TemplateBlock.template_id == template_id)
            .order_by(TemplateBlock.sort_order)
        ).all()
    )
    blocks_by_id = {block.id: block for block in blocks}
    fields = list(
        db.scalars(
            select(TemplateField)
            .join(TemplateBlock, TemplateField.block_id == TemplateBlock.id)
            .where(
                TemplateField.is_active.is_(True),
                TemplateBlock.template_id == template_id,
            )
            .order_by(TemplateBlock.sort_order, TemplateField.sort_order)
        ).all()
    )
    fixed_fields = [
        FixedField(
            key=f.key,
            label=f.label,
            value_text=values.get(f.id, ""),
            source_kind=f.source_kind.value,
            is_required=f.is_required,
            block_code=blocks_by_id[f.block_id].code,
            block_title=blocks_by_id[f.block_id].title,
        )
        for f in fields
    ]
    dynamic_blocks = [
        DynamicBlock(
            id=b.id,
            code=b.code,
            title=b.title,
            layout=(b.layout or Layout.TWO_COL).value,
        )
        for b in blocks
        if b.kind == BlockKind.TABELLA_DINAMICA
    ]
    voci = {
        b.code: list(
            db.scalars(
                select(Voce)
                .where(Voce.block_id == b.id, Voce.is_active.is_(True))
                .order_by(Voce.label)
            ).all()
        )
        for b in blocks
        if b.kind == BlockKind.TABELLA_DINAMICA
    }
    block_codes = {b.id: b.code for b in blocks}
    return fixed_fields, dynamic_blocks, voci, block_codes


def _resolve_derived(
    fields: list[FixedField], offer_name: str, technology: Technology | None
) -> list[FixedField]:
    resolved: list[FixedField] = []
    for fixed in fields:
        if fixed.source_kind == SourceKind.OFFER_NAME.value:
            fixed = replace(fixed, value_text=offer_name)
        elif fixed.source_kind == SourceKind.TECHNOLOGY.value and technology is not None:
            if "download" in fixed.key:
                fixed = replace(
                    fixed, value_text=format_speed(technology.max_download_mbps, "Download")
                )
            else:
                fixed = replace(
                    fixed, value_text=format_speed(technology.max_upload_mbps, "Upload")
                )
        resolved.append(fixed)
    return resolved


def get_sintesi_data(db: Session, offer_id: uuid.UUID) -> SintesiData:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)

    values = {
        value.template_field_id: value.value_text
        for value in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    fixed_fields, dynamic_blocks, voci, block_codes = _definitions(db, doc.template_id, values)
    technology = db.get(Technology, offer.technology_id) if offer.technology_id else None
    fixed_fields = _resolve_derived(fixed_fields, offer.name, technology)
    voci_by_id = {v.id: v for v in db.scalars(select(Voce)).all()}
    rows = [
        RowData(
            id=r.id,
            block_code=block_codes[r.block_id],
            parent_row_id=r.parent_row_id,
            voce_id=r.voce_id,
            voce_label=voci_by_id[r.voce_id].label,
            value_text=r.value_text or "",
            sort_order=r.sort_order,
        )
        for r in db.scalars(
            select(OfferRow)
            .where(OfferRow.offer_document_id == doc.id)
            .order_by(OfferRow.sort_order, OfferRow.id)
        ).all()
    ]
    return SintesiData(
        offer_id=offer.id,
        offer_name=offer.name,
        fixed_fields=fixed_fields,
        dynamic_blocks=dynamic_blocks,
        rows=rows,
        voci=voci,
        technology_id=offer.technology_id,
        offer_status=offer.status.value,
        agcom_code=offer.agcom_code,
    )


def get_sintesi_template_data(db: Session) -> SintesiData:
    template = _active_fisse_template(db)
    fixed_fields, dynamic_blocks, voci, _block_codes = _definitions(db, template.id, {})
    return SintesiData(
        offer_id=None,
        offer_name="",
        fixed_fields=fixed_fields,
        dynamic_blocks=dynamic_blocks,
        rows=[],
        voci=voci,
    )


def sintesi_to_json(data: SintesiData) -> dict[str, object]:
    return {
        "offer_id": str(data.offer_id) if data.offer_id else None,
        "offer_name": data.offer_name,
        "technology_id": str(data.technology_id) if data.technology_id else None,
        "status": data.offer_status,
        "agcom_code": data.agcom_code,
        "fixed_fields": [
            {
                "key": f.key,
                "label": f.label,
                "value": f.value_text,
                "source_kind": f.source_kind,
                "is_required": f.is_required,
                "block_code": f.block_code,
                "block_title": f.block_title,
            }
            for f in data.fixed_fields
        ],
        "derived_fields": [
            {"key": f.key, "label": f.label, "value": f.value_text}
            for f in data.fixed_fields
            if f.source_kind != SourceKind.INPUT.value
        ],
        "blocks": [
            {
                "id": str(b.id),
                "code": b.code,
                "title": b.title,
                "layout": b.layout,
                "voci": [{"id": str(v.id), "label": v.label} for v in data.voci.get(b.code, [])],
            }
            for b in data.dynamic_blocks
        ],
        "rows": [
            {
                "id": str(r.id),
                "block": r.block_code,
                "parent_row_id": str(r.parent_row_id) if r.parent_row_id else None,
                "voce_id": str(r.voce_id),
                "voce_label": r.voce_label,
                "value": r.value_text,
                "sort_order": r.sort_order,
            }
            for r in data.rows
        ],
    }


def _order_rows(rows: list[RowIn]) -> list[RowIn]:
    pending = {row.local_id: row for row in rows}
    ordered: list[RowIn] = []
    while pending:
        ready = [
            row for row in pending.values()
            if not row.parent_local_id
            or any(parent.local_id == row.parent_local_id for parent in ordered)
        ]
        if not ready:
            raise InvalidRowError("Riferimenti padre/figlio incoerenti")
        for row in ready:
            if row.parent_local_id:
                parent = next(p for p in ordered if p.local_id == row.parent_local_id)
                if parent.parent_local_id:
                    raise InvalidRowError("Le tabelle ammettono solo due livelli (padre → figlio)")
            ordered.append(row)
            pending.pop(row.local_id)
    return ordered


def _validate_payload(
    db: Session, template_id: uuid.UUID, data: SintesiSaveRequest
) -> tuple[dict[str, TemplateField], dict[str, TemplateBlock], list[RowIn]]:
    template_blocks = list(
        db.scalars(
            select(TemplateBlock).where(TemplateBlock.template_id == template_id)
        ).all()
    )
    block_ids = [b.id for b in template_blocks]
    fields = {
        f.key: f
        for f in db.scalars(
            select(TemplateField).where(
                TemplateField.block_id.in_(block_ids), TemplateField.is_active.is_(True)
            )
        ).all()
    }
    for key in data.fixed:
        field = fields.get(key)
        if field is None:
            raise FieldNotFoundError(f"Campo '{key}' inesistente")
        if field.source_kind != SourceKind.INPUT:
            raise InvalidRowError(f"Il campo '{key}' non è compilabile")

    blocks = {b.code: b for b in template_blocks if b.kind == BlockKind.TABELLA_DINAMICA}
    ordered = _order_rows(data.rows)
    for row in ordered:
        block = blocks.get(row.block)
        if block is None:
            raise BlockNotFoundError(f"Tabella '{row.block}' inesistente")
        voce = db.get(Voce, row.voce_id)
        if voce is None or voce.block_id != block.id:
            raise VoceNotFoundError(f"Voce {row.voce_id} inesistente per '{row.block}'")
    return fields, blocks, ordered


def _active_fisse_template(db: Session) -> DocumentTemplate:
    template = db.scalar(
        select(DocumentTemplate).where(
            DocumentTemplate.doc_type == DocType.SINTESI,
            DocumentTemplate.category == Category.FISSE,
            DocumentTemplate.is_active.is_(True),
        )
    )
    if template is None:
        raise TemplateNotFoundError("Nessun template SINTESI attivo per la categoria FISSE")
    return template


def create_offer_with_sintesi(db: Session, data: OfferCreateFull) -> Offer:
    template = _active_fisse_template(db)
    payload = SintesiSaveRequest(fixed=data.fixed, rows=data.rows)
    _validate_payload(db, template.id, payload)
    offer = offer_service.create_offer(db, data)
    offer_service.create_sintesi_document(db, offer.id)
    save_sintesi(db, offer.id, payload)
    return offer


def _validate_metadata(db: Session, data: SintesiSaveRequest) -> None:
    if (
        "technology_id" in data.model_fields_set
        and data.technology_id is not None
        and db.get(Technology, data.technology_id) is None
    ):
        raise OfferNotFoundError("Tecnologia inesistente")


def _apply_offer_metadata(db: Session, offer: Offer, data: SintesiSaveRequest) -> None:
    provided = data.model_fields_set
    if "name" in provided and data.name is not None:
        offer_service.rename_offer(db, offer, data.name)
    if "technology_id" in provided:
        offer.technology_id = data.technology_id
    if "agcom_code" in provided:
        offer.agcom_code = data.agcom_code.strip() or None
    if "status" in provided and data.status is not None:
        offer.status = data.status


def save_sintesi(db: Session, offer_id: uuid.UUID, data: SintesiSaveRequest) -> None:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)
    fields, blocks, ordered = _validate_payload(db, doc.template_id, data)
    _validate_metadata(db, data)

    existing_values = {
        v.template_field_id: v
        for v in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    for key, template_field in fields.items():
        if template_field.source_kind != SourceKind.INPUT:
            continue
        value = (data.fixed.get(key) or "").strip()
        existing = existing_values.get(template_field.id)
        if value and existing is None:
            db.add(OfferFieldValue(offer_document_id=doc.id,
                                   template_field_id=template_field.id, value_text=value))
        elif value and existing is not None and existing.value_text != value:
            existing.value_text = value
        elif not value and existing is not None:
            db.delete(existing)

    for old in db.scalars(
        select(OfferRow).where(OfferRow.offer_document_id == doc.id)
    ).all():
        db.delete(old)
    db.flush()

    rows_by_local: dict[str, OfferRow] = {}
    for order, row in enumerate(ordered):
        row_obj = OfferRow(
            offer_document_id=doc.id,
            block_id=blocks[row.block].id,
            parent_row_id=rows_by_local[row.parent_local_id].id if row.parent_local_id else None,
            voce_id=row.voce_id,
            value_text=row.value.strip() or None,
            sort_order=order,
        )
        db.add(row_obj)
        db.flush()
        rows_by_local[row.local_id] = row_obj

    _apply_offer_metadata(db, offer, data)
    offer_service.touch(db, offer, doc)
    db.commit()
