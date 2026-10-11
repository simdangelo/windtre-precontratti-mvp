# 11 — FastAPI: router ed endpoint

Il router è lo strato di **presentazione**: traduce una richiesta HTTP in una
chiamata al servizio e il risultato in una risposta. Deve restare **sottile**.

---

## Router sottili

Un endpoint fa esattamente quattro cose:

1. Riceve input validati (path/query param + body schema).
2. Riceve le dipendenze (`Session`, utente corrente).
3. Delega al servizio, traducendo le eccezioni di dominio in `HTTPException`.
4. Restituisce il risultato (che FastAPI serializza col `response_model`).

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.database import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemResponse
from app.services import item as item_service
from app.services.exceptions import CategoryNotFoundError

router = APIRouter()


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    data: ItemCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Item:
    try:
        return item_service.create_item(db, current_user.id, data)
    except CategoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category doesn't exist"
        ) from e
```

**Nel router non devono mai comparire**: query SQL, `db.add/commit`, regole di
business, `if` decisionali sul dominio. La `Session` è solo un valore da passare
al servizio.

---

## Assemblaggio dell'app

```python
# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import category, item
from app.database import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    engine.dispose()  # chiude il pool allo shutdown


app = FastAPI(title="App API", lifespan=lifespan)

app.include_router(item.router, prefix="/api/items", tags=["items"])
app.include_router(category.router, prefix="/api/categories", tags=["categories"])
```

- Usa **`lifespan`**, non il deprecato `@app.on_event("startup")`.
- I router dichiarano solo il proprio percorso relativo; il `prefix` e i `tags`
  li mette `include_router` in `main.py`.

---

## Dependency injection

FastAPI costruisce il grafo delle dipendenze a partire dai parametri. Lo stile
moderno usa `Annotated`:

```python
db: Annotated[Session, Depends(get_db)]
current_user: CurrentUser          # alias Annotated[User, Depends(get_current_user)]
```

L'alias `CurrentUser` (vedi [14 — Autenticazione](14-autenticazione.md)) evita di
ripetere `User = Depends(get_current_user)` in ogni firma e centralizza il tipo.

---

## Parametri e validazione

```python
from typing import Annotated
from fastapi import Query


@router.get("", response_model=list[ItemResponse])
def list_items(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    category_id: int | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Item]:
    filters = item_service.ItemFilters(q=q, category_id=category_id)
    return item_service.list_items(db, current_user.id, filters, skip=skip, limit=limit)
```

- I vincoli (`ge`, `le`, `min_length`) si dichiarano nell'annotazione: la
  validazione è automatica.
- I parametri di paginazione hanno sempre dei limiti massimi (`le=100`): senza,
  un client può chiedere l'intera tabella.

---

## Ordine dei path

Le route **statiche** vanno dichiarate **prima** di quelle dinamiche, altrimenti
`/summary` viene catturata da `/{item_id}`:

```python
@router.get("/summary", response_model=SummaryResponse)   # prima
def get_summary(...): ...

@router.get("/{item_id}", response_model=ItemResponse)    # dopo
def get_item(...): ...
```

---

## Status code e `response_model`

| Operazione | Status |
|-----------|--------|
| `POST` che crea | `201 Created` |
| `GET`/`PATCH` | `200 OK` |
| `DELETE` | `204 No Content` (ritorna `None`) |

- `response_model` è il **filtro** dell'output: solo i campi dichiarati escono,
  anche se il modello ORM ne ha altri (protegge dall'esporre interni).
- Per il `204`, la funzione deve dichiarare `-> None` e non restituire corpo.
- Usa le costanti `status.HTTP_*`, non i numeri nudi.

---

## Aggiornamento parziale (PATCH)

```python
@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    data: ItemUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Item:
    try:
        return item_service.update_item(db, current_user.id, item_id, data)
    except ItemNotFoundError as e:
        raise HTTPException(status_code=404, detail="Item doesn't exist") from e
```

La partialità è gestita nel servizio con `model_dump(exclude_unset=True)` (vedi
[08 — Schemas](08-pydantic-schemas.md)).

---

## Gestione centralizzata degli errori

Il router traduce solo le eccezioni **previste**. Per tutto il resto si
registrano handler globali in `main.py` (vedi
[12 — Gestione errori](12-gestione-errori.md)): un handler per le eccezioni non
gestite che logga e restituisce `500` senza far trapelare dettagli interni, e un
middleware che assegna un `request_id` per correlare i log.

---

## CORS e single origin

La scelta di default è **una sola origine**:

- In sviluppo, il dev server del frontend fa da proxy verso `/api` → niente
  CORS.
- In produzione, FastAPI serve i file statici del frontend → stessa origine.

`CORSMiddleware` con `allow_origins=["*"]` è una scorciatoia della POC, non una
soluzione permanente: va introdotta solo come eccezione esplicita e discussa.

---

## Servire file statici / SPA

Se il backend serve anche il frontend buildato, si monta `StaticFiles` e si
aggiunge un fallback per le route SPA:

```python
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend-dist"
router = APIRouter()

if FRONTEND_DIST.is_dir():
    router.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @router.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        candidate = FRONTEND_DIST / path
        return FileResponse(candidate if candidate.is_file() else FRONTEND_DIST / "index.html")
```

---

## Sync o async?

Il progetto usa **SQLAlchemy sincrono**. Con un endpoint `def` (non `async def`)
FastAPI lo esegue in un threadpool e le chiamate bloccanti (DB) non bloccano
l'event loop. Se un endpoint è `async def`, **non** deve contenere chiamate
bloccanti altrimenti blocca tutto il server. Regola: finché il DB è sincrono,
endpoint `def`.

---

## Insidie

- **Logica di business o query nel router**: viola i layer.
- **`response_model` riusando il `Create`**: espone campi interni.
- **Route dinamiche prima di quelle statiche**: `/summary` finisce in
  `/{item_id}`.
- **Numeri di status nudi**: usa `status.HTTP_*`.
- **`CORS allow_origins=["*"]` come soluzione definitiva**.
- **`async def` con codice bloccante** (DB sync, `requests`, I/O di file):
  blocca l'event loop.
- **`@app.on_event`**: deprecato, usa `lifespan`.
- **Nessun limite sui parametri di paginazione**: un client può chiedere tutto.
- **Eccezioni non tradotte**: un errore di dominio che arriva al client come
  `500` con dettagli interni.
