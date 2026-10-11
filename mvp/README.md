# MVP Sintesi & Trasparenze

Web app MVP per la compilazione della Sintesi contrattuale di offerte Fisse
(form separato, tavole dinamiche a voci, modifica massiva) e la generazione del
DOCX dal template Word.

## Documentazione

Il pacchetto è **autocontenuto**: la documentazione completa è in
[`docs/README.md`](docs/README.md) — panoramica dell'applicativo, funzionalità
implementate, modello dati, fuori scope e roadmap, piano di implementazione,
documenti di design e guida di ingegneria.

## Requisiti
- uv, Python 3.13

## Avvio
```bash
uv sync
uv run uvicorn app.main:app --reload
# http://localhost:8000
```

All'avvio l'app crea automaticamente il database (`data/mvp.db`), lo schema e
carica le definizioni (segmenti, tecnologie, template, voci). L'operazione è
idempotente. Il seed manuale resta disponibile ma non è più obbligatorio:

```bash
uv run python -m app.seed
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
