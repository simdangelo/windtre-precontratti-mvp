# 01 — Panoramica dell'applicativo

## 1. Contesto

WINDTRE (con il marchio Very Mobile) deve produrre, per ogni offerta
commerciale, documenti regolamentari destinati ai clienti:

- la **Sintesi Contrattuale**: documento Word (poi PDF) con sezioni, tabelle
  padre/figlio, note e bollini di tecnologia;
- la **Trasparenza Tariffaria**: scheda Excel a griglia fissa imposta da AGCOM.

Oggi i documenti sono file sparsi sui PC del marketing: ogni modifica comune a
più offerte va rifatta a mano, con errori e disallineamenti.

**Questo MVP copre solo la Sintesi**, e solo per la categoria di offerte
**Fisse**. La Trasparenza è progettata ma rimandata (vedi documento 04).

## 2. Obiettivo e decisioni di fondo

L'app permette al marketing di:

1. creare **offerte Fisse** (nome univoco, segmento, tecnologia);
2. gestire il **ciclo di vita dell'offerta** (`NUOVA`/`APERTA`/`CHIUSA`) con il
   **codice AGCOM**;
3. **compilare la Sintesi** su un form (tabelle fisse + tabelle a righe
   variabili, con la tecnologia modificabile);
4. **generare il DOCX** dal template Word, pronto per la distribuzione;
5. applicare **modifiche massive** sulla Sintesi (stesso valore su più offerte)
   con anteprima ed esito per offerta.

Le decisioni di progetto che danno forma a tutto il resto:

| Decisione | Conseguenza |
|---|---|
| **Due ground truth indipendenti** (Sintesi, Trasparenza) | I due documenti si compilano separatamente e possono divergere; qui è implementata solo la Sintesi |
| **Voci delle tabelle dinamiche da un dizionario condiviso** | Le etichette di padri/figli si scelgono da una tendina o si creano con "Nuova voce"; è ciò che rende possibile riconoscere "la stessa voce" tra offerte diverse |
| **Nessuna voce obbligatoria nelle tabelle dinamiche** | L'utente crea solo le righe che servono; il template definisce solo titolo e layout |
| **Azioni massive solo sulla Sintesi** | La Trasparenza (futura) non avrà modifiche massive |
| **Un template per categoria** (Fisse, Mobile, Very) | Nell'MVP esiste solo il template `SINTESI_FISSE` |
| **Niente punti prezzo / varianti** | L'unità di lavoro è l'offerta con nome univoco |
| **Stato e codice AGCOM liberi** | Nessun vincolo automatico: li imposta l'utente (default `NUOVA`); tag colorati e chip per leggerli a colpo d'occhio |

## 3. Utenti e flusso operativo

Gli utenti sono persone del marketing, non tecniche. Il flusso tipico:

1. **Nuova offerta** → si apre il form completo: Nome offerta, Segmento,
   Tecnologia, **Stato e codice AGCOM** (già presenti, default `NUOVA`) + tutti
   i campi della Sintesi (tabelle fisse e tabelle dinamiche). Con una sola
   azione ("Crea offerta") nascono offerta, documento Sintesi e valori, e si
   torna all'elenco.
2. **Editor Sintesi** → si compila e si salva dalla barra in fondo ("Applica
   Modifiche", che riporta all'elenco); si può cambiare **tecnologia**, **stato
   e codice AGCOM**, generare la Sintesi `.docx` (solo dopo il salvataggio) e
   scaricarla. Si possono aggiungere voci nuove al dizionario senza uscire
   dalla pagina.
3. **Modifica massiva multi-campo** → si compilano solo i valori da cambiare
   (campi fissi e voci) e si scelgono le offerte; si vede un'anteprima con gli
   esiti e il dettaglio per offerta (prima → dopo) e si applica.
4. **Elenco offerte** → per le offerte senza documento Sintesi c'è il tasto
   "Crea Sintesi" (creazione on the fly, come nell'app precedente); la tabella
   mostra **stato** e **codice AGCOM**.

### Le pagine

| Pagina | URL | Cosa contiene |
|---|---|---|
| Elenco offerte | `/` | Tabella delle offerte con stato, codice AGCOM, "Apri" / "Crea Sintesi" e "Nuova offerta" |
| Nuova offerta | `/offers/new` | Form completo: anagrafica + tabelle fisse + tabelle dinamiche (nasce `NUOVA`) |
| Editor Sintesi | `/offers/{id}` | Tecnologia/stato/AGCOM, compilazione, barra "Applica Modifiche" + "Genera Sintesi (.docx)" in fondo, documenti generati |
| Modifica massiva | `/bulk` | Bersaglio, valore, selezione offerte, anteprima, applicazione |

L'interfaccia è server-rendered (Jinja2) con tema scuro nello stile della
dashboard WINDTRE esistente; le parti interattive (tabelle dinamiche, anteprima
massiva) usano JavaScript vanilla in `app/static/editor.js` e `editor.css`.

## 4. Stack e architettura

| Livello | Tecnologia |
|---|---|
| Linguaggio / gestione progetto | Python 3.13, `uv` |
| API e pagine | FastAPI + Jinja2 (`TemplateResponse`) |
| Persistenza | SQLAlchemy 2.0, SQLite (`data/mvp.db`) |
| Contratti API | Pydantic v2 |
| Rendering DOCX | `docxtpl` (merge field + cicli) |
| Qualità | pytest + TestClient, ruff, mypy strict |

Architettura **a strati** (come da guida `docs/best-practices/`):

```
app/
├── main.py        # assembly: lifespan (bootstrap DB), error handler, static
├── config.py      # Settings (pydantic-settings, prefisso MVP_)
├── database.py    # engine, SessionLocal, Base, get_db
├── bootstrap.py   # crea schema + seed all'avvio (idempotente)
├── seed.py        # entrypoint opzionale: python -m app.seed
├── api/           # PRESENTAZIONE: router pagine + router API, dependencies
├── schemas/       # CONTRATTO API: Pydantic
├── services/      # LOGICA: offer, sintesi, voce, generation, bulk, seed
├── models/        # PERSISTENZA: SQLAlchemy, un file per tabella
├── static/        # editor.js, editor.css
└── templates/     # pagine Jinja2 (base, elenco, nuova, editor, bulk)
```

Regole rispettate: i router sono sottili (nessuna query, nessun commit); i
servizi non conoscono FastAPI; i modelli sono muti. Le eccezioni di dominio
(`app/services/exceptions.py`) vengono tradotte in risposte HTTP solo al
confine (`app/main.py`).

## 5. File e dati prodotti

```
mvp/
├── data/mvp.db                 # SQLite (creata al primo avvio)
├── data/generated/             # DOCX generati (mai sovrascritti)
└── templates/word/sintesi_fisse_template.docx   # template di generazione
```

Il template Word contiene i **merge field** (`{{ campo.<chiave> }}`) e i
**cicli delle tabelle dinamiche** (`{%tr for r in prezzo.righe %}`). Dettagli e
convenzioni nel documento 02; il modello delle definizioni nel documento 03.

## 6. Avvio e comandi

```bash
cd mvp
uv sync                                # dipendenze
uv run uvicorn app.main:app --reload   # avvia (bootstrap automatico)
uv run pytest                          # test
uv run ruff check .                    # lint
uv run mypy app                        # type check strict
```

Configurazione opzionale via `.env` (vedi `.env.example`): URL del database,
directory dati/file generati, percorso del template.
