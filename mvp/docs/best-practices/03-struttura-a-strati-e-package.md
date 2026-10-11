# 03 — Struttura a strati e package

Come è organizzato il backend, perché è organizzato così, e come si scrivono
gli import perché la struttura regga nel tempo.

---

## Perché separare in strati

Un'applicazione backend ha tre responsabilità distinte:

1. **Ricevere le richieste** (HTTP, JSON, file).
2. **Decidere cosa fare** (le regole: totali, validazioni incrociate, permessi).
3. **Conservare i dati** (leggere/scrivere sul database).

Mettere tutto insieme funziona per un prototipo, ma appena il codice cresce:

- la stessa regola si duplica in più endpoint e prima o poi diverge;
- per capire un comportamento bisogna leggere codice HTTP, SQL e regole nello
  stesso file;
- cambiare lo schema del database tocca ogni punto in cui il DB è mescolato;
- testare una regola significa passare per HTTP e per il database.

La struttura a strati assegna **una responsabilità per strato** e impone
chiamate in **una sola direzione**.

---

## I quattro package

```
app/
├── main.py                 # creazione FastAPI, middleware, include_router, lifespan
├── config.py               # Settings (pydantic-settings)
├── database.py             # engine, SessionLocal, Base, get_db
├── api/                    # PRESENTAZIONE — router FastAPI e dependencies
│   ├── __init__.py
│   ├── dependencies.py     # get_current_user, CurrentUser, ...
│   └── routers/
│       ├── __init__.py
│       ├── offer.py
│       └── segment.py
├── schemas/                # CONTRATTO API — Pydantic
│   ├── __init__.py
│   ├── offer.py
│   └── segment.py
├── services/               # LOGICA DI BUSINESS — funzioni/classi pure
│   ├── __init__.py
│   ├── exceptions.py       # eccezioni di dominio
│   └── offer.py
└── models/                 # PERSISTENZA — SQLAlchemy
    ├── __init__.py
    ├── types.py            # enum condivisi
    ├── offer.py
    └── segment.py
```

Questa è la stessa divisione di pynance (`api/`, `schemas/`, `services/`,
`models/`) e la forma mainstream delle applicazioni FastAPI reali.

### Le regole che non si violano

- Ogni strato chiama **solo quello immediatamente sotto**. `api → services →
  models`.
- `services/` **non importa mai FastAPI** e niente da `api/`.
- `api/` **non tocca il database**: nessuna query, nessun `db.add/commit`. La
  `Session` compare solo come dipendenza iniettata da passare al servizio.
- I **modelli** non contengono regole di business, solo semplici proprietà
  derivate.
- Gli **schemas** sono il contratto API: i request schema sono input validato
  per i servizi; i response schema sono solo per l'API e non entrano nel
  livello dati.

### Perché non un repository layer

Il pattern repository serve a poter scambiare o simulare il database. Qui il
database è uno solo e i test girano contro un DB di test vero: il repository
sarebbe indirezione senza ritorno. I servizi usano la `Session` direttamente.

---

## Che architettura è (e che non è)

Vale la pena essere espliciti, perché "a strati" viene spesso confuso con
"esagonale" o "clean". Non lo è, e non è nemmeno una variante nata per caso: è
una **layered architecture pragmatica**, con alcune scelte prese deliberatamente
e altre rifiutate.

### I tre modelli a confronto

**Layered (a strati) — quello che usiamo.** Tre livelli orizzontali
(presentazione → business → dati) con chiamate solo top-down. Nessuna
inversione delle dipendenze: lo strato basso non definisce interfacce che quello
alto implementa; non esistono "porte" né "adapter".

**Hexagonal / Ports & Adapters.** Il dominio sta al centro ed è completamente
isolato. Tutto ciò che è esterno (HTTP, database, code, servizi terzi) viene
raggiunto tramite **porte** (interfacce definite dal dominio) implementate da
**adapter** (le classi concrete). La dipendenza è invertita: è il mondo esterno
a dipendere dal dominio, non viceversa. Serve a poter scambiare tecnologia
(due database, più API esterne) senza toccare la logica.

**Clean Architecture.** Un raffinamento dell'idea esagonale, organizzato in
**cerchi concentrici**: entità (regole enterprise), use case (regole
applicative), interface adapter (presenter/controller/gateway), framework e
driver. La **regola della dipendenza** è ferrea: le dipendenze puntano sempre
verso l'interno; il dominio non conosce né il framework né il database.

### Confronto sulle dimensioni che contano

| Dimensione | Layered (noi) | Hexagonal / Clean |
|-----------|---------------|-------------------|
| Dipendenze | top-down tra gli strati | inversione verso il dominio |
| Dominio | modelli ORM dentro il servizio | puro, senza framework/ORM |
| Persistenza | `Session` usata direttamente | dietro una porta/repository |
| Contratti | schemas Pydantic al confine HTTP | porte definite dal dominio |
| Costo per feature | basso | alto (interfacce, mapping) |
| Paga quando | un DB, dominio contenuto | più tecnologie, dominio ricco |

### Cosa abbiamo adottato e perché

Abbiamo scelto il **layered semplice** per tre ragioni concrete:

1. **Una sola tecnologia per concern.** Un database (Postgres, forse Spanner in
   futuro), un solo confine HTTP. Le porte e gli adapter comprano la
   sostituibilità *a runtime* di una tecnologia — utile quando ne hai due in
   parallelo, non quando ne hai una sola e non è previsto affiancarla.
2. **Dominio di dimensione contenuta.** La logica (validazioni incrociate,
   scoping, generazione documenti) non ha bisogno di un modello di dominio
   indipendente dall'ORM. Un secondo modello "puro" da mantenere e mappare
   sarebbe cerimonia senza ritorno.
3. **Testabilità ottenuta per altra via.** Il beneficio principale
   dell'esagionale è poter testare il dominio senza infrastruttura. Qui lo
   otteniamo testando **attraverso l'HTTP** contro un database di test vero:
   nessun doppione da mantenere, e verifichiamo il comportamento reale.

Alcuni tratti "esagonali" li abbiamo comunque, senza il vocabolario: il
servizio non conosce FastAPI (dominio non a conoscenza del framework), le
eccezioni di dominio vengono tradotte solo al confine, la direzione delle
dipendenze è rigida. È una versione leggera degli stessi principi.

### Cosa abbiamo deliberatamente rifiutato

- **Repository pattern**: indirezione per scambiare/simulare il DB. Non serve
  con un solo DB e test su DB reale.
- **Dominio puro separato dall'ORM**: un doppio modello da mappare a mano.
- **Inversione delle dipendenze con porte/adapter**: nessuna necessità di
  sostituire l'infrastruttura a runtime.

### La regola che decide

Ogni livello di indirezione deve **comprare qualcosa di concreto**. Non si
aggiunge un'astrazione "perché è più pulito": si aggiunge quando risolve un
problema reale (più tecnologie, dominio davvero ricco, esigenza di sostituzione
a runtime). La scelta è **revisabile**: se in futuro il progetto dovesse avere
due backend di persistenza o un dominio molto più ricco, introdurre porte e
adapter diventa una decisione motivata — non un errore da correggere. Nel
frattempo, il layered semplice con confini rispettati è la forma che risolve i
problemi veri con meno codice.

> Vale la pena registrare questa decisione in un breve **ADR** (Context,
> Decision, Alternatives, Consequences) quando il progetto verrà stabilizzato,
> così la ratio resta tracciabile e la sua revisione è un atto esplicito.

---

## Il package come facciata

Ogni package espone una API pubblica tramite il proprio `__init__.py`, che
ri-esporta i simboli e dichiara `__all__`:

```python
# app/models/__init__.py
from app.models.offer import Offer
from app.models.segment import Segment
from app.models.types import OfferStatus

__all__ = ["Offer", "OfferStatus", "Segment"]
```

I consumatori importano **dalla facciata**, mai dal percorso interno:

```python
# CORRETTO
from app.models import Offer, Segment

# SBAGLIATO (fragile: qualunque riordino interno rompe i consumatori)
from app.models.offer import Offer
```

Il vantaggio: gli interni possono cambiare (un file si sposta, si divide) senza
toccare i consumatori, purché la facciata resti stabile.

**Regola anti-import-circolare:** solo l'`__init__.py` importa i moduli interni.
I moduli interni importano tra loro per percorso pieno (`from app.models.segment
import Segment`), **mai** dal root del package (`from app.models import ...`).

---

## Import assoluti

Usa import **assoluti** dall'inizio del percorso:

```python
from app.services.offer import bulk_update_offers   # preferito
from .offer import bulk_update_offers               # sconsigliato oltre un livello
```

Gli import assoluti sono espliciti su da dove arriva il simbolo, robusti quando
un package viene annidato e sono quelli preferiti da PEP 8 e da mypy.

---

## Un file per entità

- Un file per tabella/entità in `models/` (es. `offer.py`, `segment.py`).
- Un file per entità in `schemas/` e in `services/`.
- Gli **enum condivisi** vivono in `models/types.py` (`StrEnum`).
- Le **eccezioni di dominio** vivono in `services/exceptions.py`.

---

## Naming convention

Vale per servizi, router, endpoint, dataclass e response schema.

### CRUD

`create_<entity>` / `get_<entity>` (uno per id) / `list_<entities>` (collezione)
/ `update_<entity>` / `delete_<entity>`.

> Per le collezioni si usa `list_`, **non** `get_` al plurale.

Gli endpoint rispecchiano:

| Operazione | Servizio | Endpoint |
|-----------|----------|----------|
| crea | `create_offer` | `POST /offers` |
| leggi uno | `get_offer` | `GET /offers/{id}` |
| elenca | `list_offers` | `GET /offers` |
| aggiorna | `update_offer` | `PATCH /offers/{id}` |
| cancella | `delete_offer` | `DELETE /offers/{id}` |

### Report

Grammatica `<metrica>[_by_<dimensione>]`, con metriche `summary`, `trend`,
`comparison`. Il periodo è espresso da query param, mai nel nome:

- `get_summary`, `get_summary_by_category`, `get_trend`, `get_comparison`
- endpoint `/summary`, `/summary-by-category`, `/trend`, `/comparison`
  (trattini negli URL, underscore in Python).

I tipi rispecchiano: `Summary`/`SummaryResponse`,
`SummaryByCategoryRow`/`SummaryByCategoryRowResponse`.

---

## Da `app/` attuale alla struttura target

La POC attuale ha file piatti (`app/api_routes.py`, `app/database_models.py`,
`app/document_generator.py`) che mescolano responsabilità. Il refactor li
distribuisce così:

| File attuale | Destinazione |
|--------------|--------------|
| `app/main.py` | resta, ma assottigliato (solo assembly dell'app) |
| `app/api_routes.py` | `app/api/routers/*.py` (uno per risorsa) |
| `app/database_models.py` (ORM + schemi Pydantic insieme) | ORM → `app/models/*.py`; Pydantic → `app/schemas/*.py` |
| `app/services/*.py` | restano, allineati alle regole |
| engine/`SessionLocal` duplicati | un solo `app/database.py` |
| `os.environ`/`load_dotenv` | `app/config.py` con `pydantic-settings` |

`document_generator.py` è un caso a parte (rendering documenti): diventa un
servizio di supporto sotto `app/services/` (o una cartella dedicata), ma non
deve mai essere importato da `models/`.

---

## Insidie

- **Saltare gli strati**: il router che interroga il DB "perché è più veloce",
  il servizio che solleva `HTTPException`. Ogni scorciatoia rimescola le
  responsabilità.
- **Dipendenza verso l'alto**: un modello che importa da `api/`.
- **Import dai percorsi interni**: vanifica la facciata e rende ogni refactor
  invasivo.
- **Import circolari**: quasi sempre causati da un modulo interno che importa
  dal root del package.
- **Package senza `__init__.py`**: non è un package, gli import tra strati si
  rompono in modi confusi.
- **Un file "modello" che contiene anche gli schemi Pydantic**: è esattamente il
  problema attuale della POC; tienili separati.
- **`__init__.py` che esegue logica all'import**: la facciata deve solo
  ri-esportare.
