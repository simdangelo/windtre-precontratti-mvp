from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TemplateBlock, Voce
from app.schemas import VoceCreate
from app.services.exceptions import BlockNotFoundError, VoceAlreadyExistsError
from app.services.seed import slugify


def create_voce(db: Session, data: VoceCreate) -> Voce:
    """Crea una voce nuova; il nome è univoco per tabella, senza distinzione
    di maiuscole/minuscole ("MODEM" = "Modem" = "modem")."""
    block = db.get(TemplateBlock, data.block_id)
    if block is None:
        raise BlockNotFoundError("Tabella inesistente")

    label = data.label.strip()
    existing = db.scalar(
        select(Voce).where(
            Voce.block_id == block.id,
            func.lower(Voce.label) == label.lower(),
        )
    )
    if existing is not None:
        raise VoceAlreadyExistsError(
            f'La voce "{existing.label}" esiste già in questa tabella'
        )

    code = slugify(label) or "voce"
    if db.scalar(select(Voce).where(Voce.block_id == block.id, Voce.code == code)):
        raise VoceAlreadyExistsError(
            f'Esiste già una voce con un nome equivalente a "{label}"'
        )

    voce = Voce(block_id=block.id, code=code, label=label)
    db.add(voce)
    db.commit()
    db.refresh(voce)
    return voce
