from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import DocumentTemplate, Segment, Technology, TemplateBlock, TemplateField, Voce
from app.services.seed import seed_definitions


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_seed_creates_definitions() -> None:
    db = make_session()
    seed_definitions(db)
    assert db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == "SINTESI_FISSE"))
    keys = {f.key for f in db.scalars(select(TemplateField)).all()}
    assert {"nome_offerta", "servizi", "velocita_download", "durata_minima"} <= keys
    blocks = {b.code: b for b in db.scalars(select(TemplateBlock)).all()}
    assert blocks["prezzo"].layout == "2_col"
    assert blocks["costi"].layout == "1_col"
    labels = {v.label for v in db.scalars(select(Voce)).all()}
    assert {"Costo mensile", "Costo SIM", "Modem"} <= labels


def test_seed_is_idempotent() -> None:
    db = make_session()
    seed_definitions(db)
    seed_definitions(db)
    assert len(db.scalars(select(Segment)).all()) == 4
    assert len(db.scalars(select(Technology)).all()) == 3
