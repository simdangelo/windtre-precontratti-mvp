from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import bootstrap_database
from app.models import Segment


def test_bootstrap_creates_tables_and_seeds(tmp_path) -> None:
    db_path = tmp_path / "boot.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    test_factory: sessionmaker[Session] = sessionmaker(
        bind=test_engine, autoflush=False, expire_on_commit=False
    )
    bootstrap_database(test_engine, test_factory)
    with test_factory() as db:
        assert db.scalar(select(Segment)) is not None
