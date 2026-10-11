from app.config import settings


def test_settings_have_defaults() -> None:
    assert settings.database_url.startswith("sqlite:///")
    assert settings.word_template_path.name == "sintesi_fisse_template.docx"


def test_get_db_yields_session() -> None:
    from app.database import get_db

    generator = get_db()
    session = next(generator)
    assert session is not None
    generator.close()
