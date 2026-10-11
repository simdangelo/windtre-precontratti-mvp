from enum import StrEnum

from sqlalchemy import Enum


class Category(StrEnum):
    FISSE = "fisse"
    MOBILE = "mobile"
    VERY = "very"


class DocType(StrEnum):
    SINTESI = "sintesi"
    TRASPARENZA = "trasparenza"


class OfferStatus(StrEnum):
    NUOVA = "nuova"
    APERTA = "aperta"
    CHIUSA = "chiusa"


class BlockKind(StrEnum):
    INTESTAZIONE = "intestazione"
    TABELLA_FISSA = "tabella_fissa"
    TABELLA_DINAMICA = "tabella_dinamica"
    TESTO = "testo"


class Layout(StrEnum):
    ONE_COL = "1_col"
    TWO_COL = "2_col"


class SourceKind(StrEnum):
    INPUT = "input"
    OFFER_NAME = "offer_name"
    TECHNOLOGY = "technology"
    COSTANTE = "costante"


class Outcome(StrEnum):
    DA_MODIFICARE = "da_modificare"
    INVARIATA = "invariata"
    SALTATA_ASSENTE = "saltata_assente"
    APPLICATA = "applicata"
    FALLITA = "fallita"


class BulkTargetKind(StrEnum):
    TEMPLATE_FIELD = "template_field"
    VOCE = "voce"
    TECHNOLOGY = "technology"


class BulkStatus(StrEnum):
    ANTEPRIMA = "anteprima"
    APPLICATA = "applicata"
    ANNULLATA = "annullata"


def enum_col(enum_cls: type[StrEnum], name: str, length: int = 32) -> Enum:
    return Enum(
        enum_cls, name=name, native_enum=False, length=length,
        values_callable=lambda e: [m.value for m in e],
    )
