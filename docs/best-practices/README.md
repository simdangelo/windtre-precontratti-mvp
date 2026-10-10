# Best practices — guida del progetto

Questa cartella raccoglie le convenzioni e le best practice da seguire nel
refactor del backend. Non è documentazione del prodotto (per quello vedi
`docs/onboarding/` e `docs/architecture_blueprint.md`): è il **manuale di
ingegneria** che dice come si scrive il codice, come si struttura il progetto e
cosa evitare.

La guida nasce dall'analisi di due repository di riferimento indicati dal
committente:

- **pynance** — riferimento principale per ambiente Python, tooling e
  architettura a strati (`backend/pyproject.toml`, `backend/pynance/`, `docs/wiki/`).
- **fastapi-tutorial-by-corey-schafer** — riferimento per FastAPI, SQLAlchemy,
  Pydantic e testing.

> **Fuori scope per ora:** le migrazioni del database (Alembic). In questi
> documenti si parla di schema e di `create_all` per i test; la gestione
> versionata dello schema è rimandata a uno step successivo.

> **Guida pratica quotidiana** (setup, comandi, git, checklist pre-push):
> [`CONTRIBUTING.md`](../../CONTRIBUTING.md) nella root del progetto.

---

## Indice

I documenti sono ordinati secondo la **sequenza di adozione nel refactor**, non
per importanza astratta: prima le fondamenta che sbloccano tutto il resto, poi
l'infrastruttura dati, quindi il dominio e l'API, la qualità, e in fondo ciò che
arriva più tardi (autenticazione, SSO). L'ultimo è un riferimento trasversale.

### Fase 1 — Fondamenta

| # | Documento | Cosa copre |
|---|-----------|------------|
| 01 | [Ambiente e tooling](01-ambiente-e-tooling.md) | Python, `uv`, `ruff`, `mypy`, VS Code, `pre-commit`, `.env` |
| 02 | [Git e commit convention](02-git-e-commit-convention.md) | Conventional Commits leggera, branch, cosa committare |
| 03 | [Struttura a strati e package](03-struttura-a-strati-e-package.md) | Architettura a layer (vs hexagonal/clean), facade, import, naming |

### Fase 2 — Infrastruttura dati

| # | Documento | Cosa copre |
|---|-----------|------------|
| 04 | [Configurazione con pydantic-settings](04-pydantic-settings-env.md) | `Settings`, `SecretStr`, `.env`, precedenza |
| 05 | [Database: engine, sessioni e Postgres](05-database-engine-sessioni-e-postgres.md) | Engine, sessionmaker, `get_db`, pool, configurazione Postgres |
| 06 | [SQLAlchemy — modelli](06-sqlalchemy-modelli.md) | Un file per tabella, stile 2.0, colonne, relazioni, enum |
| 07 | [Query con SQLAlchemy](07-query-sqlalchemy.md) | `select()` 2.0, filtri, join, eager loading, N+1 |

### Fase 3 — Dominio e API

| # | Documento | Cosa copre |
|---|-----------|------------|
| 08 | [Pydantic — schemas](08-pydantic-schemas.md) | Base/Create/Update/Response, validazione, `from_attributes` |
| 09 | [Eccezioni personalizzate](09-eccezioni-personalizzate.md) | Progettare le eccezioni di dominio e tradurle |
| 10 | [Service layer](10-services.md) | Logica di business, eccezioni di dominio, transazioni |
| 11 | [FastAPI — router ed endpoint](11-fastapi-router-ed-endpoint.md) | Router sottili, dependency injection, status code |
| 12 | [Gestione degli errori](12-gestione-errori.md) | Traduzione al confine, mappa errori, EAFP |

### Fase 4 — Qualità

| # | Documento | Cosa copre |
|---|-----------|------------|
| 13 | [Testing con pytest](13-testing-pytest.md) | Fixture, `conftest.py`, test attraverso HTTP, DB di test |

### Fase 5 — Più avanti

| # | Documento | Cosa copre |
|---|-----------|------------|
| 14 | [Autenticazione](14-autenticazione.md) | Dependency utente corrente, sessioni vs JWT, scoping per utente |

### Riferimento

| # | Documento | Cosa copre |
|---|-----------|------------|
| 15 | [Anti-pattern e insidie](15-anti-pattern-e-insidie.md) | Elenco consolidato di cosa non fare + checklist pre-PR |

> **Nota sull'ordine.** Il testing (13) è documentato dopo i layer che verifica,
> ma nella pratica si scrive **da subito**: appena esiste un servizio, il suo
> test. L'autenticazione (14) dipende dai layer sottostanti e dalla decisione su
> sessioni vs OIDC, quindi arriva più avanti. Le migrazioni (Alembic) restano
> fuori scope per ora.

---

## I principi trasversali

Se dovessi dimenticare tutto il resto, ricorda questi. Ogni documento li
declina nel suo ambito.

1. **A strati e top-down.** `api/` (HTTP) → `services/` (regole) → `models/`
   (dati). Ogni strato chiama solo quello sotto. Il router non tocca il
   database; il servizio non conosce FastAPI; il modello non contiene regole.
2. **Pydantic è il confine, non il dominio.** Gli schemas `*Create`/`*Update`
   validano l'input dell'API; i `*Response` modellano l'output. I servizi
   ritornano modelli ORM o tipi propri, non schemas di risposta.
3. **Tutto tipizzato.** Type hints su ogni funzione e variabile, `mypy` in
   modalità `strict`. `Any` solo con una spiegazione.
4. **Configurazione centralizzata.** `pydantic-settings` legge `.env`; niente
   `os.environ` sparso, niente credenziali nel codice.
5. **Una sessione per richiesta.** Engine e `sessionmaker` creati una volta;
   `get_db` fornisce la `Session` e la chiude sempre.
6. **Eccezioni di dominio, tradotte al confine.** Il servizio solleva
   `ItemNotFoundError`; il router la traduce in `HTTPException(404)`.
7. **Errori di forma al framework, errori di merito al codice.** Input
   malformato → `422` automatico di Pydantic; regole di business → tuo codice.
8. **Test attraverso l'HTTP layer**, contro un database di test vero, con
   `app.dependency_overrides`.
9. **Isola i dati per proprietario.** Ogni riga di un utente si crea, legge,
   aggiorna e cancella sempre nel perimetro di quell'utente.
10. **Eager load ciò che leggi.** Un relationship dentro un loop è la firma
    dell'N+1: caricalo con `selectinload`/`joinedload`.

---

## Cheat sheet dei comandi

```bash
# Ambiente
uv sync                      # crea/aggiorna .venv dal lock
uv run <comando>             # esegue dentro l'ambiente (mai python/pip nudi)

# Sviluppo
uv run uvicorn app.main:app --reload
uv run ruff check . --fix    # lint + fix automatici
uv run ruff format .         # formattazione
uv run mypy app tests        # type check (strict)
uv run pytest                # test
uv run pre-commit run --all-files
```

> `pre-commit install` va eseguito **una volta** per repository: senza,
> `.pre-commit-config.yaml` è carta morta.

---

## Convenzione dei documenti

Ogni documento segue la stessa struttura, per facilità di consultazione:

- **Razionale** — perché esiste la pratica.
- **Regole** — cosa fare, con esempi di codice.
- **Trade-off** — quando la pratica non conviene.
- **Insidie** — gli errori tipici da evitare.

Gli esempi usano un dominio generico (`User`, `Category`, `Item`) per restare
riusabili anche quando il dominio del prodotto cambia.
