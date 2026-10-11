# MVP Sintesi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Web app MVP (FastAPI + SQLAlchemy + Pydantic, SQLite) per creare offerte Fisse, compilare la Sintesi (campi fissi + tabelle dinamiche Prezzo 2 colonne e Costi 1 colonna con dizionario delle voci), generare il DOCX dal template `sintesi_fisse_template.docx` e applicare modifiche massive sulla Sintesi con anteprima.

**Architecture:** Layered semplice (`api/` → `services/` → `models/`), come da `../docs/best-practices`. Router sottili con endpoint JSON per editor e massive; pagine HTML server-rendered con `Jinja2Templates`/`TemplateResponse` nello stile di `admin_dashboard.html` (tema scuro, accento arancione). Nessun repository layer: i servizi usano la `Session` direttamente.

**Tech Stack:** Python 3.13, uv, FastAPI, SQLAlchemy 2.0, Pydantic v2 + pydantic-settings, Jinja2, docxtpl, SQLite, pytest + TestClient, ruff, mypy.

**Deviazioni consapevoli (concordate con lo sviluppatore):**
- DB di sviluppo **e di test su SQLite** (le best-practice suggeriscono Postgres per i test).
- Nessuna autenticazione/RBAC nell'MVP.
- Migrazioni (Alembic) fuori scope: `Base.metadata.create_all`.
- Note delle Sintesi fuori scope (il template di test non ne ha).

**Nota sui commit:** i task NON includono commit; verranno fatti solo se richiesto esplicitamente.

**Riferimenti:**
- Template Word: `templates/word/sintesi_fisse_template.docx` (copiato dal progetto padre).
- Documenti di progetto: `../docs/MVP_Sintesi_Trasparenze.md`, `../docs/MVP_Soluzione_Adottata.md`.
- Best practice: `../docs/best-practices/`.

---

## Decisioni e assunzioni registrate

1. **Offerta** = riga con nome univoco. Il documento `SINTESI` (a DB) **non** nasce con l'offerta: nell'elenco offerte c'è il tasto **"Crea Sintesi"** che lo crea on the fly (come l'app attuale); editor e generazione richiedono il documento. Nessun modello dei punti prezzo.
2. **Tecnologia**: attributo dell'offerta; determina velocità (merge field derivati) e futura immagine bollino.
3. **Tabelle dinamiche**: `Prezzo` (2 colonne) e `Costi` (1 colonna). Nessuna voce obbligatoria; padri e figli composti dall'utente; le etichette passano dal **dizionario delle voci** (menu + "Nuova voce").
4. **Massiva**: bersaglio = campo fisso **o** voce. I bersagli tipici sono i **valori dei padri** nelle tabelle a 1 colonna e i **valori dei padri e dei figli** nelle tabelle a 2 colonne (in pratica: tutte le righe con quella voce, qualunque sia il ruolo). Operazione `SET_VALUE` con opzione "crea se manca"; per la creazione di una voce usata come figlio serve il padre di contesto (indicato nel payload).
5. **Storico**: registro minimo `change_event` + `change_item`.
6. **Seed definizioni** allineato al template Word; **seed voci** inventato (sottoinsieme dal documento reale).
7. **UI**: pagine server-rendered (stile dashboard esistente) + JS vanilla per editor dinamico e massiva; nessun framework frontend.
8. **Generazione**: docxtpl; file in `data/generated/`; naming semplice `<nome>_sintesi_<timestamp>.docx`.

---

## Mappa dei file

```
mvp/
├── pyproject.toml               # uv, deps, ruff, mypy, pytest
├── .env.example
├── .gitignore
├── README.md
├── templates/word/sintesi_fisse_template.docx
├── app/
│   ├── __init__.py
│   ├── main.py                  # assembly, lifespan, error handlers
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # engine, SessionLocal, Base, get_db
│   ├── seed.py                  # python -m app.seed
│   ├── models/                  # un file per tabella
│   │   ├── __init__.py, types.py, segment.py, technology.py,
│   │   ├── document_template.py, template_block.py, template_field.py, voce.py,
│   │   ├── offer.py, offer_document.py, offer_field_value.py, offer_row.py,
│   │   └── bulk_operation.py, generated_document.py, change_event.py
│   ├── schemas/                 # __init__.py, offer.py, sintesi.py, voce.py, bulk.py
│   ├── services/                # __init__.py, exceptions.py, seed.py, offer.py,
│   │   └── sintesi.py, voce.py, generation.py, bulk.py, history.py
│   ├── api/
│   │   ├── __init__.py, dependencies.py
│   │   └── routers/__init__.py, pages.py, api.py
│   └── templates/               # base.html, offers_list.html, offer_new.html,
│       └── offer_detail.html, bulk.html
├── data/                        # SQLite + file generati (gitignored)
└── tests/                       # conftest.py, test_offers.py, test_sintesi.py,
                                 # test_voci.py, test_generation.py, test_bulk.py
```

---

## Task 0: Scaffolding del progetto

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`
- Copy: `../templates/sintesi_fisse_template.docx` → `templates/word/sintesi_fisse_template.docx`

- [ ] **Step 1: Inizializza il progetto uv**

```bash
cd mvp
uv init --bare --python 3.13
uv add fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings jinja2 python-multipart docxtpl
uv add --dev pytest httpx ruff mypy
mkdir -p app/models app/schemas app/services app/api/routers app/templates templates/word data/generated tests
# NOTA: mvp è un progetto STANDALONE. Se uv rileva un workspace nel progetto
# padre, rimuovi il blocco [tool.uv.workspace] dal pyproject del padre e
# verifica che `uv run` da mvp usi mvp/.venv (ed `import app` risolva mvp/app).
```

- [ ] **Step 2: Copia il template Word**

```bash
cp ../templates/sintesi_fisse_template.docx templates/word/sintesi_fisse_template.docx
ls -la templates/word/
```

Expected: il file esiste.

- [ ] **Step 3: Configura i tool in `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["docxtpl.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Crea `.gitignore` e `.env.example`**

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
data/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

`.env.example`:
```
MVP_DATABASE_URL=sqlite:///./data/mvp.db
MVP_DATA_DIR=data
MVP_GENERATED_DIR=data/generated
MVP_WORD_TEMPLATE_PATH=templates/word/sintesi_fisse_template.docx
```

- [ ] **Step 5: Verifica l'ambiente**

```bash
uv run python -c "import fastapi, sqlalchemy, docxtpl; print('ok')"
```

Expected: `ok`.

---

## Task 1: Config e database

**Files:**
- Create: `app/__init__.py` (vuoto), `app/config.py`, `app/database.py`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_smoke.py`:
```python
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
```

- [ ] **Step 2: Esegui e verifica il fallimento**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Implementa `app/config.py`**

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MVP_", extra="ignore")

    app_name: str = "MVP Sintesi & Trasparenze"
    database_url: str = "sqlite:///./data/mvp.db"
    data_dir: Path = Path("data")
    generated_dir: Path = Path("data/generated")
    word_template_path: Path = Path("templates/word/sintesi_fisse_template.docx")


settings = Settings()
```

- [ ] **Step 4: Implementa `app/database.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Esegui i test**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS (2 test).

---

## Task 2: Modelli SQLAlchemy

**Files:**
- Create: `app/models/types.py`, `segment.py`, `technology.py`, `document_template.py`, `template_block.py`, `template_field.py`, `voce.py`, `offer.py`, `offer_document.py`, `offer_field_value.py`, `offer_row.py`, `bulk_operation.py`, `generated_document.py`, `change_event.py`, `app/models/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_models.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Category, DocType, DocumentTemplate, Offer, OfferDocument, Segment, Technology,
)


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_offer_roundtrip() -> None:
    db = make_session()
    segment = Segment(code="W3_FIX_CB_CNS", name="Fisso CB Consumer")
    tech = Technology(code="FWA", name="FWA Indoor", max_download_mbps=300, max_upload_mbps=50)
    template = DocumentTemplate(code="SINTESI_FISSE", doc_type=DocType.SINTESI,
                                category=Category.FISSE, version=1, file_path="x.docx")
    db.add_all([segment, tech, template])
    db.flush()

    offer = Offer(
        name="SUPER Internet Casa 5G",
        name_key="super internet casa 5g",
        category=Category.FISSE,
        segment_id=segment.id,
        technology_id=tech.id,
    )
    db.add(offer)
    db.flush()
    doc = OfferDocument(offer_id=offer.id, doc_type=DocType.SINTESI, template_id=template.id)
    db.add(doc)
    db.commit()

    assert offer.id is not None
    assert doc.offer_id == offer.id
```

- [ ] **Step 2: Esegui e verifica il fallimento**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Implementa `app/models/types.py`**

```python
from enum import StrEnum


class Category(StrEnum):
    FISSE = "fisse"
    MOBILE = "mobile"
    VERY = "very"


class DocType(StrEnum):
    SINTESI = "sintesi"
    TRASPARENZA = "trasparenza"


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
    DA_CREARE = "da_creare"
    APPLICATA = "applicata"
    FALLITA = "fallita"


class BulkTargetKind(StrEnum):
    TEMPLATE_FIELD = "template_field"
    VOCE = "voce"


class BulkOpType(StrEnum):
    SET_VALUE = "set_value"
    ADD_VALUE = "add_value"


class BulkStatus(StrEnum):
    ANTEPRIMA = "anteprima"
    APPLICATA = "applicata"
    ANNULLATA = "annullata"


class EventKind(StrEnum):
    CREATE = "create"
    MANUAL_EDIT = "manual_edit"
    BULK = "bulk"
    GENERATE = "generate"
```

- [ ] **Step 4: Implementa i modelli**

Helper enum (usare in tutti i modelli), con type hints per mypy strict:
```python
from sqlalchemy import Enum


def enum_col(enum_cls: type[StrEnum], name: str, length: int = 32) -> Enum:
    return Enum(
        enum_cls, name=name, native_enum=False, length=length,
        values_callable=lambda e: [m.value for m in e],
    )
```
Nota implementativa: `enum_col` vive in `app/models/types.py` (con `from sqlalchemy import Enum` in testa al file) e viene importato nei modelli.

`app/models/segment.py`:
```python
import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
```

`app/models/technology.py`:
```python
import uuid

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    max_download_mbps: Mapped[int] = mapped_column(Integer)
    max_upload_mbps: Mapped[int] = mapped_column(Integer)
```

`app/models/document_template.py`:
```python
import uuid

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import Category, DocType, enum_col


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    doc_type: Mapped[DocType] = mapped_column(enum_col(DocType, "doc_type"), nullable=False)
    category: Mapped[Category] = mapped_column(enum_col(Category, "category"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
```

`app/models/template_block.py`:
```python
import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import BlockKind, Layout, enum_col


class TemplateBlock(Base):
    __tablename__ = "template_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_templates.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[BlockKind] = mapped_column(enum_col(BlockKind, "block_kind"), nullable=False)
    layout: Mapped[Layout | None] = mapped_column(enum_col(Layout, "layout", 16), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer)
```

`app/models/template_field.py`:
```python
import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import SourceKind, enum_col


class TemplateField(Base):
    __tablename__ = "template_fields"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(200))
    source_kind: Mapped[SourceKind] = mapped_column(
        enum_col(SourceKind, "source_kind"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(default=True)
```

`app/models/voce.py`:
```python
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Voce(Base):
    __tablename__ = "voci"
    __table_args__ = (
        UniqueConstraint("block_id", "code", name="uq_voce_block_code"),
        UniqueConstraint("block_id", "label", name="uq_voce_block_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
```

`app/models/offer.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import Category, enum_col


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[Category] = mapped_column(enum_col(Category, "category"), nullable=False)
    segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("segments.id"))
    technology_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technologies.id"), nullable=True
    )
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

`app/models/offer_document.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import DocType, enum_col


class OfferDocument(Base):
    __tablename__ = "offer_documents"
    __table_args__ = (
        UniqueConstraint("offer_id", "doc_type", name="uq_offer_document_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), index=True)
    doc_type: Mapped[DocType] = mapped_column(enum_col(DocType, "doc_type"), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_templates.id"))
    status: Mapped[str] = mapped_column(String(32), default="bozza")
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

`app/models/offer_field_value.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OfferFieldValue(Base):
    __tablename__ = "offer_field_values"

    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), primary_key=True
    )
    template_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_fields.id"), primary_key=True
    )
    value_text: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

`app/models/offer_row.py`:
```python
import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OfferRow(Base):
    __tablename__ = "offer_rows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_blocks.id"), index=True)
    parent_row_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_rows.id"), nullable=True
    )
    voce_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("voci.id"), index=True)
    value_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
```

`app/models/bulk_operation.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import BulkOpType, BulkStatus, BulkTargetKind, Outcome, enum_col


class BulkOperation(Base):
    __tablename__ = "bulk_operations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_kind: Mapped[BulkTargetKind] = mapped_column(
        enum_col(BulkTargetKind, "bulk_target_kind"), nullable=False
    )
    template_field_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("template_fields.id"), nullable=True
    )
    voce_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voci.id"), nullable=True)
    parent_voce_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voci.id"), nullable=True
    )
    op_type: Mapped[BulkOpType] = mapped_column(
        enum_col(BulkOpType, "bulk_op_type"), nullable=False
    )
    new_value_text: Mapped[str] = mapped_column(String(500))
    create_if_missing: Mapped[bool] = mapped_column(default=False)
    status: Mapped[BulkStatus] = mapped_column(
        enum_col(BulkStatus, "bulk_status"), default=BulkStatus.ANTEPRIMA
    )
    offers_selected_count: Mapped[int] = mapped_column(Integer, default=0)
    offers_changed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BulkOperationTarget(Base):
    __tablename__ = "bulk_operation_targets"

    bulk_operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bulk_operations.id"), primary_key=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), primary_key=True)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offer_documents.id"))
    outcome: Mapped[Outcome] = mapped_column(enum_col(Outcome, "outcome"), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    new_value: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

`app/models/generated_document.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_documents.id"), index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_templates.id"))
    file_type: Mapped[str] = mapped_column(String(16), default="docx")
    file_path: Mapped[str] = mapped_column(String(500))
    is_current: Mapped[bool] = mapped_column(default=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

`app/models/change_event.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import EventKind, enum_col


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[EventKind] = mapped_column(enum_col(EventKind, "event_kind"), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    bulk_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bulk_operations.id"), nullable=True
    )


class ChangeItem(Base):
    __tablename__ = "change_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("change_events.id"), index=True)
    offer_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offer_documents.id"))
    template_field_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("template_fields.id"), nullable=True
    )
    voce_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voci.id"), nullable=True)
    old_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 5: Facciata `app/models/__init__.py`** (ri-esporta tutti i simboli con `__all__`; vedi lista completa nella mappa dei file: `BulkOperation`, `BulkOperationTarget`, `ChangeEvent`, `ChangeItem`, `DocumentTemplate`, `GeneratedDocument`, `Offer`, `OfferDocument`, `OfferFieldValue`, `OfferRow`, `Segment`, `Technology`, `TemplateBlock`, `TemplateField`, `Voce` + enum `BlockKind`, `BulkOpType`, `BulkStatus`, `BulkTargetKind`, `Category`, `DocType`, `EventKind`, `Layout`, `Outcome`, `SourceKind`).

- [ ] **Step 6: Esegui i test**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS.

---

## Task 3: Seed delle definizioni (allineato al template Word)

**Files:**
- Create: `app/services/__init__.py` (vuoto), `app/services/seed.py`, `app/seed.py`
- Test: `tests/test_seed.py`

Definizioni (devono combaciare con i merge field del template):
- **Campi fissi**: `nome_offerta` (OFFER_NAME), `disponibilita` (INPUT); `servizi`, `traffico_internet`, `traffico_fonia`, `apparecchiature` (INPUT); `velocita_download`, `velocita_upload` (TECHNOLOGY); `durata_minima`, `rinnovo`, `risoluzione_anticipata`, `sblocco_apparato` (INPUT).
- **Blocchi dinamici**: `prezzo` (2 colonne) e `costi` (1 colonna).
- **Voci seed**: Prezzo → "Costo mensile", "Per i già clienti", "Costo SIM", "Rata modem"; Costi → "Costo di attivazione", "Modem", "Costo di disattivazione".
- **Segmenti seed** (Fisse): `W3_FIX_GA_CNS`, `W3_FIX_CB_CNS`, `W3_FIX_GA_MB`, `W3_FIX_CB_MB` con nomi estesi.
- **Tecnologie seed**: `FWA` (300/50), `FTTC` (200/20), `FTTH` (1000/100).

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_seed.py`)
```python
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import DocumentTemplate, Segment, TemplateBlock, TemplateField, Technology, Voce
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
```

- [ ] **Step 2: Esegui e verifica il fallimento**

Run: `uv run pytest tests/test_seed.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementa `app/services/seed.py`**
```python
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BlockKind, Category, DocType, DocumentTemplate, Layout, Segment, SourceKind,
    TemplateBlock, TemplateField, Technology, Voce,
)

SEGMENTS = [
    ("W3_FIX_GA_CNS", "Fisso GA e Cross Selling Consumer"),
    ("W3_FIX_CB_CNS", "Fisso CB Consumer"),
    ("W3_FIX_GA_MB", "Fisso GA e Cross Selling Microbusiness"),
    ("W3_FIX_CB_MB", "Fisso CB Microbusiness"),
]

TECHNOLOGIES = [
    ("FWA", "FWA Indoor", 300, 50),
    ("FTTC", "FTTC", 200, 20),
    ("FTTH", "FTTH", 1000, 100),
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
    for code, name, download, upload in TECHNOLOGIES:
        if not db.scalar(select(Technology).where(Technology.code == code)):
            db.add(Technology(code=code, name=name,
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
```

- [ ] **Step 4: Implementa `app/seed.py`**
```python
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_definitions


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_definitions(db)
    print("Seed completato.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Esegui i test**

Run: `uv run pytest tests/test_seed.py -v` → PASS.

---

## Task 4: Eccezioni di dominio e storico minimo

**Files:**
- Create: `app/services/exceptions.py`, `app/services/history.py`
- Test: coperto dai task successivi (nessun test dedicato)

- [ ] **Step 1: Implementa `app/services/exceptions.py`**
```python
class DomainError(Exception):
    """Base per tutti gli errori di dominio."""


class DomainNotFoundError(DomainError):
    pass


class DomainValidationError(DomainError):
    pass


class DuplicateNameError(DomainValidationError):
    pass


class OfferNotFoundError(DomainNotFoundError):
    pass


class DocumentNotFoundError(DomainNotFoundError):
    pass


class TemplateNotFoundError(DomainNotFoundError):
    pass


class BlockNotFoundError(DomainNotFoundError):
    pass


class VoceNotFoundError(DomainNotFoundError):
    pass


class FieldNotFoundError(DomainNotFoundError):
    pass


class BulkOperationNotFoundError(DomainNotFoundError):
    pass


class InvalidRowError(DomainValidationError):
    pass


class GenerationError(DomainError):
    pass
```

- [ ] **Step 2: Implementa `app/services/history.py`**
```python
import uuid

from sqlalchemy.orm import Session

from app.models import ChangeEvent, ChangeItem, EventKind


def record_event(
    db: Session,
    kind: EventKind,
    items: list[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, str | None, str | None]],
    bulk_operation_id: uuid.UUID | None = None,
) -> ChangeEvent:
    """items: (offer_document_id, template_field_id, voce_id, old_value, new_value)"""
    event = ChangeEvent(kind=kind, bulk_operation_id=bulk_operation_id)
    db.add(event)
    db.flush()
    for offer_document_id, field_id, voce_id, old_value, new_value in items:
        db.add(ChangeItem(event_id=event.id, offer_document_id=offer_document_id,
                          template_field_id=field_id, voce_id=voce_id,
                          old_value=old_value, new_value=new_value))
    return event
```

---

## Task 5: Schemas Pydantic

**Files:**
- Create: `app/schemas/__init__.py`, `offer.py`, `sintesi.py`, `voce.py`, `bulk.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_schemas.py`)
```python
import uuid

import pytest
from pydantic import ValidationError

from app.schemas import OfferCreate, RowIn, SintesiSaveRequest, VoceCreate


def test_offer_create_validates_name() -> None:
    with pytest.raises(ValidationError):
        OfferCreate(name="", segment_id=uuid.uuid4())


def test_row_defaults() -> None:
    row = RowIn(block="prezzo", local_id="r1", voce_id=uuid.uuid4())
    assert row.value == ""
    assert row.parent_local_id is None


def test_sintesi_payload() -> None:
    payload = SintesiSaveRequest(
        fixed={"servizi": "Fisso fonia e Internet"},
        rows=[RowIn(block="prezzo", local_id="r1", voce_id=uuid.uuid4())],
    )
    assert payload.fixed["servizi"].startswith("Fisso")


def test_voce_label_not_empty() -> None:
    with pytest.raises(ValidationError):
        VoceCreate(block_id=uuid.uuid4(), label="   ")
```

- [ ] **Step 2: Esegui e verifica il fallimento**

Run: `uv run pytest tests/test_schemas.py -v` → FAIL.

- [ ] **Step 3: Implementa gli schemas**

`app/schemas/offer.py`:
```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Category


class OfferCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    segment_id: uuid.UUID
    technology_id: uuid.UUID | None = None
    category: Category = Category.FISSE


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    segment_id: uuid.UUID
    technology_id: uuid.UUID | None
    row_version: int
    updated_at: datetime
```

`app/schemas/sintesi.py`:
```python
import uuid

from pydantic import BaseModel, Field


class RowIn(BaseModel):
    block: str = Field(min_length=1, max_length=50)
    local_id: str = Field(min_length=1, max_length=36)
    parent_local_id: str | None = None
    voce_id: uuid.UUID
    value: str = Field(default="", max_length=500)


class SintesiSaveRequest(BaseModel):
    fixed: dict[str, str] = Field(default_factory=dict)
    rows: list[RowIn] = Field(default_factory=list)
```

`app/schemas/voce.py`:
```python
import uuid

from pydantic import BaseModel, Field, field_validator


class VoceCreate(BaseModel):
    block_id: uuid.UUID
    label: str = Field(min_length=1, max_length=200)

    @field_validator("label")
    @classmethod
    def strip_and_check(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label vuota")
        return value
```

`app/schemas/bulk.py`:
```python
import uuid

from pydantic import BaseModel, Field, model_validator

from app.models import BulkTargetKind


class BulkRequest(BaseModel):
    target_kind: BulkTargetKind
    template_field_key: str | None = None
    voce_id: uuid.UUID | None = None
    parent_voce_id: uuid.UUID | None = None
    new_value: str = Field(default="", max_length=500)
    offer_ids: list[uuid.UUID] = Field(min_length=1)
    create_if_missing: bool = False

    @model_validator(mode="after")
    def check_target(self) -> "BulkRequest":
        if self.target_kind == BulkTargetKind.TEMPLATE_FIELD and not self.template_field_key:
            raise ValueError("template_field_key obbligatorio per i campi fissi")
        if self.target_kind == BulkTargetKind.VOCE and self.voce_id is None:
            raise ValueError("voce_id obbligatorio per le voci")
        return self


class BulkTargetPreview(BaseModel):
    offer_id: uuid.UUID
    offer_name: str
    outcome: str
    old_value: str | None
    new_value: str


class BulkPreviewResponse(BaseModel):
    operation_id: uuid.UUID
    counts: dict[str, int]
    targets: list[BulkTargetPreview]


class BulkApplyResponse(BaseModel):
    operation_id: uuid.UUID
    counts: dict[str, int]
```

`app/schemas/__init__.py`: ri-esporta `OfferCreate`, `OfferResponse`, `RowIn`,
`SintesiSaveRequest`, `VoceCreate`, `BulkRequest`, `BulkTargetPreview`,
`BulkPreviewResponse`, `BulkApplyResponse` con `__all__`.

- [ ] **Step 4: Esegui i test**

Run: `uv run pytest tests/test_schemas.py -v` → PASS.

---

## Task 6: Servizi Offer + pagine elenco/nuova offerta

**Files:**
- Create: `app/services/offer.py`, `app/api/__init__.py`, `app/api/dependencies.py`, `app/api/routers/__init__.py`, `app/api/routers/pages.py`, `app/api/routers/api.py` (scheletro), `app/main.py`, `app/templates/base.html`, `app/templates/offers_list.html`, `app/templates/offer_new.html`
- Test: `tests/conftest.py`, `tests/test_offers.py`

- [ ] **Step 1: Scrivi `tests/conftest.py`**
```python
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
    BulkOperation, BulkOperationTarget, ChangeEvent, ChangeItem, DocumentTemplate,
    GeneratedDocument, Offer, OfferDocument, OfferFieldValue, OfferRow, Segment,
    Technology, TemplateBlock, TemplateField, Voce,
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
        ChangeItem, ChangeEvent, BulkOperationTarget, BulkOperation,
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
```

- [ ] **Step 2: Scrivi `tests/test_offers.py`**
```python
from fastapi.testclient import TestClient


def test_create_offer_and_list(client: TestClient, segment_id: str, technology_id: str) -> None:
    response = client.post(
        "/offers",
        data={"name": "SUPER Internet Casa 5G", "segment_id": segment_id,
              "technology_id": technology_id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get("/")
    assert "SUPER Internet Casa 5G" in page.text
    assert "Crea Sintesi" in page.text


def test_create_sintesi_from_list(client: TestClient, segment_id: str, technology_id: str) -> None:
    from tests.conftest import create_offer_only

    offer_id = create_offer_only(client, "Offerta Con Sintesi", segment_id, technology_id)
    assert "Crea Sintesi" in client.get("/").text
    create = client.post(f"/offers/{offer_id}/sintesi", follow_redirects=False)
    assert create.status_code == 303
    assert create.headers["location"] == f"/offers/{offer_id}"


def test_duplicate_name_is_rejected(client: TestClient, segment_id: str, technology_id: str) -> None:
    payload = {"name": "Offerta Duplicata", "segment_id": segment_id,
               "technology_id": technology_id}
    assert client.post("/offers", data=payload, follow_redirects=False).status_code == 303
    second = client.post("/offers", data=payload, follow_redirects=False)
    assert second.status_code == 400
    assert "esiste già" in second.text


def test_offer_not_found(client: TestClient) -> None:
    response = client.get("/offers/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

- [ ] **Step 3: Esegui e verifica il fallimento** (`uv run pytest tests/test_offers.py -v` → FAIL).

- [ ] **Step 4: Implementa `app/services/offer.py`**
```python
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, DocType, DocumentTemplate, Offer, OfferDocument, Segment, Technology
from app.schemas import OfferCreate
from app.services.exceptions import (
    DocumentNotFoundError, DuplicateNameError, OfferNotFoundError, TemplateNotFoundError,
)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def create_offer(db: Session, data: OfferCreate) -> Offer:
    if db.get(Segment, data.segment_id) is None:
        raise OfferNotFoundError("Segmento inesistente")
    if data.technology_id and db.get(Technology, data.technology_id) is None:
        raise OfferNotFoundError("Tecnologia inesistente")

    name_key = normalize_name(data.name)
    if db.scalar(select(Offer).where(Offer.name_key == name_key)):
        raise DuplicateNameError(f"Un'offerta con nome '{data.name}' esiste già")

    offer = Offer(name=data.name.strip(), name_key=name_key, category=data.category,
                  segment_id=data.segment_id, technology_id=data.technology_id)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def create_sintesi_document(db: Session, offer_id: uuid.UUID) -> OfferDocument:
    """Crea (on the fly) il documento Sintesi a DB, se non esiste."""
    offer = get_offer(db, offer_id)
    existing = db.scalar(
        select(OfferDocument).where(
            OfferDocument.offer_id == offer.id, OfferDocument.doc_type == DocType.SINTESI
        )
    )
    if existing is not None:
        return existing
    template = db.scalar(
        select(DocumentTemplate).where(
            DocumentTemplate.doc_type == DocType.SINTESI,
            DocumentTemplate.category == Category.FISSE,
            DocumentTemplate.is_active.is_(True),
        )
    )
    if template is None:
        raise TemplateNotFoundError("Nessun template SINTESI attivo per la categoria FISSE")
    doc = OfferDocument(offer_id=offer.id, doc_type=DocType.SINTESI, template_id=template.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@dataclass(frozen=True)
class OfferOverview:
    offer: Offer
    has_sintesi: bool


def list_offers_overview(db: Session) -> list[OfferOverview]:
    offers = list(db.scalars(select(Offer).order_by(Offer.name)).all())
    doc_offer_ids = set(
        db.scalars(
            select(OfferDocument.offer_id).where(OfferDocument.doc_type == DocType.SINTESI)
        ).all()
    )
    return [OfferOverview(offer=o, has_sintesi=o.id in doc_offer_ids) for o in offers]


def list_offers(db: Session) -> list[Offer]:
    return list(db.scalars(select(Offer).order_by(Offer.name)).all())


def get_offer(db: Session, offer_id: uuid.UUID) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise OfferNotFoundError(f"Offerta {offer_id} non trovata")
    return offer


def get_sintesi_document(db: Session, offer_id: uuid.UUID) -> OfferDocument:
    offer = get_offer(db, offer_id)
    doc = db.scalar(
        select(OfferDocument).where(
            OfferDocument.offer_id == offer.id, OfferDocument.doc_type == DocType.SINTESI
        )
    )
    if doc is None:
        raise DocumentNotFoundError(f"Documento Sintesi assente per l'offerta {offer.name}")
    return doc


def touch(db: Session, offer: Offer, doc: OfferDocument) -> None:
    offer.row_version += 1
    offer.updated_at = datetime.now(UTC)
    doc.row_version += 1
    doc.updated_at = datetime.now(UTC)
```

- [ ] **Step 5: Implementa `app/api/dependencies.py`**
```python
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
```

- [ ] **Step 6: Implementa `app/api/routers/pages.py` (parte elenco/creazione)**
```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import templates
from app.database import get_db
from app.models import Segment, Technology
from app.schemas import OfferCreate
from app.services import offer as offer_service
from app.services.exceptions import DuplicateNameError

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def offers_list(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "offers_list.html",
        {"overviews": offer_service.list_offers_overview(db), "title": "Offerte",
         "active": "offers"},
    )


@router.post("/offers/{offer_id}/sintesi")
def sintesi_create(
    offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> RedirectResponse:
    offer_service.create_sintesi_document(db, offer_id)
    return RedirectResponse(url=f"/offers/{offer_id}", status_code=303)


@router.get("/offers/new", response_class=HTMLResponse)
def offer_new(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "offer_new.html",
        {"segments": db.scalars(select(Segment)).all(),
         "technologies": db.scalars(select(Technology)).all(),
         "title": "Nuova offerta", "active": "offers"},
    )


@router.post("/offers")
def offer_create(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str, Form()],
    segment_id: Annotated[uuid.UUID, Form()],
    technology_id: Annotated[uuid.UUID | None, Form()] = None,
) -> Response:
    try:
        offer = offer_service.create_offer(
            db, OfferCreate(name=name, segment_id=segment_id, technology_id=technology_id)
        )
    except DuplicateNameError as exc:
        return templates.TemplateResponse(
            request, "offer_new.html",
            {"segments": db.scalars(select(Segment)).all(),
             "technologies": db.scalars(select(Technology)).all(),
             "title": "Nuova offerta", "active": "offers", "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/offers/{offer.id}", status_code=303)
```

- [ ] **Step 7: Implementa `app/api/routers/api.py` (scheletro)**
```python
from fastapi import APIRouter

router = APIRouter()
```

- [ ] **Step 8: Implementa `app/main.py`**
```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import api, pages
from app.database import engine
from app.services.exceptions import (
    DomainNotFoundError, DomainValidationError, GenerationError,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(title="MVP Sintesi & Trasparenze", lifespan=lifespan)


@app.exception_handler(DomainNotFoundError)
async def not_found_handler(_request: Request, exc: DomainNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DomainValidationError)
async def validation_handler(_request: Request, exc: DomainValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(GenerationError)
async def generation_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
```

- [ ] **Step 9: Implementa `app/templates/base.html`**

Struttura completa (tema scuro come `admin_dashboard.html`): variabili CSS
`--w3-orange #FF6600`, `--w3-dark #121214`, `--w3-gray-dark #1E1E24`,
`--w3-gray-light #2A2A32`, `--w3-border #3A3A45`, `--w3-text-primary #FFF`,
`--w3-text-secondary #A0A0B0`, `--w3-green #39B54A`, `--w3-yellow #FF9E1B`,
`--w3-red #E40046`; font Google `Outfit` (titoli) e `Inter` (testo); header con
titolo `WINDTRE <span>Sintesi</span> — MVP` e nav con link `Offerte` (`/`) e
`Modifica massiva` (`/bulk`), classe `active` passata dal template; container
`max-width:1200px`; classi riusabili: `.card`, `.btn`, `.btn.secondary`,
`.btn.small`, `.error`, `.muted`, `.row-actions`, `.grid`, `.grid.cols-3`;
blocco Jinja `{% block content %}{% endblock %}`.

- [ ] **Step 10: Implementa `app/templates/offers_list.html` e `app/templates/offer_new.html`**

`offers_list.html`: estende base; card "Offerte" con bottone "Nuova offerta";
tabella (Nome, Categoria, Ultima modifica, azioni): per ogni riga `overview`, se
`overview.has_sintesi` link "Apri" → `/offers/{{ overview.offer.id }}`, altrimenti
form `POST /offers/{{ overview.offer.id }}/sintesi` con bottone **"Crea Sintesi"**
(creazione del documento a DB on the fly, come l'app attuale); se vuota, messaggio
"Nessuna offerta. Creane una.".

`offer_new.html`: estende base; card "Nuova offerta" con eventuale `.error`
(`{{ error }}`); form `POST /offers` con campi: `name` (required),
`segment_id` (select dei segmenti), `technology_id` (select con opzione vuota),
submit "Crea offerta".

- [ ] **Step 11: Esegui i test**

Run: `uv run pytest tests/test_offers.py -v` → PASS (3 test).

---

## Task 7: Lettura Sintesi + pagina editor

**Files:**
- Create: `app/services/sintesi.py` (parte lettura), `app/templates/offer_detail.html`
- Modify: `app/api/routers/pages.py` (route `/offers/{offer_id}`)
- Test: `tests/test_sintesi.py` (parte lettura)

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_sintesi.py`)
```python
from fastapi.testclient import TestClient

from tests.conftest import create_offer


def test_editor_shows_definitions_and_voci(
    client: TestClient, segment_id: str, technology_id: str
) -> None:
    offer_id = create_offer(client, "Offerta Editor", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    assert page.status_code == 200
    assert "Servizio/i e apparecchiature" in page.text
    assert "Prezzo" in page.text
    assert "Costi" in page.text
    assert "Costo mensile" in page.text
```

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_sintesi.py -v` → 404).

- [ ] **Step 3: Implementa la parte lettura di `app/services/sintesi.py`**
```python
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BlockKind, Layout, OfferFieldValue, OfferRow, SourceKind, TemplateBlock, TemplateField, Voce,
)
from app.services import offer as offer_service


@dataclass(frozen=True)
class FixedField:
    key: str
    label: str
    value_text: str
    source_kind: str
    is_required: bool


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
    offer_id: uuid.UUID
    offer_name: str
    fixed_fields: list[FixedField] = field(default_factory=list)
    dynamic_blocks: list[DynamicBlock] = field(default_factory=list)
    rows: list[RowData] = field(default_factory=list)
    voci: dict[str, list[Voce]] = field(default_factory=dict)


def get_sintesi_data(db: Session, offer_id: uuid.UUID) -> SintesiData:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)

    blocks = list(
        db.scalars(
            select(TemplateBlock)
            .where(TemplateBlock.template_id == doc.template_id)
            .order_by(TemplateBlock.sort_order)
        ).all()
    )
    fields = list(
        db.scalars(
            select(TemplateField)
            .where(TemplateField.is_active.is_(True))
            .order_by(TemplateField.sort_order)
        ).all()
    )
    values = {
        v.template_field_id: v.value_text
        for v in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    fixed_fields = [
        FixedField(key=f.key, label=f.label, value_text=values.get(f.id, ""),
                   source_kind=f.source_kind.value, is_required=f.is_required)
        for f in fields
    ]
    dynamic_blocks = [
        DynamicBlock(id=b.id, code=b.code, title=b.title,
                     layout=(b.layout or Layout.TWO_COL).value)
        for b in blocks
        if b.kind == BlockKind.TABELLA_DINAMICA
    ]
    block_codes = {b.id: b.code for b in blocks}
    voci_by_id = {v.id: v for v in db.scalars(select(Voce)).all()}
    rows = [
        RowData(id=r.id, block_code=block_codes[r.block_id], parent_row_id=r.parent_row_id,
                voce_id=r.voce_id, voce_label=voci_by_id[r.voce_id].label,
                value_text=r.value_text or "", sort_order=r.sort_order)
        for r in db.scalars(
            select(OfferRow)
            .where(OfferRow.offer_document_id == doc.id)
            .order_by(OfferRow.sort_order, OfferRow.id)
        ).all()
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
    return SintesiData(offer_id=offer.id, offer_name=offer.name, fixed_fields=fixed_fields,
                       dynamic_blocks=dynamic_blocks, rows=rows, voci=voci)


def sintesi_to_json(data: SintesiData) -> dict:
    return {
        "offer_id": str(data.offer_id),
        "offer_name": data.offer_name,
        "fixed_fields": [
            {"key": f.key, "label": f.label, "value": f.value_text,
             "source_kind": f.source_kind, "is_required": f.is_required}
            for f in data.fixed_fields
            if f.source_kind == SourceKind.INPUT.value
        ],
        "derived_fields": [
            {"key": f.key, "label": f.label, "value": f.value_text}
            for f in data.fixed_fields
            if f.source_kind != SourceKind.INPUT.value
        ],
        "blocks": [
            {"id": str(b.id), "code": b.code, "title": b.title, "layout": b.layout,
             "voci": [{"id": str(v.id), "label": v.label} for v in data.voci.get(b.code, [])]}
            for b in data.dynamic_blocks
        ],
        "rows": [
            {"id": str(r.id), "block": r.block_code,
             "parent_row_id": str(r.parent_row_id) if r.parent_row_id else None,
             "voce_id": str(r.voce_id), "voce_label": r.voce_label,
             "value": r.value_text, "sort_order": r.sort_order}
            for r in data.rows
        ],
    }
```

- [ ] **Step 4: Implementa `app/templates/offer_detail.html`**

Struttura (estende `base.html`): card offerta (nome, categoria/segmento/tecnologia,
bottoni "Salva Sintesi" e "Genera DOCX" + `#save-status`); card "Campi fissi" con
`#fixed-fields`; `#dynamic-tables`; card "Documenti generati" con lista dei file
(link `/documents/{{ doc.id }}/download`); script `application/json` con
`sintesi_json`; JS inline che:
1. renderizza i campi fissi (`INPUT` editabili, derivati `disabled`);
2. per ogni blocco dinamico crea una card con titolo, righe e bottoni
   "Aggiungi padre", "Nuova voce…";
3. le righe rigenerate mostrano `voce` (select delle voci), `value` (input),
   "+ figlio" (solo padri), "×";
4. `collectPayload()` costruisce `{fixed, rows:[{block, local_id, parent_local_id,
   voce_id, value}]}` con `local_id` = `id` della riga (o `new-<n>` per nuove);
5. "Salva Sintesi" → `PUT /api/offers/{id}/sintesi` (Task 8);
6. "Genera DOCX" → `POST /api/offers/{id}/generate` (Task 10);
7. "Nuova voce…" → `prompt()` del label + `POST /api/voci` (Task 9), poi
   ricarica.

Il codice JS completo va scritto in questo stesso file; le stringhe UI sono in
italiano. Le nuove righe usano `local_id` generati (`r${Date.now()}`) e i padri
prima dei figli nell'array `rows`.

- [ ] **Step 5: Aggiungi la route pagina in `pages.py`**
```python
import json

from app.services import sintesi as sintesi_service


@router.get("/offers/{offer_id}", response_class=HTMLResponse)
def offer_detail(
    request: Request, offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    from app.models import GeneratedDocument

    offer = offer_service.get_offer(db, offer_id)
    # get-or-create: il documento Sintesi nasce al primo accesso all'editor,
    # così il flusso "Nuova offerta → editor" funziona senza 404.
    # Il tasto "Crea Sintesi" in elenco resta (idempotente) per gli altri casi.
    doc = offer_service.create_sintesi_document(db, offer_id)
    data = sintesi_service.get_sintesi_data(db, offer_id)
    generated_docs = db.scalars(
        select(GeneratedDocument)
        .where(GeneratedDocument.offer_document_id == doc.id)
        .order_by(GeneratedDocument.generated_at.desc())
    ).all()
    segment = db.get(Segment, offer.segment_id)
    technology = db.get(Technology, offer.technology_id) if offer.technology_id else None
    return templates.TemplateResponse(
        request, "offer_detail.html",
        {"data": data, "category": offer.category,
         "segment_name": segment.name if segment else "—",
         "technology_name": technology.name if technology else None,
         "generated_docs": generated_docs,
         "sintesi_json": json.dumps(sintesi_service.sintesi_to_json(data)),
         "title": offer.name, "active": "offers"},
    )
```

- [ ] **Step 6: Esegui i test** (`uv run pytest tests/test_sintesi.py -v` → PASS).

---

## Task 8: Salvataggio Sintesi

**Files:**
- Modify: `app/services/sintesi.py` (aggiungi `save_sintesi`), `app/api/routers/api.py` (endpoint PUT)
- Test: `tests/test_sintesi.py` (aggiungi test)

- [ ] **Step 1: Aggiungi i test che falliscono** (in `tests/test_sintesi.py`)
```python
def test_save_and_read_sintesi(client, segment_id, technology_id, db_session) -> None:
    from sqlalchemy import select

    from app.models import OfferRow, Voce

    offer_id = create_offer(client, "Offerta Save", segment_id, technology_id)
    voce_padre = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    voce_figlio = db_session.scalar(select(Voce).where(Voce.label == "Per i già clienti"))
    payload = {
        "fixed": {"disponibilita": "06-10-2025", "servizi": "Fisso fonia e Internet",
                  "traffico_internet": "Illimitato", "traffico_fonia": "Chiamate illimitate",
                  "apparecchiature": "Modem Wi-Fi 7", "durata_minima": "24 mesi",
                  "rinnovo": "Rinnovo automatico", "risoluzione_anticipata": "Costo previsto",
                  "sblocco_apparato": "Non applicabile"},
        "rows": [
            {"block": "prezzo", "local_id": "p1", "voce_id": str(voce_padre.id), "value": ""},
            {"block": "prezzo", "local_id": "p2", "parent_local_id": "p1",
             "voce_id": str(voce_figlio.id), "value": "20,99 euro/mese"},
        ],
    }
    assert client.put(f"/api/offers/{offer_id}/sintesi", json=payload).status_code == 200
    page = client.get(f"/offers/{offer_id}")
    assert "20,99 euro/mese" in page.text
    rows = db_session.scalars(select(OfferRow)).all()
    assert len(rows) == 2
    assert any(r.parent_row_id is not None for r in rows)


def test_save_rejects_unknown_field(client, segment_id, technology_id) -> None:
    offer_id = create_offer(client, "Offerta Invalid", segment_id, technology_id)
    response = client.put(f"/api/offers/{offer_id}/sintesi",
                          json={"fixed": {"inesistente": "x"}, "rows": []})
    assert response.status_code == 404
```

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_sintesi.py -v` → FAIL).

- [ ] **Step 3: Aggiungi `save_sintesi` a `app/services/sintesi.py`**
```python
from app.models import EventKind, TemplateBlock
from app.schemas import RowIn, SintesiSaveRequest
from app.services.exceptions import (
    BlockNotFoundError, FieldNotFoundError, InvalidRowError, VoceNotFoundError,
)
from app.services.history import record_event


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


def save_sintesi(db: Session, offer_id: uuid.UUID, data: SintesiSaveRequest) -> None:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)

    template_blocks = list(
        db.scalars(
            select(TemplateBlock).where(TemplateBlock.template_id == doc.template_id)
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

    items: list[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, str | None, str | None]] = []

    existing_values = {
        v.template_field_id: v
        for v in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    for key, field in fields.items():
        if field.source_kind != SourceKind.INPUT:
            continue
        value = (data.fixed.get(key) or "").strip()
        existing = existing_values.get(field.id)
        if value and existing is None:
            db.add(OfferFieldValue(offer_document_id=doc.id,
                                   template_field_id=field.id, value_text=value))
            items.append((doc.id, field.id, None, None, value))
        elif value and existing is not None and existing.value_text != value:
            items.append((doc.id, field.id, None, existing.value_text, value))
            existing.value_text = value
        elif not value and existing is not None:
            items.append((doc.id, field.id, None, existing.value_text, None))
            db.delete(existing)

    for old in db.scalars(
        select(OfferRow).where(OfferRow.offer_document_id == doc.id)
    ).all():
        db.delete(old)
        items.append((doc.id, None, old.voce_id, old.value_text, None))
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
        items.append((doc.id, None, row.voce_id, None, row.value.strip() or None))

    offer_service.touch(db, offer, doc)
    record_event(db, EventKind.MANUAL_EDIT, items)
    db.commit()
```

- [ ] **Step 4: Aggiungi l'endpoint in `app/api/routers/api.py`**
```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SintesiSaveRequest
from app.services import sintesi as sintesi_service

router = APIRouter()


@router.put("/offers/{offer_id}/sintesi")
def save_sintesi(
    offer_id: uuid.UUID, data: SintesiSaveRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    sintesi_service.save_sintesi(db, offer_id, data)
    return {"status": "ok"}
```

- [ ] **Step 5: Esegui i test** (`uv run pytest tests/test_sintesi.py -v` → PASS, 3 test).

---

## Task 9: Voci (nuova voce)

**Files:**
- Create: `app/services/voce.py`
- Modify: `app/api/routers/api.py`
- Test: `tests/test_voci.py`

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_voci.py`)
```python
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import TemplateBlock


def _prezzo_block(db_session):
    return db_session.scalar(select(TemplateBlock).where(TemplateBlock.code == "prezzo"))


def test_create_voce(client: TestClient, db_session) -> None:
    response = client.post("/api/voci",
                           json={"block_id": str(_prezzo_block(db_session).id),
                                 "label": "Costo eSIM"})
    assert response.status_code == 201
    assert response.json()["label"] == "Costo eSIM"
    assert response.json()["code"] == "costo_esim"


def test_existing_voce_returns_200(client: TestClient, db_session) -> None:
    block_id = str(_prezzo_block(db_session).id)
    first = client.post("/api/voci", json={"block_id": block_id, "label": "Costo rete"})
    second = client.post("/api/voci", json={"block_id": block_id, "label": "Costo rete"})
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
```

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_voci.py -v` → FAIL).

- [ ] **Step 3: Implementa `app/services/voce.py`**
```python
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TemplateBlock, Voce
from app.schemas import VoceCreate
from app.services.exceptions import BlockNotFoundError
from app.services.seed import slugify


@dataclass(frozen=True)
class VoceResult:
    voce: Voce
    created: bool


def get_or_create_voce(db: Session, data: VoceCreate) -> VoceResult:
    block = db.get(TemplateBlock, data.block_id)
    if block is None:
        raise BlockNotFoundError("Tabella inesistente")
    existing = db.scalar(select(Voce).where(Voce.block_id == block.id, Voce.label == data.label))
    if existing is not None:
        return VoceResult(voce=existing, created=False)

    base_code = slugify(data.label) or "voce"
    code = base_code
    suffix = 2
    while db.scalar(select(Voce).where(Voce.block_id == block.id, Voce.code == code)):
        code = f"{base_code}_{suffix}"
        suffix += 1

    voce = Voce(block_id=block.id, code=code, label=data.label)
    db.add(voce)
    db.commit()
    db.refresh(voce)
    return VoceResult(voce=voce, created=True)
```

- [ ] **Step 4: Aggiungi l'endpoint in `api.py`**
```python
from fastapi import status
from fastapi.responses import JSONResponse

from app.schemas import VoceCreate
from app.services import voce as voce_service


@router.post("/voci")
def create_voce(data: VoceCreate, db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    result = voce_service.get_or_create_voce(db, data)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        content={"id": str(result.voce.id), "label": result.voce.label,
                 "code": result.voce.code},
    )
```

- [ ] **Step 5: Esegui i test** (`uv run pytest tests/test_voci.py -v` → PASS).

---

## Task 10: Generazione DOCX

**Files:**
- Create: `app/services/generation.py`
- Modify: `app/api/routers/api.py` (endpoint generate), `app/api/routers/pages.py` (download)
- Test: `tests/test_generation.py`

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_generation.py`)
```python
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import GeneratedDocument, Voce
from tests.conftest import create_offer


def _payload(db_session) -> dict:
    voce_padre = db_session.scalar(select(Voce).where(Voce.label == "Costo mensile"))
    voce_figlio = db_session.scalar(select(Voce).where(Voce.label == "Per i già clienti"))
    return {
        "fixed": {"disponibilita": "06-10-2025",
                  "servizi": "Fisso fonia e Internet in tecnologia FWA Indoor",
                  "traffico_internet": "Illimitato", "traffico_fonia": "Chiamate illimitate",
                  "apparecchiature": "Modem Wi-Fi 7", "durata_minima": "24 mesi",
                  "rinnovo": "Rinnovo automatico", "risoluzione_anticipata": "Costo previsto",
                  "sblocco_apparato": "Non applicabile"},
        "rows": [
            {"block": "prezzo", "local_id": "p1", "voce_id": str(voce_padre.id), "value": ""},
            {"block": "prezzo", "local_id": "p2", "parent_local_id": "p1",
             "voce_id": str(voce_figlio.id), "value": "20,99 euro/mese"},
            {"block": "costi", "local_id": "c1", "voce_id": str(voce_padre.id), "value": "10 euro"},
        ],
    }


def test_generate_sintesi_docx(client: TestClient, db_session, segment_id, technology_id) -> None:
    offer_id = create_offer(client, "Offerta Da Generare", segment_id, technology_id)
    assert client.put(f"/api/offers/{offer_id}/sintesi", json=_payload(db_session)).status_code == 200

    response = client.post(f"/api/offers/{offer_id}/generate")
    assert response.status_code == 201
    document_id = response.json()["document_id"]

    record = db_session.get(GeneratedDocument, __import__("uuid").UUID(document_id))
    assert record is not None
    path = Path(record.file_path)
    assert path.is_file()

    docx = Document(str(path))
    texts = [cell.text for table in docx.tables for row in table.rows for cell in row.cells]
    assert "Offerta Da Generare" in texts
    assert "06-10-2025" in texts
    assert "20,99 euro/mese" in texts
    assert "Per i già clienti" in texts
    assert "300,00 Mbps in Download" in texts

    download = client.get(f"/documents/{document_id}/download")
    assert download.status_code == 200
    assert "word" in download.headers["content-type"]
```

Nota: il terzo target del payload usa `voce_padre` anche per `costi` (che nel seed
non contiene "Costo mensile"): sostituire con una voce del blocco `costi`
(es. "Costo di attivazione") — la voce sbagliata deve produrre 404/422, quindi
nel test usare `Voce` con `block_id == costi.id`.

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_generation.py -v` → FAIL).

- [ ] **Step 3: Implementa `app/services/generation.py`**
```python
import uuid
from datetime import UTC, datetime
from pathlib import Path

from docxtpl import DocxTemplate, RichText
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    BlockKind, EventKind, GeneratedDocument, Layout, OfferFieldValue, OfferRow,
    SourceKind, Technology, TemplateBlock, TemplateField, Voce,
)
from app.services import offer as offer_service
from app.services.exceptions import GenerationError
from app.services.history import record_event


def format_speed(value: int, direction: str) -> str:
    return f"{value},00 Mbps in {direction}"


def build_context(db: Session, offer_id: uuid.UUID) -> dict[str, object]:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)
    technology = db.get(Technology, offer.technology_id) if offer.technology_id else None

    template_blocks = db.scalars(
        select(TemplateBlock).where(TemplateBlock.template_id == doc.template_id)
    ).all()
    block_ids = [b.id for b in template_blocks]
    fields = db.scalars(
        select(TemplateField).where(
            TemplateField.block_id.in_(block_ids), TemplateField.is_active.is_(True)
        )
    ).all()
    values = {
        v.template_field_id: v.value_text
        for v in db.scalars(
            select(OfferFieldValue).where(OfferFieldValue.offer_document_id == doc.id)
        ).all()
    }
    campo: dict[str, str] = {}
    for field in fields:
        if field.source_kind == SourceKind.OFFER_NAME:
            campo[field.key] = offer.name
        elif field.source_kind == SourceKind.TECHNOLOGY:
            if technology is None:
                campo[field.key] = ""
            elif "download" in field.key:
                campo[field.key] = format_speed(technology.max_download_mbps, "Download")
            else:
                campo[field.key] = format_speed(technology.max_upload_mbps, "Upload")
        else:
            campo[field.key] = values.get(field.id, "")
    context: dict[str, object] = {"campo": campo}

    blocks = db.scalars(
        select(TemplateBlock)
        .where(
            TemplateBlock.template_id == doc.template_id,
            TemplateBlock.kind == BlockKind.TABELLA_DINAMICA,
        )
        .order_by(TemplateBlock.sort_order)
    ).all()
    voci = {v.id: v for v in db.scalars(select(Voce)).all()}

    for block in blocks:
        rows = db.scalars(
            select(OfferRow)
            .where(OfferRow.offer_document_id == doc.id, OfferRow.block_id == block.id)
            .order_by(OfferRow.sort_order, OfferRow.id)
        ).all()
        children: dict[uuid.UUID, list[OfferRow]] = {}
        parents: list[OfferRow] = []
        for row in rows:
            if row.parent_row_id:
                children.setdefault(row.parent_row_id, []).append(row)
            else:
                parents.append(row)

        rendered: list[dict[str, object]] = []
        if block.layout == Layout.TWO_COL:
            for parent in parents:
                rendered.append({"etichetta": RichText(voci[parent.voce_id].label, bold=True),
                                 "valore": parent.value_text or ""})
                for child in children.get(parent.id, []):
                    rendered.append({"etichetta": RichText(voci[child.voce_id].label),
                                     "valore": child.value_text or ""})
        else:
            for parent in parents:
                rendered.append({"testo": RichText(voci[parent.voce_id].label, bold=True)})
                if parent.value_text:
                    rendered.append({"testo": RichText(parent.value_text)})
                for child in children.get(parent.id, []):
                    rendered.append({"testo": RichText(voci[child.voce_id].label)})
                    if child.value_text:
                        rendered.append({"testo": RichText(child.value_text)})
        context[block.code] = {"righe": rendered}
    return context


def render_sintesi(db: Session, offer_id: uuid.UUID) -> GeneratedDocument:
    offer = offer_service.get_offer(db, offer_id)
    doc = offer_service.get_sintesi_document(db, offer_id)
    template_path = Path(settings.word_template_path)
    if not template_path.is_file():
        raise GenerationError(f"Template Word non trovato: {template_path}")

    context = build_context(db, offer_id)
    try:
        template = DocxTemplate(str(template_path))
        template.render(context)
    except Exception as exc:  # noqa: BLE001
        raise GenerationError(f"Errore nel rendering: {exc}") from exc

    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in offer.name).strip("_")
    file_path = settings.generated_dir / f"{safe_name}_sintesi_{timestamp}.docx"
    template.save(str(file_path))

    for previous in db.scalars(
        select(GeneratedDocument).where(
            GeneratedDocument.offer_document_id == doc.id,
            GeneratedDocument.is_current.is_(True),
        )
    ).all():
        previous.is_current = False

    generated = GeneratedDocument(offer_document_id=doc.id, template_id=doc.template_id,
                                  file_type="docx", file_path=str(file_path), is_current=True)
    db.add(generated)
    record_event(db, EventKind.GENERATE, [(doc.id, None, None, None, str(file_path))])
    db.commit()
    db.refresh(generated)
    return generated
```

- [ ] **Step 4: Aggiungi gli endpoint**

In `api.py`:
```python
from fastapi import status

from app.services import generation as generation_service


@router.post("/offers/{offer_id}/generate", status_code=status.HTTP_201_CREATED)
def generate(offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    document = generation_service.render_sintesi(db, offer_id)
    return {"document_id": str(document.id), "file_path": document.file_path}
```

In `pages.py`:
```python
from fastapi.responses import FileResponse

from app.models import GeneratedDocument
from app.services.exceptions import DocumentNotFoundError


@router.get("/documents/{document_id}/download")
def document_download(
    document_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    document = db.get(GeneratedDocument, document_id)
    if document is None:
        raise DocumentNotFoundError("Documento non trovato")
    return FileResponse(
        document.file_path,
        media_type=("application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"),
        filename=document.file_path.rsplit("/", 1)[-1],
    )
```

- [ ] **Step 5: Esegui i test** (`uv run pytest tests/test_generation.py -v` → PASS).

---

## Task 11: Massiva — anteprima

**Files:**
- Create: `app/services/bulk.py`
- Modify: `app/api/routers/api.py` (endpoint preview)
- Test: `tests/test_bulk.py`

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_bulk.py`)
```python
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import OfferRow, TemplateBlock, Voce
from tests.conftest import create_offer


def _voce(db_session, block_code: str, label: str) -> str:
    block = db_session.scalar(select(TemplateBlock).where(TemplateBlock.code == block_code))
    voce = db_session.scalar(select(Voce).where(Voce.block_id == block.id, Voce.label == label))
    assert voce is not None
    return str(voce.id)


def _set_costo_sim(client, db_session, offer_id: str, value: str | None) -> None:
    rows = []
    if value is not None:
        rows = [{"block": "prezzo", "local_id": "x1",
                 "voce_id": _voce(db_session, "prezzo", "Costo SIM"), "value": value}]
    client.put(f"/api/offers/{offer_id}/sintesi", json={"fixed": {}, "rows": rows})


def test_bulk_preview_outcomes(client: TestClient, db_session, segment_id, technology_id) -> None:
    offer_a = create_offer(client, "Bulk A", segment_id, technology_id)
    offer_b = create_offer(client, "Bulk B", segment_id, technology_id)
    offer_c = create_offer(client, "Bulk C", segment_id, technology_id)
    _set_costo_sim(client, db_session, offer_a, "10 euro")
    _set_costo_sim(client, db_session, offer_b, "12 euro")
    _set_costo_sim(client, db_session, offer_c, None)

    response = client.post("/api/bulk/preview", json={
        "target_kind": "voce",
        "voce_id": _voce(db_session, "prezzo", "Costo SIM"),
        "new_value": "12 euro",
        "offer_ids": [offer_a, offer_b, offer_c],
        "create_if_missing": False,
    })
    assert response.status_code == 200
    body = response.json()
    outcomes = {t["offer_name"]: t["outcome"] for t in body["targets"]}
    assert outcomes["Bulk A"] == "da_modificare"
    assert outcomes["Bulk B"] == "invariata"
    assert outcomes["Bulk C"] == "saltata_assente"
    assert body["counts"]["da_modificare"] == 1
```

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_bulk.py -v` → FAIL).

- [ ] **Step 3: Implementa `app/services/bulk.py` (parte anteprima)**
```python
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BulkOperation, BulkOperationTarget, BulkStatus, BulkTargetKind, BulkOpType,
    Offer, OfferFieldValue, OfferRow, Outcome, SourceKind, TemplateField, Voce,
)
from app.schemas import BulkRequest
from app.services import offer as offer_service
from app.services.exceptions import (
    BulkOperationNotFoundError, DomainValidationError, FieldNotFoundError, VoceNotFoundError,
)


@dataclass(frozen=True)
class TargetState:
    offer: Offer
    offer_document_id: uuid.UUID
    outcome: Outcome
    old_value: str | None
    new_value: str
    reason: str | None = None


def _evaluate(db: Session, req: BulkRequest, offer: Offer, document_id: uuid.UUID) -> TargetState:
    if req.target_kind == BulkTargetKind.VOCE:
        rows = db.scalars(
            select(OfferRow).where(
                OfferRow.offer_document_id == document_id,
                OfferRow.voce_id == req.voce_id,
            )
        ).all()
        if not rows:
            outcome = Outcome.DA_CREARE if req.create_if_missing else Outcome.SALTATA_ASSENTE
            return TargetState(offer, document_id, outcome, None, req.new_value)
        if any(r.value_text == req.new_value for r in rows):
            return TargetState(offer, document_id, Outcome.INVARIATA, req.new_value, req.new_value)
        return TargetState(offer, document_id, Outcome.DA_MODIFICARE, rows[0].value_text,
                           req.new_value)

    field = db.scalar(
        select(TemplateField).where(TemplateField.key == req.template_field_key)
    )
    if field is None or field.source_kind != SourceKind.INPUT:
        raise FieldNotFoundError(f"Campo '{req.template_field_key}' non modificabile")
    value = db.scalar(
        select(OfferFieldValue).where(
            OfferFieldValue.offer_document_id == document_id,
            OfferFieldValue.template_field_id == field.id,
        )
    )
    if value is None:
        outcome = Outcome.DA_CREARE if req.create_if_missing else Outcome.SALTATA_ASSENTE
        return TargetState(offer, document_id, outcome, None, req.new_value)
    if value.value_text == req.new_value:
        return TargetState(offer, document_id, Outcome.INVARIATA, req.new_value, req.new_value)
    return TargetState(offer, document_id, Outcome.DA_MODIFICARE, value.value_text, req.new_value)


def _validate_target(db: Session, req: BulkRequest) -> TemplateField | None:
    if req.target_kind == BulkTargetKind.VOCE:
        voce = db.get(Voce, req.voce_id)
        if voce is None or not voce.is_active:
            raise VoceNotFoundError(f"Voce {req.voce_id} inesistente")
        return None
    field = db.scalar(select(TemplateField).where(TemplateField.key == req.template_field_key))
    if field is None or field.source_kind != SourceKind.INPUT:
        raise FieldNotFoundError(f"Campo '{req.template_field_key}' non modificabile")
    return field


def preview_bulk(db: Session, req: BulkRequest) -> tuple[BulkOperation, list[TargetState]]:
    field = _validate_target(db, req)

    states: list[TargetState] = []
    for offer_id in req.offer_ids:
        offer = offer_service.get_offer(db, offer_id)
        doc = offer_service.get_sintesi_document(db, offer_id)
        states.append(_evaluate(db, req, offer, doc.id))

    operation = BulkOperation(
        target_kind=req.target_kind,
        template_field_id=field.id if field else None,
        voce_id=req.voce_id,
        parent_voce_id=req.parent_voce_id,
        op_type=BulkOpType.SET_VALUE,
        new_value_text=req.new_value,
        create_if_missing=req.create_if_missing,
        status=BulkStatus.ANTEPRIMA,
        offers_selected_count=len(req.offer_ids),
        offers_changed_count=sum(
            1 for s in states if s.outcome in (Outcome.DA_MODIFICARE, Outcome.DA_CREARE)
        ),
    )
    db.add(operation)
    db.flush()
    for state in states:
        db.add(BulkOperationTarget(
            bulk_operation_id=operation.id, offer_id=state.offer.id,
            offer_document_id=state.offer_document_id, outcome=state.outcome,
            old_value=state.old_value, new_value=state.new_value, reason=state.reason,
        ))
    db.commit()
    db.refresh(operation)
    return operation, states
```

- [ ] **Step 4: Aggiungi l'endpoint in `api.py`**
```python
from app.schemas import BulkRequest
from app.services import bulk as bulk_service


def _bulk_counts(states) -> dict[str, int]:
    counts: dict[str, int] = {}
    for state in states:
        counts[state.outcome.value] = counts.get(state.outcome.value, 0) + 1
    return counts


@router.post("/bulk/preview")
def bulk_preview(data: BulkRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    operation, states = bulk_service.preview_bulk(db, data)
    return {
        "operation_id": str(operation.id),
        "counts": _bulk_counts(states),
        "targets": [
            {"offer_id": str(s.offer.id), "offer_name": s.offer.name,
             "outcome": s.outcome.value, "old_value": s.old_value, "new_value": s.new_value}
            for s in states
        ],
    }
```

- [ ] **Step 5: Esegui i test** (`uv run pytest tests/test_bulk.py -v` → PASS).

---

## Task 12: Massiva — applicazione + pagina

**Files:**
- Modify: `app/services/bulk.py` (aggiungi `apply_bulk`), `app/api/routers/api.py` (endpoint apply), `app/api/routers/pages.py` (route `/bulk`), `app/templates/bulk.html`
- Test: `tests/test_bulk.py` (aggiungi test)

- [ ] **Step 1: Aggiungi i test che falliscono**
```python
def test_bulk_apply_updates_rows(client: TestClient, db_session, segment_id, technology_id) -> None:
    offer_a = create_offer(client, "Apply A", segment_id, technology_id)
    offer_c = create_offer(client, "Apply C", segment_id, technology_id)
    _set_costo_sim(client, db_session, offer_a, "10 euro")
    voce_id = _voce(db_session, "prezzo", "Costo SIM")

    preview = client.post("/api/bulk/preview", json={
        "target_kind": "voce", "voce_id": voce_id, "new_value": "12 euro",
        "offer_ids": [offer_a, offer_c], "create_if_missing": True,
    }).json()
    response = client.post(f"/api/bulk/{preview['operation_id']}/apply")
    assert response.status_code == 200
    assert response.json()["counts"]["modificate"] == 2

    rows = db_session.scalars(select(OfferRow).where(OfferRow.value_text == "12 euro")).all()
    assert len(rows) == 2  # A aggiornata + C creata
```

- [ ] **Step 2: Esegui e verifica il fallimento** (`uv run pytest tests/test_bulk.py -v` → FAIL).

- [ ] **Step 3: Aggiungi `apply_bulk` in `app/services/bulk.py`**
```python
def apply_bulk(db: Session, operation_id: uuid.UUID) -> dict[str, int]:
    operation = db.get(BulkOperation, operation_id)
    if operation is None:
        raise BulkOperationNotFoundError("Operazione massiva non trovata")
    if operation.status != BulkStatus.ANTEPRIMA:
        raise DomainValidationError("Operazione già applicata o annullata")

    targets = list(
        db.scalars(
            select(BulkOperationTarget).where(
                BulkOperationTarget.bulk_operation_id == operation.id
            )
        ).all()
    )
    counts = {"modificate": 0, "create": 0, "invariate": 0, "saltate": 0}
    # "modificate" = offerte cambiate (update o create); "create" = righe create
    items: list[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, str | None, str | None]] = []

    for target in targets:
        if target.outcome in (Outcome.INVARIATA,):
            counts["invariate"] += 1
            continue
        if target.outcome == Outcome.SALTATA_ASSENTE:
            counts["saltate"] += 1
            continue
        if target.outcome == Outcome.FALLITA:
            counts["saltate"] += 1
            continue

        if operation.target_kind == BulkTargetKind.VOCE:
            if target.outcome == Outcome.DA_CREARE:
                parent_row_id = None
                if operation.parent_voce_id:
                    parent = db.scalar(
                        select(OfferRow).where(
                            OfferRow.offer_document_id == target.offer_document_id,
                            OfferRow.voce_id == operation.parent_voce_id,
                        )
                    )
                    if parent is None:
                        target.outcome = Outcome.FALLITA
                        target.reason = "Padre di contesto assente"
                        counts["saltate"] += 1
                        continue
                    parent_row_id = parent.id
                created = OfferRow(
                    offer_document_id=target.offer_document_id,
                    block_id=db.get(Voce, operation.voce_id).block_id,
                    parent_row_id=parent_row_id, voce_id=operation.voce_id,
                    value_text=operation.new_value_text, sort_order=999,
                )
                db.add(created)
                db.flush()
                items.append((target.offer_document_id, None, operation.voce_id,
                              None, operation.new_value_text))
                counts["create"] += 1
                counts["modificate"] += 1
            else:
                rows = db.scalars(
                    select(OfferRow).where(
                        OfferRow.offer_document_id == target.offer_document_id,
                        OfferRow.voce_id == operation.voce_id,
                    )
                ).all()
                for row in rows:
                    items.append((target.offer_document_id, None, operation.voce_id,
                                  row.value_text, operation.new_value_text))
                    row.value_text = operation.new_value_text
                counts["modificate"] += 1
        else:
            field_id = operation.template_field_id
            value = db.scalar(
                select(OfferFieldValue).where(
                    OfferFieldValue.offer_document_id == target.offer_document_id,
                    OfferFieldValue.template_field_id == field_id,
                )
            )
            if value is None:
                db.add(OfferFieldValue(offer_document_id=target.offer_document_id,
                                       template_field_id=field_id,
                                       value_text=operation.new_value_text))
                items.append((target.offer_document_id, field_id, None,
                              None, operation.new_value_text))
                counts["create"] += 1
                counts["modificate"] += 1
            else:
                items.append((target.offer_document_id, field_id, None,
                              value.value_text, operation.new_value_text))
                value.value_text = operation.new_value_text
                counts["modificate"] += 1

        target.outcome = Outcome.APPLICATA
        offer = db.get(Offer, target.offer_id)
        if offer is not None:
            offer.row_version += 1
            offer.updated_at = datetime.now(UTC)

    operation.status = BulkStatus.APPLICATA
    operation.applied_at = datetime.now(UTC)
    operation.offers_changed_count = counts["modificate"]
    record_bulk_event(db, operation.id, items)
    db.commit()
    return counts
```

`record_bulk_event` (in `bulk.py`, con `from app.models import EventKind` e
`from app.services.history import record_event` in testa al file):
```python
def record_bulk_event(
    db: Session,
    operation_id: uuid.UUID,
    items: list[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, str | None, str | None]],
) -> None:
    record_event(db, EventKind.BULK, items, bulk_operation_id=operation_id)
```

- [ ] **Step 4: Aggiungi l'endpoint in `api.py`**
```python
@router.post("/bulk/{operation_id}/apply")
def bulk_apply(
    operation_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> dict:
    counts = bulk_service.apply_bulk(db, operation_id)
    return {"operation_id": str(operation_id), "counts": counts}
```

- [ ] **Step 5: Aggiungi la route `/bulk` in `pages.py` e `app/templates/bulk.html`**

Route: passa `offers` (tutte), `fields` (campi `INPUT`), `voci` (raggruppate per
blocco dinamico) al template.

`bulk.html` (estende base): form con select "Tipo bersaglio"
(`template_field` / `voce`), select bersaglio popolata via JS in base al tipo,
input valore, checkbox "crea se manca", **select opzionale "Padre di contesto"**
(visibile per il tipo voce quando "crea se manca" è attivo; popolato con le voci
dello stesso blocco del bersaglio; inviato come `parent_voce_id`), lista offerte
con checkbox (tutte selezionate di default), bottone "Anteprima". L'anteprima
(`POST /api/bulk/preview`) renderizza una tabella (Offerta | Valore attuale |
Esito | Nuovo valore) + conteggi, e mostra il bottone "Applica" che chiama
(`POST /api/bulk/{id}/apply`); al termine mostra i conteggi e ricarica la lista
offerte.

- [ ] **Step 6: Esegui i test** (`uv run pytest tests/test_bulk.py -v` → PASS).

---

## Task 13: README, seed reale e verifica finale

**Files:**
- Create: `README.md`
- Test: suite completa

- [ ] **Step 1: Scrivi `README.md`**
```markdown
# MVP Sintesi & Trasparenze

Web app MVP per la compilazione della Sintesi contrattuale di offerte Fisse
(form separato, tavole dinamiche a voci, modifica massiva) e la generazione del
DOCX dal template Word.

## Requisiti
- uv, Python 3.13

## Avvio
```bash
uv sync
uv run python -m app.seed        # definizioni + seed (crea data/mvp.db)
uv run uvicorn app.main:app --reload
# http://localhost:8000
```

## Test
```bash
uv run pytest
uv run ruff check . --fix
uv run mypy app
```

## Struttura
- `app/models/` SQLAlchemy (un file per tabella)
- `app/schemas/` Pydantic (contratto API)
- `app/services/` logica di business
- `app/api/` router FastAPI + pagine Jinja2
- `templates/word/sintesi_fisse_template.docx` template di generazione
```

- [ ] **Step 2: Seed reale**

```bash
uv run python -m app.seed
uv run pytest
```
Expected: i test passano, `data/mvp.db` creato.

- [ ] **Step 3: Smoke test manuale (facoltativo ma consigliato)**

```bash
uv run uvicorn app.main:app --reload
```
Crea un'offerta, compila campi fissi e tabelle dinamiche, salva, genera il DOCX,
scaricalo e verifica il contenuto; poi prova una massiva su una voce.

- [ ] **Step 4: Verifica finale della suite**

```bash
uv run pytest -v
uv run ruff check .
uv run mypy app
```
Expected: tutto verde (mypy strict può richiedere aggiustamenti di annotazioni;
nessun tipo `Any` non giustificato).

---

## Task 14: Nuova offerta a form completo (una sola azione)

**Feedback utente:** da home, "Nuova offerta" deve mostrare **subito tutti i campi** (anagrafica + campi fissi + tabelle dinamiche) e con **una sola azione** creare offerta, documento Sintesi e valori. Niente doppio passaggio.

**Files:**
- Modify: `app/schemas/offer.py` (+ `OfferCreateFull`), `app/schemas/__init__.py`
- Modify: `app/services/sintesi.py` (+ `get_sintesi_template_data`, `create_offer_with_sintesi`, validazione estratta)
- Modify: `app/api/routers/api.py` (+ `POST /api/offers` JSON), `app/api/routers/pages.py` (route `/offers/new` con definizioni complete)
- Create: `app/static/editor.js` (JS dell'editor estratto dal template)
- Modify: `app/templates/offer_detail.html`, `app/templates/offer_new.html`, `app/main.py` (mount `/static`)
- Test: `tests/test_offers.py` (+ 3 test)

- [ ] **Step 1: Scrivi i test che falliscono** (in `tests/test_offers.py`)
```python
def test_new_offer_page_shows_full_form(client: TestClient) -> None:
    page = client.get("/offers/new")
    assert page.status_code == 200
    assert "Nome offerta" in page.text
    assert "Disponibilit" in page.text          # campo fisso nelle definizioni JSON
    assert '"code": "prezzo"' in page.text      # blocco dinamico Prezzo
    assert "editor.js" in page.text


def test_create_offer_full_via_api(client, db_session, segment_id, technology_id) -> None:
    from sqlalchemy import select
    from app.models import Offer, OfferDocument, OfferRow, Voce

    voce = db_session.scalar(select(Voce).where(Voce.label == "Costo SIM"))
    payload = {
        "name": "Offerta Full", "segment_id": segment_id, "technology_id": technology_id,
        "fixed": {"disponibilita": "01-01-2026", "servizi": "Fisso fonia e Internet",
                  "traffico_internet": "Illimitato", "traffico_fonia": "Chiamate illimitate",
                  "apparecchiature": "Modem", "durata_minima": "24 mesi",
                  "rinnovo": "Rinnovo automatico", "risoluzione_anticipata": "Costo",
                  "sblocco_apparato": "Non applicabile"},
        "rows": [{"block": "prezzo", "local_id": "r1",
                  "voce_id": str(voce.id), "value": "10 euro"}],
    }
    response = client.post("/api/offers", json=payload)
    assert response.status_code == 201
    offer_id = response.json()["id"]

    assert client.get(f"/offers/{offer_id}").status_code == 200
    assert db_session.scalar(select(Offer).where(Offer.name == "Offerta Full")) is not None
    assert db_session.scalars(select(OfferDocument)).all()
    assert len(db_session.scalars(select(OfferRow)).all()) == 1


def test_create_offer_full_invalid_creates_nothing(client, db_session, segment_id, technology_id):
    from sqlalchemy import select
    from app.models import Offer

    response = client.post("/api/offers", json={
        "name": "Offerta Ko", "segment_id": segment_id, "technology_id": technology_id,
        "fixed": {"inesistente": "x"}, "rows": [],
    })
    assert response.status_code == 404
    assert db_session.scalar(select(Offer).where(Offer.name == "Offerta Ko")) is None
```

- [ ] **Step 2: Esegui e verifica fallimento** (`uv run pytest tests/test_offers.py -v` → FAIL).

- [ ] **Step 3: Schema `OfferCreateFull`** in `app/schemas/offer.py`
```python
from app.schemas.sintesi import RowIn


class OfferCreateFull(OfferCreate):
    fixed: dict[str, str] = Field(default_factory=dict)
    rows: list[RowIn] = Field(default_factory=list)
```
Esportalo in `app/schemas/__init__.py`.

- [ ] **Step 4: Servizio in `app/services/sintesi.py`**
1. Estrai la validazione oggi dentro `save_sintesi` in:
```python
def _validate_payload(
    db: Session, template_id: uuid.UUID, data: SintesiSaveRequest
) -> tuple[dict[str, TemplateField], dict[str, TemplateBlock], list[RowIn]]:
    # blocco attuale: template_blocks/fields filtrati, controlli fixed, block, voce, _order_rows
    # ritorna (fields, blocks, ordered)
```
e fai chiamare `_validate_payload` da `save_sintesi` (nessun cambio di comportamento).
2. Aggiungi:
```python
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
    _validate_payload(db, template.id, payload)  # prima di creare: niente offerte orfane
    offer = offer_service.create_offer(db, data)
    offer_service.create_sintesi_document(db, offer.id)
    save_sintesi(db, offer.id, payload)
    return offer


def get_sintesi_template_data(db: Session) -> SintesiData:
    template = _active_fisse_template(db)
    # come get_sintesi_data ma senza documento/valori: fixed_fields con value_text=""
    # e rows=[]; voci/dynamic_blocks dalle definizioni del template
```
Riusa la stessa costruzione di `get_sintesi_data` (estrai un helper comune se serve).

- [ ] **Step 5: Endpoint `POST /api/offers`** in `app/api/routers/api.py`
```python
from app.schemas import OfferCreateFull


@router.post("/offers", status_code=201)
def create_offer_full(
    data: OfferCreateFull, db: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    offer = sintesi_service.create_offer_with_sintesi(db, data)
    return {"id": str(offer.id)}
```

- [ ] **Step 6: Estrai il JS in `app/static/editor.js`**

Sposta il blocco `<script>` di `offer_detail.html` in `app/static/editor.js` e gestisci due modalità:
- `window.SINTESI_MODE = "edit"` (in `offer_detail.html`): comportamento attuale (PUT).
- `window.SINTESI_MODE = "new"` (in `offer_new.html`): il bottone "Crea offerta" raccoglie `name`, `segment_id`, `technology_id` dai campi della card anagrafica + `{fixed, rows}` e invia `POST /api/offers`; su 201 redirige a `/offers/{id}`.

In `app/main.py` monta gli statici:
```python
from pathlib import Path

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
```

**Nota "Nuova voce…" senza reload:** in modalità new (e anche in edit) il click su "Nuova voce…" NON deve ricaricare la pagina (perderebbe i campi già digitati). Dopo il `POST /api/voci`: aggiungi la voce a `DATA.blocks[...].voci`, appendi l'`<option>` a tutte le `select.voce-select` di quel blocco e selezionala nell'ultima select del blocco che ha avuto il focus (altrimenti resta selezionabile a mano). Nessun rerender delle righe (le modifiche non salvate vivono nel DOM).

- [ ] **Step 7: Route `/offers/new` a form completo** in `pages.py`

Passa `data=sintesi_service.get_sintesi_template_data(db)`, `segments`, `technologies`, e il JSON delle definizioni (come l'editor). Il template `offer_new.html` diventa la pagina completa: card anagrafica (Nome offerta, Segmento, Tecnologia), campi fissi, tabelle dinamiche, bottone **"Crea offerta"**, link "Annulla"; include `<script src="/static/editor.js"></script>` e `window.SINTESI_MODE = "new"`.

- [ ] **Step 8: Aggiorna `offer_detail.html`** per usare `editor.js` (rimuovi lo script inline, aggiungi `window.SINTESI_MODE = "edit"` e lo `<script src="/static/editor.js"></script>`). La route `POST /offers` (form minimale) resta per compatibilità e per i test esistenti.

- [ ] **Step 9: Esegui la suite**

Run: `uv run pytest -q` → tutti verdi (23 + 3 nuovi); `uv run ruff check .`; `uv run mypy app`.

---

## Task 15: Bootstrap del database all'avvio (fix "no such table")

**Feedback utente:** avviando solo `uv run uvicorn app.main:app --reload`, `GET /` → 500 `no such table: offers` (DB assente o vuoto: il seed era un passo manuale dimenticato).

**Fix:** all'avvio l'app crea directory, schema e applica il seed delle definizioni (idempotente). `python -m app.seed` resta disponibile ma non è più obbligatorio.

**Files:**
- Create: `app/bootstrap.py`
- Modify: `app/main.py` (lifespan), `README.md`
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Scrivi il test che fallisce** (`tests/test_bootstrap.py`)
```python
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
```

- [ ] **Step 2: Esegui e verifica fallimento** (`uv run pytest tests/test_bootstrap.py -v` → FAIL).

- [ ] **Step 3: Implementa `app/bootstrap.py`**
```python
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
```

- [ ] **Step 4: Chiama il bootstrap nel lifespan di `app/main.py`**
```python
from app.bootstrap import bootstrap_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    bootstrap_database()
    yield
    engine.dispose()
```

- [ ] **Step 5: Aggiorna `README.md`**: all'avvio il database viene creato e le definizioni caricate automaticamente; `uv run python -m app.seed` resta disponibile (idempotente).

- [ ] **Step 6: Verifica**
```bash
rm -f data/mvp.db
uv run pytest -q
uv run uvicorn app.main:app --port 8012   # GET / → 200 (Ctrl+C dopo la prova)
```

---

## Task 16: Popolamento dei campi derivati (nome offerta e velocità)

**Feedback utente:** nel form "Nuova offerta", selezionando la **Tecnologia** le due caselle velocità (disabilitate) devono popolarsi correttamente; digitando **Nome offerta** si deve popolare il campo "Nome Offerta" nella tabella Intestazione.

**Nota:** il popolamento manca anche nell'editor (i derivati `nome_offerta`/`velocita_*` risultano vuoti perché non sono valori salvati). Si corregge: **server-side in edit mode** (valori da offerta/tecnologia) e **client-side live in new mode**.

**Files:**
- Create: `app/services/formatting.py`
- Modify: `app/services/generation.py`, `app/services/sintesi.py`, `app/templates/offer_new.html`, `app/static/editor.js`
- Test: `tests/test_sintesi.py`, `tests/test_offers.py`

- [ ] **Step 1: `app/services/formatting.py`**
```python
def format_speed(value: int, direction: str) -> str:
    return f"{value},00 Mbps in {direction}"
```

- [ ] **Step 2: `app/services/generation.py`** usa `from app.services.formatting import format_speed` e rimuovi la definizione locale (comportamento invariato).

- [ ] **Step 3: `app/services/sintesi.py` — risolvi i derivati in `get_sintesi_data`**
```python
from dataclasses import replace

from app.models import Technology
from app.services.formatting import format_speed


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
```
In `get_sintesi_data`, dopo `_definitions(...)`:
```python
    technology = db.get(Technology, offer.technology_id) if offer.technology_id else None
    fixed_fields = _resolve_derived(fixed_fields, offer.name, technology)
```
(la modalità new resta con derivati vuoti: li popola il JS.)

- [ ] **Step 4: `app/templates/offer_new.html`** — dati velocità sulle option:
```html
{% for technology in technologies %}
<option value="{{ technology.id }}"
        data-download="{{ technology.max_download_mbps }}"
        data-upload="{{ technology.max_upload_mbps }}">{{ technology.name }}</option>
{% endfor %}
```

- [ ] **Step 5: `app/static/editor.js`** — live update in modalità new
```js
  function formatSpeedJs(value, direction) {
    const number = Number(value);
    if (!Number.isFinite(number)) { return ""; }
    return number.toFixed(2).replace(".", ",") + " Mbps in " + direction;
  }

  function setDerivedValue(key, value) {
    const input = document.querySelector('input[data-key="' + key + '"]');
    if (input) { input.value = value; }
  }

  function refreshDerivedFields() {
    const nameInput = document.getElementById("offer-name");
    if (nameInput) { setDerivedValue("nome_offerta", nameInput.value); }
    const techSelect = document.getElementById("technology-id");
    if (techSelect) {
      const option = techSelect.selectedOptions[0];
      const download = option && option.dataset.download ? option.dataset.download : "";
      const upload = option && option.dataset.upload ? option.dataset.upload : "";
      setDerivedValue("velocita_download", download ? formatSpeedJs(download, "Download") : "");
      setDerivedValue("velocita_upload", upload ? formatSpeedJs(upload, "Upload") : "");
    }
  }
```
e nel blocco `if (MODE === "new")` (dopo `renderFixedFields()`):
```js
    const nameInput = document.getElementById("offer-name");
    const techSelect = document.getElementById("technology-id");
    if (nameInput) { nameInput.addEventListener("input", refreshDerivedFields); }
    if (techSelect) { techSelect.addEventListener("change", refreshDerivedFields); }
    refreshDerivedFields();
```

- [ ] **Step 6: Test**
`tests/test_sintesi.py` (edit mode, derivati risolti):
```python
def test_editor_shows_derived_values(client, segment_id, technology_id) -> None:
    import json
    import re

    offer_id = create_offer(client, "Offerta Derivati", segment_id, technology_id)
    page = client.get(f"/offers/{offer_id}")
    match = re.search(r'<script id="sintesi-json"[^>]*>(.*?)</script>', page.text, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    values = {f["key"]: f["value"] for f in data["fixed_fields"]}
    assert values["nome_offerta"] == "Offerta Derivati"
    assert values["velocita_download"] == "300,00 Mbps in Download"
    assert values["velocita_upload"] == "50,00 Mbps in Upload"
```
`tests/test_offers.py` (contratto template new):
```python
def test_new_offer_page_has_derived_wiring(client: TestClient) -> None:
    page = client.get("/offers/new")
    assert 'id="offer-name"' in page.text
    assert 'id="technology-id"' in page.text
    assert "data-download=" in page.text
    assert "refreshDerivedFields" in ... # nel JS statico, non nella pagina
```
(sostituire l'ultima assert con: `assert "/static/editor.js" in page.text`.)

- [ ] **Step 7: Verifica**
```bash
node --check app/static/editor.js
uv run pytest -q
uv run ruff check .
uv run mypy app
```
Smoke: avvia uvicorn, apri `/offers/new`, seleziona una tecnologia → le caselle velocità si popolano; digita il nome → il campo Nome Offerta si aggiorna.

---

## Task 17: Rendering frontend diverso per tabelle 1 colonna e 2 colonne

**Richiesta utente:** nel frontend le tabelle dinamiche devono apparire diversamente a seconda del layout: `2_col` (Prezzo) affiancata, `1_col` (Costi) incolonnata. Il dato esiste già in `DATA.blocks[].layout` (`template_blocks.layout`).

**Files:**
- Create: `app/static/editor.css`
- Modify: `app/static/editor.js`, `app/templates/offer_new.html`, `app/templates/offer_detail.html`
- Test: `tests/test_offers.py` (+1)

- [ ] **Step 1: Estrai gli stili dell'editor in `app/static/editor.css`**

Sposta lì le regole oggi duplicate nei due template (`.block-card`, `.block-card .card-header h3`, `.block-card table td:first-child`, `.data-row select.voce-select`, ecc.) e aggiungi le regole per i layout:

```css
.block-card.layout-2-col table td:first-child { width: 40%; }
.block-card.layout-2-col .data-row select.voce-select { min-width: 200px; }

.block-card.layout-1-col table,
.block-card.layout-1-col thead,
.block-card.layout-1-col tbody,
.block-card.layout-1-col tr,
.block-card.layout-1-col td { display: block; width: auto; }
.block-card.layout-1-col thead { display: none; }
.block-card.layout-1-col .data-row {
  border: 1px solid var(--w3-border);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: var(--w3-gray-light);
}
.block-card.layout-1-col .data-row td { padding: 4px 0; }
.block-card.layout-1-col .data-row select.voce-select,
.block-card.layout-1-col .data-row .value-input { width: 100%; }
.block-card.layout-1-col .child-row { margin-left: 24px; }
```

In entrambi i template: rimuovi dalle `<style>` le regole spostate e aggiungi
`<link rel="stylesheet" href="/static/editor.css">` nell'`<head>`.

- [ ] **Step 2: `app/static/editor.js` — classe di layout sul blocco**

In `renderBlock`, dopo `card.dataset.block = block.code;`:
```js
    card.classList.add(block.layout === "1_col" ? "layout-1-col" : "layout-2-col");
```

- [ ] **Step 2b: etichetta nel titolo della card**

Accanto al titolo del blocco mostra in piccolo il layout: `· tabella a 1 colonna` /
`· tabella a 2 colonne` (span `.muted`), così la differenza è esplicita anche a
colpo d'occhio. Aggiorna lo smoke DOM per verificare la presenza dell'etichetta.

- [ ] **Step 3: (opzionale, per coerenza pre-JS) Jinja nei template**

Sui `div.block-card` server-rendered: `class="block-card {{ 'layout-1-col' if block.layout == '1_col' else 'layout-2-col' }}"`.

- [ ] **Step 4: Test** (`tests/test_offers.py`)
```python
def test_editor_pages_link_editor_css(client: TestClient) -> None:
    for path in ("/offers/new",):
        page = client.get(path)
        assert page.status_code == 200
        assert "/static/editor.css" in page.text
```

- [ ] **Step 5: Verifica**
```bash
node --check app/static/editor.js
uv run pytest -q
uv run ruff check .
uv run mypy app
```
Smoke (harness Node con DOM stub, come Task 16): con un blocco `1_col` la card ha `layout-1-col` e le righe sono `display:block` (classe presente); con `2_col` ha `layout-2-col`.

---

## Handoff

Dopo il Task 13 l'MVP è completo: offerte Fisse, Sintesi con campi fissi e
tabelle dinamiche (voci dal dizionario + "Nuova voce"), generazione DOCX dal
template, modifiche massive con anteprima e storico minimo.

**Fuori scope (fase 2):** Trasparenza, note con chip, PDF, Stati AGCOM/naming,
permessi, cluster, RDA, alias tra voci, valori ricorrenti.

