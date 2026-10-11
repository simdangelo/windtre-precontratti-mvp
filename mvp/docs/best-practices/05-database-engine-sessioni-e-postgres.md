# 05 — Database: engine, sessioni e Postgres

Come si connette l'applicazione al database, come si gestisce il ciclo di vita
della sessione, e come si configura un Postgres in modo sano. Il target attuale
è Postgres; la configurazione resta volutamente portabile (il progetto potrebbe
passare a Cloud Spanner più avanti).

---

## I tre oggetti di SQLAlchemy

Confonderli è la radice di quasi tutti i bug di setup:

| Oggetto | Cos'è | Vita |
|---------|-------|------|
| `Engine` | factory di connessioni: conosce URL, driver e **pool** | una volta, per tutta l'app |
| `sessionmaker` | factory di sessioni, legata all'engine con configurazione condivisa | una volta, per tutta l'app |
| `Session` | unità di lavoro: traccia gli oggetti, tiene la transazione | **breve, per richiesta** |

### Engine — creato una volta

```python
from sqlalchemy import create_engine

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
```

L'engine possiede il **pool di connessioni**: tiene un piccolo insieme di
connessioni TCP già aperte e pronte, così una nuova `Session` non paga
l'handshake ogni volta. Non si interagisce quasi mai con l'engine direttamente.

### Sessionmaker — creato una volta

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
```

È il "template delle sessioni": stessa engine, stessi default. Questo è
l'oggetto da cui il resto dell'app dipende.

### Session — creata per richiesta, mai condivisa

- Nuova a ogni richiesta (o operazione logica).
- **Mai condivisa** tra richieste o thread: non è thread-safe.
- **Sempre chiusa**: chiudere restituisce la connessione al pool. Le sessioni
  non chiuse esauriscono il pool.

### `expire_on_commit=False`

Per default, dopo il `commit()` SQLAlchemy "scade" gli oggetti: la prossima
lettura di un attributo re-interroga il database. In un'app web questo produce
query inattese e, se la sessione è chiusa, `DetachedInstanceError`. Per questo
si imposta `expire_on_commit=False`.

### `autoflush`

Con `autoflush=True` (default) una query fa prima il flush dei cambi pendenti.
Comodo ma sorprendente (una query può scatenare scritture). Lo teniamo a `False`
e facciamo flush/commit espliciti dove serve.

---

## Il ciclo di vita: add / flush / commit / refresh / rollback

```python
item = Item(name="x")
db.add(item)       # 1. traccia l'oggetto (nessun SQL)
db.flush()         # 2. manda l'INSERT nel DB, dentro la transazione aperta
print(item.id)     #    ora c'è: generato dal DB durante il flush
db.commit()        # 3. chiude la transazione: il dato è persistente
db.refresh(item)   # 4. rilegge la riga (server default, trigger, valori calcolati)
```

- `add` → tracking, non SQL.
- `flush` → esegue INSERT/UPDATE **dentro** la transazione (qui arrivano gli id
  auto-generati).
- `commit` → rende permanenti le modifiche.
- `refresh` → re-interroga la riga per i valori calcolati dal DB.
- `rollback` → scarta il lavoro non committato. Pattern standard:
  `try: ... commit() except: rollback(); raise`.

---

## `get_db`: la dependency di FastAPI

```python
# app/database.py
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Il router la riceve e la passa al servizio:

```python
db: Annotated[Session, Depends(get_db)]
```

### Chi fa `commit`?

Due filosofie, entrambe valide — se ne sceglie **una** e si è coerenti:

- **Option A — commit nel teardown di `get_db`.** Meno boilerplate, ma il commit
  avviene dopo la serializzazione della risposta: se non hai fatto `flush`,
  l'id può risultare `None` nel body.
- **Option B — commit nel servizio (mainstream FastAPI).** Chi fa il lavoro
  committa e fa `refresh`. Esplicito e con valori corretti prima della
  serializzazione.

> **Noi usiamo l'Option B.** `get_db` resta solo setup/teardown (rollback su
> errore + close sempre).

---

## Configurare un Postgres

### Stringa di connessione

Formato SQLAlchemy: `dialect+driver://user:password@host:port/database`.

```
postgresql+psycopg://app_user:password@localhost:5432/app_db
```

La stringa **non va scritta nel codice**: arriva da `settings.database_url`
(vedi [04 — Configurazione](04-pydantic-settings-env.md)).

### Postgres locale con Docker Compose

Il database di sviluppo gira in container, mai installato sull'host:

```yaml
services:
  db:
    image: postgres:17
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Il volume preserva i dati tra un riavvio e l'altro; l'healthcheck evita che il
backend parta prima che il DB sia pronto.

### Pool

| Parametro | Cosa fa | Perché |
|-----------|---------|--------|
| `pool_size` | connessioni mantenute aperte | limita il carico sul DB |
| `max_overflow` | connessioni extra oltre `pool_size` | picchi temporanei |
| `pool_pre_ping` | verifica la connessione prima di usarla | evita connessioni morte dopo un riavvio del DB |
| `pool_recycle` | ricicla le connessioni dopo N secondi | evita timeout lato DB |

Regola: dimensionare il pool in base al numero di worker e ai limiti di
connessioni del server. Un pool troppo grande satura Postgres, troppo piccolo
crea code.

---

## Portabilità (nota per il futuro Spanner)

Il target attuale è Postgres, ma la configurazione resta generica per non
precludere Cloud Spanner:

- Niente estensioni Postgres-specifiche (`gen_random_uuid()`, funzioni custom).
- UUID generati in Python (`default=uuid4`), non dal database.
- Evitare dialetto SQLite (es. `connect_args={"check_same_thread": False}`) nel
  codice di produzione: era un dettaglio della POC.
- SQLAlchemy 2.0 `select()` standard, senza costrutti specifici del dialetto.

---

## Database di test

I test usano un **database Postgres separato** (es. `app_test_db`), creato dai
modelli tramite `Base.metadata.create_all`, mai il DB di sviluppo. I dettagli
sono in [13 — Testing](13-testing-pytest.md).

---

## Esempio di riferimento

```python
# app/database.py
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## Insidie

- **Engine creato per richiesta**: butta via il pool e paga il setup ogni volta.
- **Sessione condivisa** tra richieste/thread: transazioni incrociate e race
  condition.
- **Dimenticare `close()`**: connessioni del pool che si esauriscono.
- **Leggere l'id prima di `flush`/`commit`**: `None`, perché il DB non l'ha
  ancora generato.
- **Restituire oggetti senza `refresh`** quando il DB calcola valori: `None` o
  dati stantii nella risposta.
- **`expire_on_commit=True` + sessione chiusa**: `DetachedInstanceError`.
- **Commit sia nel servizio sia in `get_db`**: doppio commit. Scegli l'unico
  proprietario (Option B).
- **Nessun `rollback` su errore**: transazione rimasta aperta che avvelena la
  richiesta successiva che riusa la connessione.
- **Credenziali hardcoded** nella stringa di connessione.
- **Nessun `pool_pre_ping`**: dopo un riavvio del DB le connessioni morte
  generano errori intermittenti.
- **Un DB SQLite in produzione "tanto è comodo"**: non regge concorrenza e
  differenze di dialetto.
