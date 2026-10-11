# MVP Sintesi & Trasparenze — Documentazione

Questo pacchetto (`mvp/`) è un MVP **autocontenuto**: contiene l'applicazione,
il template Word, i test e questa documentazione. Chi lo riceve può avviarlo e
capire **cosa fa, come è fatto, cosa manca**.

## Da dove partire

| # | Documento | Contenuto |
|---|---|---|
| — | **Questo indice** | Mappa della documentazione e avvio rapido |
| 01 | [Panoramica dell'applicativo](01_PANORAMICA_APPLICATIVO.md) | Contesto WINDTRE, obiettivo, utenti, flusso operativo, pagine, stack e struttura |
| 02 | [Funzionalità implementate](02_FUNZIONALITA_IMPLEMENTATE.md) | Tutto ciò che l'MVP fa oggi, in dettaglio: form, editor, generazione, massive, API, test |
| 03 | [Modello dati](03_MODELLO_DATI.md) | Schema del database: tabelle, colonne, relazioni, enum, seed, scelte di design |
| 04 | [Fuori scope e roadmap](04_FUORI_SCOPE_E_ROADMAP.md) | Cosa non è stato implementato per semplicità e come aggiungerlo (Trasparenza, note, PDF, AGCOM, permessi…) |
| 05 | [Documento di riferimento dell'MVP](05_DOCUMENTO_DI_RIFERIMENTO_MVP.md) | **Il documento più completo**: registro delle decisioni, razionale del modello, ER completo, esempio end-to-end, punti aperti (stile dei documenti in `riferimenti/`) |
| — | [`plans/`](plans/2026-10-10-mvp-sintesi.md) | Piano di implementazione eseguito, task per task (storico) |
| — | [`riferimenti/`](riferimenti/) | Documenti di design del progetto (dal repo principale), utili per il razionale |
| — | [`best-practices/`](best-practices/) | Guida di ingegneria seguita dal codice (architettura a strati, Pydantic, SQLAlchemy, testing) |

> **As-built vs design.** Per capire *com'è davvero* l'MVP fanno fede i documenti
> 01–04 e il codice. I documenti in `riferimenti/` descrivono il progetto e il
> design complessivo: alcune parti (es. note con chip, Trasparenza, mappature)
> sono ancora solo su carta.

## Avvio rapido

```bash
cd mvp
uv sync
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000
```

Al primo avvio l'app crea da sola il database SQLite (`data/mvp.db`), lo schema
e le definizioni di base (segmenti, tecnologie, template, campi, voci).
Non serve nessun passo manuale.

```bash
uv run pytest        # 78 test
uv run ruff check .  # lint
uv run mypy app      # type check (strict)
```

## In una frase

Web app per il marketing WINDTRE che permette di **creare offerte Fisse**,
**compilare la Sintesi contrattuale** (campi fissi + tabelle dinamiche con voci
scelte da un dizionario), **generare il DOCX** dal template Word e applicare
**modifiche massive** su più offerte con anteprima.
