from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_definitions


def bootstrap_database(
    db_engine: Engine = engine,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> None:
    """Crea directory, schema e definizioni (idempotente). Sicuro a ogni avvio."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(db_engine)
    with session_factory() as db:
        seed_definitions(db)
