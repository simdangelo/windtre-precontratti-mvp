# 12 — Gestione degli errori

Un'applicazione a strati non gestisce gli errori in un punto solo: li **solleva**
nello strato che li scopre, nella lingua del dominio, e li **traduce** al
confine. Ogni strato parla la sua lingua.

---

## Ogni strato parla la sua lingua

- **Business logic** → linguaggio del dominio: `ItemNotFoundError`,
  `CategoryHasItemsError`. Il nome dell'eccezione è il nome della regola
  violata.
- **Presentazione** → linguaggio del trasporto: status code HTTP e messaggi per
  il client.
- **Validazione** → linguaggio della forma: campo mancante, valore non valido.
  La gestisce FastAPI/Pydantic, non il tuo codice.

Regola: un errore è **creato** dove nasce e **tradotto** dove deve essere
comunicato. Il servizio non solleva mai `HTTPException`; il router non inventa
mai una regola.

---

## Eccezioni di dominio

Una classe per condizione, in `app/services/exceptions.py`:

```python
class ItemNotFoundError(Exception):
    pass


class DuplicateItemError(Exception):
    pass


class CategoryHasItemsError(Exception):
    pass
```

Perché non un `ValueError` generico: chi deve tradurre non sa cosa significhi.
Perché non `None`: il chiamante deve indovinare se "non trovato" o "vuoto
legittimo". L'eccezione nominata è auto-documentante e rende la traduzione una
corrispondenza uno-a-uno.

> Progettazione completa (naming, gerarchia, contesto, testing):
> [09 — Eccezioni personalizzate](09-eccezioni-personalizzate.md).

---

## La traduzione al confine

Il router intercetta le eccezioni di dominio e le mappa sui codici HTTP:

```python
try:
    return item_service.create_item(db, current_user.id, data)
except CategoryNotFoundError as e:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Category doesn't exist"
    ) from e
```

- Il `raise ... from e` incatena l'eccezione originale (buono per il debugging,
  non trapela al client).
- La traduzione è una **corrispondenza 1:1**: se nel `except` compare una
  condizione/ragionamento, la logica è slittata dal servizio al router.

---

## Errori di forma: al framework

Input malformato (campo mancante, tipo sbagliato, stringa troppo lunga) →
`422` automatico di Pydantic. Non scrivere codice per questo: la validazione è
dichiarativa e sta sullo schema di input. Il tuo codice gestisce solo gli errori
di **merito** (quelli che richiedono di consultare lo stato del sistema).

---

## Il database come garante: EAFP

Alcune regole non si affidano solo al controllo preventivo (race condition). Il
vincolo del database è la garanzia dura e atomica; il codice traduce l'errore di
integrità in un'eccezione di dominio:

```python
from sqlalchemy.exc import IntegrityError

try:
    db.commit()
except IntegrityError as e:
    db.rollback()
    raise DuplicateItemError(...) from e
```

L'**esistenza** si controlla prima (per distinguere `404` da `409`); la **regola
di integrità** la fa rispettare il database.

> Attenzione: intercettare in modo cieco un `IntegrityError` è corretto solo se
> l'operazione può violare **un solo** vincolo noto. Se possono scattarne
> diversi (FK, unique, check), l'errore è ambiguo: va ispezionato o disambiguato
> con un controllo preventivo.

---

## La mappa degli errori

| Situazione | Chi la scopre | Risposta |
|-----------|---------------|----------|
| Input malformato (forma) | Pydantic | `422` automatico |
| Entità non trovata | servizio (eccezione di dominio) | `404` |
| Regola di integrità violata | database, tradotto dal servizio | `409` (o adatto) |
| Non autorizzato | dependency auth | `401` |
| Dato di un altro utente | scoping → "non esiste" | `404` |
| Eccezione inattesa | handler globale | `500` (senza dettagli interni) |
| Tutto ok | — | `200` / `201` / `204` |

---

## Handler globali e logging

In `main.py` si registrano handler per gli errori che non sono previsti dai
router:

```python
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception on %s %s request_id=%s",
        request.method,
        request.url.path,
        request_id,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"X-Request-ID": request_id},
    )
```

Note:

- Si logga l'eccezione **completa** lato server (`exc_info`), ma al client si
  manda un messaggio generico: mai far trapelare stack trace, query o dettagli
  interni.
- Un middleware HTTP assegna un `request_id` a ogni richiesta e lo restituisce
  nell'header `X-Request-ID`: serve a correlare log e segnalazioni.
- `print` non è logging: usa il modulo `logging`.

---

## Rollback: parte della gestione errore

Quando un `commit` fallisce, la sessione resta incoerente. Se la si riusa senza
`rollback`, l'errore avvelena la richiesta successiva che ottiene la stessa
connessione dal pool. Il `rollback` (in `get_db` o nel servizio dopo
l'`IntegrityError`) è obbligatorio.

---

## Insidie

- **Eccezioni con nomi generici** (`ValueError`): il router non sa tradurle.
- **Tradurre troppo presto**: `HTTPException` nel servizio accoppia la logica al
  trasporto.
- **Tradurre troppo tardi**: un `IntegrityError` grezzo che arriva al client come
  `500` con dettagli interni.
- **Nessun `rollback`** dopo un commit fallito.
- **Controlli preventivi al posto dei vincoli**: lasciano aperta la race
  condition e duplicano nel codice una regola già garantita dal DB.
- **Far trapelare `str(exc)`** nella risposta: leak di informazioni.
- **`except Exception: pass`**: nasconde i bug. Se catturi, gestisci o rilancia.
- **Perdere l'eccezione originale** senza `from e`: difficile da debuggare.
