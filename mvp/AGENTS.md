# AGENTS.md — MVP Sintesi WINDTRE

## Regole di lavoro

- **Dopo ogni modifica al codice/comportamento, aggiornare subito i documenti
  in `docs/` (01–05)** così che restino sempre allineati. Vale anche per
  scelte, rimozioni e rinvii: aggiornare il registro decisioni di `05`, la
  sezione di competenza di `02`/`03` e le piste in `04`.
- Non committare mai senza richiesta esplicita.

## Comandi

- Test: `uv run pytest -q`
- Lint: `uv run ruff check .`
- Tipi: `uv run mypy app`
- JS: `node --check app/static/editor.js`
- Avvio: `uv run uvicorn app.main:app --reload`
