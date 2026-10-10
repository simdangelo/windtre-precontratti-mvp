# Contributing — guida per gli sviluppatori

Benvenuto nel progetto. Questo documento spiega **come lavorare in questa
repository**: stack, setup dell'ambiente, comandi quotidiani e cosa fare prima
di committare e pushare.

Per il dettaglio teorico delle scelte tecniche vedi
[`docs/best-practices/`](docs/best-practices/README.md): è il manuale di
ingegneria del progetto. Qui c'è la pratica quotidiana.

---

## Stack

| Ambito | Tecnologia |
|--------|------------|
| Linguaggio | Python >= 3.13 (versione in `.python-version`) |
| Package/environment manager | **uv** |
| Web framework | **FastAPI** (endpoint sincroni) |
| ORM / DB access | **SQLAlchemy 2.0** (sincrono) |
| Validazione / config | **Pydantic v2**, **pydantic-settings** |
| Database | Postgres (target); SQLite per il mockup locale |
| Testing | **pytest** (attraverso l'HTTP layer) |
| Lint / format | **ruff** |
| Type checking | **mypy** (modalità `strict`) |
| Hook pre-commit | **pre-commit** (opzionale) |

Fonte di verità per le dipendenze: `pyproject.toml` (intervalli) + `uv.lock`
(versioni esatte). **Non** si usa `pip` né `requirements.txt`.

---

## Prerequisiti

- **`uv`** installato:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- `uv` scarica da solo la versione Python richiesta da `.python-version`.

---

## Setup iniziale

```bash
# 1. Installa le dipendenze (runtime + sviluppo) e crea .venv
uv sync

# 2. Crea il file .env locale partendo dall'esempio
cp .env.example .env

# 3. (Opzionale, consigliato) Installa gli hook pre-commit
uv run pre-commit install
```

> Il passo 3 è **facoltativo**: se non lo esegui, gli stessi controlli vanno
> lanciati a mano (vedi *Prima di committare / pushare*). Se lo esegui, però,
> vanno rifatti a ogni macchina su cui cloni il repository.

---

## Lanciare l'applicazione

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- Applicazione: <http://localhost:8000>
- Documentazione OpenAPI (Swagger): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Al primo avvio il mockup locale crea il database SQLite `pre_contratti.db` e ne
esegue il seed.

---

## Git

Convenzioni per branch e commit: [02 — Git e commit convention](docs/best-practices/02-git-e-commit-convention.md).

---

## Prima di committare / pushare

Controlli da eseguire ogni volta. `pre-commit`, se installato, li esegue già
automaticamente al commit; qui li lanci a mano.

```bash
# Formatta il codice (riscrive lo stile: spazi, a capo, ordine degli import)
uv run ruff format .

# Lint: trova bug e pattern sospetti; --fix corregge il correggibile
uv run ruff check . --fix

# Type check statico in modalità strict (le promesse delle annotazioni)
uv run mypy app tests

# Esegue la suite di test
uv run pytest
```

---

## Struttura del progetto (target)

Il refactor porta il backend da file piatti (`app/api_routes.py`,
`app/database_models.py`) a una struttura a strati:

```
app/
├── main.py            # creazione FastAPI, middleware, include_router, lifespan
├── config.py          # Settings (pydantic-settings)
├── database.py        # engine, SessionLocal, Base, get_db
├── api/               # router FastAPI + dependencies (presentazione)
├── schemas/           # Pydantic request/response (contratto API)
├── services/          # logica di business (nessun import FastAPI)
└── models/            # modelli SQLAlchemy (un file per entità)
```

Regola d'oro: `api → services → models`, mai il contrario. Dettagli in
[03 — Struttura a strati](docs/best-practices/03-struttura-a-strati-e-package.md).

---

## Dove approfondire

| Argomento | Documento |
|-----------|-----------|
| Setup e tooling | [01 — Ambiente e tooling](docs/best-practices/01-ambiente-e-tooling.md) |
| Git e commit | [02 — Git e commit convention](docs/best-practices/02-git-e-commit-convention.md) |
| Architettura | [03 — Struttura a strati](docs/best-practices/03-struttura-a-strati-e-package.md) |
| Indice completo | [docs/best-practices/README.md](docs/best-practices/README.md) |
