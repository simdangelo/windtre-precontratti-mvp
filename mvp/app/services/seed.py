import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BlockKind,
    Category,
    DocType,
    DocumentTemplate,
    Layout,
    Segment,
    SourceKind,
    Technology,
    TemplateBlock,
    TemplateField,
    Voce,
)

SEGMENTS = [
    ("W3_FIX_GA_CNS", "Fisso GA e Cross Selling Consumer"),
    ("W3_FIX_CB_CNS", "Fisso CB Consumer"),
    ("W3_FIX_GA_MB", "Fisso GA e Cross Selling Microbusiness"),
    ("W3_FIX_CB_MB", "Fisso CB Microbusiness"),
]

TECHNOLOGIES = [
    ("FWA", "FWA Indoor", 300, 50, "templates/bollini/bollino_fwa_fibra_radio.png"),
    ("FTTC", "FTTC", 200, 20, "templates/bollini/bollino_fttc_fibra_rame.png"),
    ("FTTH", "FTTH", 1000, 100, "templates/bollini/bollino_ftth_fibra_verde.png"),
]

FIXED_BLOCKS = [
    ("intestazione", "Intestazione", BlockKind.INTESTAZIONE, [
        ("nome_offerta", "Nome Offerta", SourceKind.OFFER_NAME),
        ("disponibilita", "Disponibilità offerta", SourceKind.INPUT),
    ]),
    ("servizi", "Servizio/i e apparecchiature", BlockKind.TABELLA_FISSA, [
        ("servizi", "Servizi", SourceKind.INPUT),
        ("traffico_internet", "Traffico internet", SourceKind.INPUT),
        ("traffico_fonia", "Traffico fonia", SourceKind.INPUT),
        ("apparecchiature", "Apparecchiature", SourceKind.INPUT),
    ]),
    ("velocita", "Velocità del servizio Internet e mezzi di ricorso", BlockKind.TABELLA_FISSA, [
        ("velocita_download", "Velocità massimo di connessione Internet", SourceKind.TECHNOLOGY),
        ("velocita_upload", "Velocità massimo di connessione Internet", SourceKind.TECHNOLOGY),
    ]),
    ("durata", "Durata, rinnovo e risoluzione", BlockKind.TABELLA_FISSA, [
        ("durata_minima", "Durata minima del contratto del servizio", SourceKind.INPUT),
        ("rinnovo", "Condizioni di rinnovo o risoluzione al termine della durata minima",
         SourceKind.INPUT),
        ("risoluzione_anticipata", "Condizioni risoluzione anticipata, oneri e costi",
         SourceKind.INPUT),
        ("sblocco_apparato", "Condizioni di sblocco dell'apparato", SourceKind.INPUT),
    ]),
]

DYNAMIC_BLOCKS = [
    ("prezzo", "Prezzo", Layout.TWO_COL,
     ["Costo mensile", "Per i già clienti", "Costo SIM", "Rata modem"]),
    ("costi", "Costi", Layout.ONE_COL,
     ["Costo di attivazione", "Modem", "Costo di disattivazione"]),
]


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()


def seed_definitions(db: Session) -> None:
    for code, name in SEGMENTS:
        if not db.scalar(select(Segment).where(Segment.code == code)):
            db.add(Segment(code=code, name=name))
    for code, name, download, upload, badge_path in TECHNOLOGIES:
        if not db.scalar(select(Technology).where(Technology.code == code)):
            db.add(Technology(code=code, name=name, badge_path=badge_path,
                              max_download_mbps=download, max_upload_mbps=upload))
    db.flush()

    template = db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == "SINTESI_FISSE"))
    if template is None:
        template = DocumentTemplate(
            code="SINTESI_FISSE", doc_type=DocType.SINTESI, category=Category.FISSE,
            version=1, file_path="templates/word/sintesi_fisse_template.docx",
        )
        db.add(template)
        db.flush()

    for order, (code, title, kind, fields) in enumerate(FIXED_BLOCKS):
        block = db.scalar(select(TemplateBlock).where(TemplateBlock.code == code))
        if block is None:
            block = TemplateBlock(template_id=template.id, code=code, kind=kind,
                                  title=title, sort_order=order)
            db.add(block)
            db.flush()
        for field_order, (key, label, source) in enumerate(fields):
            if not db.scalar(select(TemplateField).where(TemplateField.key == key)):
                db.add(TemplateField(block_id=block.id, key=key, label=label,
                                     source_kind=source, sort_order=field_order))

    for order, (code, title, layout, labels) in enumerate(DYNAMIC_BLOCKS):
        block = db.scalar(select(TemplateBlock).where(TemplateBlock.code == code))
        if block is None:
            block = TemplateBlock(template_id=template.id, code=code,
                                  kind=BlockKind.TABELLA_DINAMICA, layout=layout,
                                  title=title, sort_order=10 + order)
            db.add(block)
            db.flush()
        for label in labels:
            exists = db.scalar(select(Voce).where(Voce.block_id == block.id, Voce.label == label))
            if not exists:
                db.add(Voce(block_id=block.id, code=slugify(label), label=label))

    db.commit()
