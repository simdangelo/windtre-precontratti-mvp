import uuid

import pytest

from app.models import Technology
from app.services import catalog as catalog_service
from app.services.exceptions import DocumentNotFoundError, TechnologyNotFoundError


def test_catalog_lists_technologies_and_segments(db_session) -> None:
    technologies = catalog_service.list_technologies(db_session)
    codes = [t.code for t in technologies]
    assert "FWA" in codes
    names = [t.name for t in technologies]
    assert names == sorted(names)

    segments = catalog_service.list_segments(db_session)
    assert any(s.code == "W3_FIX_CB_CNS" for s in segments)


def test_catalog_badge_path(db_session, technology_id: str) -> None:
    path = catalog_service.get_technology_badge_path(db_session, uuid.UUID(technology_id))
    assert path.is_file()
    assert path.suffix == ".png"


def test_catalog_badge_missing_raises(db_session) -> None:
    with pytest.raises(TechnologyNotFoundError):
        catalog_service.get_technology_badge_path(db_session, uuid.uuid4())


def test_catalog_document_path_missing_raises(db_session) -> None:
    with pytest.raises(DocumentNotFoundError):
        catalog_service.get_generated_document_path(db_session, uuid.uuid4())


def test_catalog_badge_without_path_raises(db_session) -> None:
    technology = Technology(code="NO_BADGE", name="Senza bollino",
                            badge_path=None, max_download_mbps=1, max_upload_mbps=1)
    db_session.add(technology)
    db_session.commit()
    with pytest.raises(TechnologyNotFoundError) as excinfo:
        catalog_service.get_technology_badge_path(db_session, technology.id)
    assert "Bollino non disponibile per la tecnologia" in str(excinfo.value)


def test_catalog_badge_missing_file_raises(db_session) -> None:
    technology = Technology(code="BAD_BADGE", name="Bollino rotto",
                            badge_path="templates/bollini/does_not_exist.png",
                            max_download_mbps=1, max_upload_mbps=1)
    db_session.add(technology)
    db_session.commit()
    with pytest.raises(TechnologyNotFoundError) as excinfo:
        catalog_service.get_technology_badge_path(db_session, technology.id)
    assert "File del bollino non trovato" in str(excinfo.value)


def test_catalog_has_badge(db_session, technology_id: str) -> None:
    technology = db_session.get(Technology, uuid.UUID(technology_id))
    assert technology is not None
    assert catalog_service.has_badge(technology) is True
