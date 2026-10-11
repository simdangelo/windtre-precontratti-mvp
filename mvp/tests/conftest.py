import os
import tempfile

TMP_DIR = tempfile.mkdtemp(prefix="mvp-test-")
os.environ["MVP_DATABASE_URL"] = f"sqlite:///{TMP_DIR}/test.db"
os.environ["MVP_DATA_DIR"] = TMP_DIR
os.environ["MVP_GENERATED_DIR"] = f"{TMP_DIR}/generated"
os.environ["MVP_WORD_TEMPLATE_PATH"] = "templates/word/sintesi_fisse_template.docx"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    BulkOperation,
    BulkOperationItem,
    BulkOperationTarget,
    DocumentTemplate,
    GeneratedDocument,
    Offer,
    OfferDocument,
    OfferFieldValue,
    OfferRow,
    Segment,
    Technology,
    TemplateBlock,
    TemplateField,
    Voce,
)
from app.services.seed import seed_definitions  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(setup_database: None) -> Generator:
    session = SessionLocal()
    for model in (
        BulkOperationItem, BulkOperationTarget, BulkOperation,
        GeneratedDocument, OfferRow, OfferFieldValue, OfferDocument, Offer,
        Voce, TemplateField, TemplateBlock, DocumentTemplate, Technology, Segment,
    ):
        session.execute(delete(model))
    session.commit()
    seed_definitions(session)
    yield session
    session.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def segment_id(db_session) -> str:
    segment = db_session.scalar(select(Segment).where(Segment.code == "W3_FIX_CB_CNS"))
    assert segment is not None
    return str(segment.id)


@pytest.fixture
def technology_id(db_session) -> str:
    tech = db_session.scalar(select(Technology).where(Technology.code == "FWA"))
    assert tech is not None
    return str(tech.id)


def create_offer_only(client: TestClient, name: str, segment_id: str, technology_id: str) -> str:
    """Crea l'offerta senza documento Sintesi."""
    response = client.post(
        "/offers",
        data={"name": name, "segment_id": segment_id, "technology_id": technology_id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.headers["location"].rsplit("/", 1)[-1]


def create_offer(client: TestClient, name: str, segment_id: str, technology_id: str) -> str:
    """Crea l'offerta e il documento Sintesi (caso normale dei test)."""
    offer_id = create_offer_only(client, name, segment_id, technology_id)
    response = client.post(f"/offers/{offer_id}/sintesi", follow_redirects=False)
    assert response.status_code == 303
    return offer_id
