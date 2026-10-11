# 15 — Anti-pattern e insidie

Un elenco consolidato, pensato come checklist di review. Ogni voce è un errore
frequente, il motivo per cui è pericoloso e la correzione.

---

## Architettura e layer

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| Query nel router | rompe i confini, logica non riusabile | sposta nel servizio |
| `HTTPException` nel servizio | accoppia la logica al trasporto | eccezione di dominio + traduzione nel router |
| Regole di business sul modello | modello grasso, regola duplicata e non testata | servizio |
| Import dai percorsi interni | fragile ai refactor | importa dalla facciata del package |
| Import circolari | `ImportError` a runtime | solo `__init__.py` importa gli interni |
| `requirements.txt` + `pyproject.toml` | due fonti di verità che divergono | tieni solo `pyproject.toml` + `uv.lock` |
| `document_generator` importato dai modelli | dipendenza verso il basso invertita | tienilo in `services/` |

## Database e SQLAlchemy

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| Engine/sessionmaker creati per richiesta | butti il pool, paghi l'handshake ogni volta | creali una volta in `database.py` |
| Sessione condivisa tra richieste/thread | transazioni incrociate, race condition | nuova sessione per richiesta |
| Dimenticare `close()` | esaurisci il pool | `finally: session.close()` |
| `db.query()` | stile legacy | `db.execute(select(...))` |
| N+1 (relazione in un loop) | l'endpoint peggiora linearmente/quadraticamente | `selectinload`/`joinedload` |
| Id letto prima del flush | `None` | `flush`/`commit` + `refresh` |
| `expire_on_commit=True` in app web | `DetachedInstanceError` | `expire_on_commit=False` |
| `and`/`or` di Python nelle query | filtri sbagliati | `.where(*conditions)` o `and_`/`or_` |
| `== None` | non è `IS NULL` | `.is_(None)` |
| `Float` per il denaro | errori di arrotondamento | `Numeric` + `Decimal` da stringa |
| datetime naive | bug di fuso orario | `timezone=True` + `datetime.now(UTC)` |
| UUID generato dal DB | non portabile (Spanner) | `default=uuid4` in Python |
| Vincoli UNIQUE globali su entità utente | il primo utente blocca il nome a tutti | `UNIQUE (user_id, name)` |
| `IntegrityError` grezzo al client | `500` con dettagli interni | traduci in eccezione di dominio + `rollback` |
| Nessun `rollback` dopo errore | sessione incoerente per la richiesta successiva | `rollback` esplicito o in `get_db` |
| SQL costruito per concatenazione | SQL injection | `text()` con parametri legati |

## API e FastAPI

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| Logica nel router | layer violato | delega al servizio |
| `response_model` che riusa `Create` | espone campi interni | separa `Response` |
| Route dinamiche prima delle statiche | `/summary` catturata da `/{id}` | dichiara prima le statiche |
| Status code come numeri nudi | difficile da leggere | `status.HTTP_*` |
| `async def` con I/O bloccante | blocca l'event loop | `def` finché il DB è sync |
| `@app.on_event` | deprecato | `lifespan` |
| CORS `allow_origins=["*"]` permanente | sicurezza allentata | single origin / proxy |
| Nessun limite su `skip`/`limit` | un client scarica tutto | `Query(ge=..., le=...)` |
| `str(exc)` nella risposta | leak di informazioni | messaggio generico, log lato server |
| `print` come logging | non strutturato, non correlabile | modulo `logging` + request id |

## Configurazione e sicurezza

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| `.env` committato | fuga di segreti (anche se rimosso dopo: ruota le chiavi) | gitignora, committa `.env.example` |
| Credenziali hardcoded | stesse in tutti gli ambienti | `pydantic-settings` + `.env` |
| `os.environ` sparso | niente tipi né validazione | `Settings` centralizzato |
| Segreto tipizzato `str` | finisce nei log | `SecretStr` |
| Password in chiaro / hash deboli | compromissione account | Argon2id via `pwdlib` |
| Confronto password con `==` | timing attack | `verify_password` della libreria |
| Cookie senza `HttpOnly`/`Secure` | XSS/HTTP | flag obbligatori |
| `user_id` preso dal body | un utente crea righe per un altro | dal token |
| Query senza `WHERE user_id` | fuga di dati tra utenti | scoping sempre |
| `403` dove serve `404` | rivela l'esistenza di dati altrui | `404` |
| Segreto JWT con default nel codice | token falsificabili | obbligatorio da env |

## Python e tooling

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| `python`/`pip` nudi | ambiente sbagliato, lock aggirato | `uv run` |
| `uv.lock` non committato | ambienti non riproducibili | committalo |
| mypy senza `strict` | finta sicurezza | `strict = true` |
| `Any` come scappatoia | disabilita i controlli | tipo preciso, o spiega |
| `# type: ignore` per zittire | nasconde il problema | risolvi o documenta |
| Default mutabili (`default=[]`) | condivisi tra istanze | `default_factory` |
| `except Exception: pass` | nasconde i bug | gestisci o rilancia |
| `from pkg import *` | API sporca | import espliciti + `__all__` nella facciata |
| Formattazione mescolata a logica nello stesso commit | review illeggibile | commit atomici |
| `print` di debug lasciati | rumore e leak | rimuovi o usa `logging` |

## Enum ed eccezioni

| Anti-pattern | Perché è male | Correzione |
|--------------|---------------|------------|
| Valori enum come stringhe libere | niente validazione, magic value | `StrEnum` + colonna `Enum` |
| `values_callable` dimenticato | nel DB finiscono i nomi (`DRAFT`), non i valori | `values_callable=lambda e: [m.value for m in e]` |
| Enum nativo per vocabolario instabile | `ALTER TYPE` doloroso, non portabile (Spanner) | `native_enum=False` o lookup table |
| Enum per insiemi che crescono a runtime | serve un rilascio per un dato | tabella dedicata + FK |
| `ValueError`/`None` per segnalare regole | traduzione ambigua o impossibile | eccezione di dominio nominata |
| `HTTPException` nel servizio | logica accoppiata al trasporto | eccezione di dominio |
| Gerarchie di eccezioni profonde | cerimonia senza ritorno | piatte, o base comune a due livelli |
| `raise XError(...)` senza `from e` | perdi la causa originale | `raise ... from e` |
| Messaggi di eccezione con segreti/PII | finiscono nei log | contesto non sensibile |

---

## Checklist finale prima di una PR

- [ ] Nessuna query o regola nel router; nessun import FastAPI nel servizio.
- [ ] Ogni accesso al DB è scoped a utente/segmento.
- [ ] Nessun N+1 sui nuovi endpoint di lista.
- [ ] Configurazione via `settings`, nessun segreto nel codice.
- [ ] Eccezioni di dominio tradotte al confine; `rollback` dove serve.
- [ ] `response_model` separato dai request schema.
- [ ] Test aggiunti per felice / non trovato / 422 / scoping.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app tests`,
      `uv run pytest` tutti verdi.
- [ ] Commit atomici con messaggi `type(scope): subject`.
