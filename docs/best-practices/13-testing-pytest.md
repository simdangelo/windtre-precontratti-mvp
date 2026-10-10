# 13 — Testing con pytest

Come si scrivono i test del backend: attraverso l'HTTP layer, contro un database
di test vero, con fixture condivise in `conftest.py`.

---

## Perché i test esistono

I test sono la rete di sicurezza che rende sicuro il refactor: bloccano *cosa*
fa il codice, così puoi cambiarne *come* senza rompere il comportamento. Sono
anche documentazione eseguibile.

Il ciclo è **TDD**: scrivi prima il test che fallisce (dimostra il requisito),
poi il codice minimo che lo fa passare, poi rifattorizzi. Guardare il test
fallire prima è ciò che gli dà valore.

---

## Le basi di pytest

- Scoperta per convenzione: file `test_*.py`, funzioni `test_*`.
- `assert` normale: pytest riscrive le asserzioni e mostra i valori reali, senza
  boilerplate `unittest`.
- **Fixture**: funzioni che preparano ciò che serve al test.

```python
@pytest.fixture
def item():
    return Item(name="x")
```

### Forma `yield` (setup + teardown)

```python
@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Il teardown gira **sempre**, anche se il test fallisce. È lo stesso pattern
`yield` di `get_db`.

### Scope

| Scope | Gira una volta per... | Per cosa |
|-------|----------------------|----------|
| `function` (default) | test | stato fresco per ogni test |
| `module` | modulo | setup di modulo |
| `session` | intera run | setup costoso una volta sola (creare lo schema) |

Parti da function-scoped; allarga solo quando il setup è davvero costoso.

### `parametrize`

```python
@pytest.mark.parametrize("a,b,expected", [(1, 2, 3), (0, 0, 0), (-1, 1, 0)])
def test_add(a, b, expected):
    assert a + b == expected
```

Ogni riga diventa un test separato con i valori nel nome: un fallimento dice
esattamente quale caso è rotto. Meglio di un loop con `assert` dentro (che si
ferma al primo errore).

### `conftest.py`

Le fixture in `tests/conftest.py` sono disponibili a **tutti** i file nella
cartella e sotto, senza import. Qui stanno client, sessione, e gli helper per
creare dati attraverso l'API.

---

## Testare attraverso l'HTTP layer

La strategia del progetto (come pynance): le richieste attraversano **tutto** —
validazione, router, servizio, SQL vero sul database di test, serializzazione. Il
test verifica il comportamento reale, non la tua idea del comportamento.

```python
def test_create_item(client: TestClient):
    category = create_category(client, "books")
    response = client.post(
        "/api/items",
        json={"name": "book", "amount": "12.34", "category_id": category["id"]},
    )
    assert response.status_code == 201
    assert response.json()["amount"] == "12.34"
```

Per FastAPI:

- **Sync**: `fastapi.testclient.TestClient` (usa `httpx` sotto).
- **Async**: `httpx.AsyncClient` con `ASGITransport(app=app)`.

Il client parla con l'app **senza avviare un server**: niente porte, niente
processi separati.

---

## Il punto di giunzione: `dependency_overrides`

In produzione l'app usa `get_db`; nei test la stessa app deve usare il database
di test. Si sovrascrive la dependency:

```python
# tests/conftest.py
import os
from collections.abc import Generator

os.environ["DATABASE_URL"] = "postgresql+psycopg://app_user:pass@localhost:5432/app_test_db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def setup_database() -> Generator[None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(setup_database: None) -> Generator[Session]:
    session = TestingSessionLocal()
    # pulizia: ogni test parte da tabula rasa
    session.execute(delete(Item))
    session.execute(delete(Category))
    session.execute(delete(User))
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

Punti chiave:

- Le variabili d'ambiente si impostano **prima** di importare l'app (il
  `Settings` singleton si valuta all'import).
- Lo schema si crea una volta per sessione (`scope="session"`); la pulizia dei
  dati è per test.
- `app.dependency_overrides.clear()` nel teardown è obbligatorio, altrimenti i
  test successivi usano l'override sbagliato.

---

## Il database di test

- Deve essere **Postgres**, separato da sviluppo/produzione (es. `app_test_db`).
  SQLite nei test nasconde differenze di dialetto (tipi, vincoli, `GROUP BY`).
- Lo schema si crea **dai modelli** (`Base.metadata.create_all`): veloce e
  sempre allineato ai modelli correnti.
- L'alternativa (eseguire le migrazioni) è più fedele alla produzione ma più
  lenta. In questo progetto, con le migrazioni fuori scope, si usa il
  create-dai-modelli.

---

## Cosa testare

- **Percorsi felici**: crea, leggi, aggiorna, cancella, report corretti.
- **Regole di business tramite comportamento osservabile**: se una regola dice
  "il tipo segue la categoria", cambia la categoria e verifica che la risposta
  cambi.
- **Non trovati**: id inesistente → `404`.
- **Validazione**: input mancanti/malformati → `422`.
- **Scoping/auth**: un utente non vede né modifica i dati di un altro.

---

## Test buoni: comportamento, non implementazione

- **Un comportamento per test**: tre `assert` indipendenti nascondono
  informazioni in caso di fallimento.
- **Asserisci il risultato, non i passi**: `assert result == expected`, non
  "il servizio è stato chiamato con X".
- **Isola**: ogni test deve funzionare da solo, in qualunque ordine.
- **Confine e mezzo**: i casi limite da soli possono mascherare bug. Testa
  l'inizio, un valore centrale, la fine.
- **Attento al falso verde**: un test che passa prima che la feature esista non
  prova nulla.

---

## Trade-off

Testare attraverso l'HTTP costa (DB di test, esecuzione più lenta). Conviene
quando la logica è attaccata alla persistenza, che è il caso di un'app a strati.
La **logica pura** (matematica, trasformazioni senza I/O) resta più veloce e
altrettanto affidabile se testata direttamente, senza passare dall'HTTP.

---

## Insidie

- **Test che dipendono dall'ordine**: righe accumulate tra test. Pulisci nelle
  fixture.
- **Asserzioni sull'implementazione**: si rompono a ogni refactor innocuo.
- **Dimenticare il teardown**: sessioni/client non chiusi, override non rimossi.
- **`pytest.raises` dimenticato**: per "questo solleva", usa
  `with pytest.raises(ValueError):`, non `try/except` nel test.
- **Skip come abitudine**: un test skippato è un test che non testa.
- **DB di test = DB di sviluppo**: dati e segreti mescolati.
