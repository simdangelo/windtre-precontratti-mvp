# 10 — Service layer

Lo strato dei servizi contiene la **logica di business**: le regole
dell'applicazione. È il cuore del backend e deve poter essere letto, testato e
riusato senza sapere nulla di HTTP.

---

## Cos'è un servizio

Una funzione (o un piccolo gruppo di funzioni) che implementa un **caso d'uso**:

```python
# app/services/item.py
from sqlalchemy.orm import Session

from app.models import Item
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.exceptions import CategoryNotFoundError


def create_item(db: Session, user_id: int, data: ItemCreate) -> Item:
    category = db.get(Category, data.category_id)
    if category is None or category.user_id != user_id:
        raise CategoryNotFoundError(f"Category {data.category_id} doesn't exist")

    item = Item(
        name=data.name,
        category_id=data.category_id,
        user_id=user_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
```

Caratteristiche:

- Riceve la `Session` e dati **già validati** (schemas `*Create`/`*Update`).
- Applica le regole e accede al database direttamente (niente repository layer).
- Ritorna un modello ORM (per il CRUD) o un tipo proprio (per i report).
- **Non importa FastAPI** e non solleva `HTTPException`.

---

## Le regole

1. **Nessun import di FastAPI.** Un servizio non deve sapere che esiste un server
   web: altrimenti non è più chiamabile da un test diretto, da uno script, da un
   job in background.
2. **Nessuna risposta HTTP.** Le eccezioni sono di **dominio**
   (`ItemNotFoundError`), non `HTTPException`. La traduzione avviene nel router.
3. **La `Session` è un parametro**, non un oggetto globale. Il servizio non crea
   né chiude sessioni.
4. **Il servizio committa** (Option B, vedi
   [05 — Database](05-database-engine-sessioni-e-postgres.md)) e fa `refresh`
   di ciò che ritorna.
5. **Un servizio per caso d'uso**, non un "god object" con venti metodi.

---

## Naming

Rispetta la convenzione CRUD e report (vedi
[03 — Struttura](03-struttura-a-strati-e-package.md)):

```python
create_item(db, user_id, data)
get_item(db, user_id, item_id)
list_items(db, user_id, filters)
update_item(db, user_id, item_id, data)
delete_item(db, user_id, item_id)

get_summary(db, user_id, month, year)
get_summary_by_category(db, user_id, item_type, month, year)
```

I **filtri** di una lista si raggruppano in una dataclass per non avere dieci
parametri sparsi:

```python
from dataclasses import dataclass


@dataclass
class ItemFilters:
    q: str | None = None
    category_id: int | None = None
    year: int | None = None


def list_items(db: Session, user_id: int, filters: ItemFilters) -> list[Item]:
    ...
```

---

## Eccezioni di dominio

Le eccezioni vivono in `app/services/exceptions.py`, una classe per condizione:

```python
class ItemNotFoundError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class DuplicateItemError(Exception):
    pass
```

Perché eccezioni e non `None`: il nome dice **quale regola** è stata violata,
senza che il chiamante debba interpretare un valore sentinella (un `None` è "non
trovato" o "risultato valido ma vuoto"?).

> Progettazione completa (naming, gerarchia, contesto, testing):
> [09 — Eccezioni personalizzate](09-eccezioni-personalizzate.md).

---

## Il database come garante: EAFP

Alcune regole non si affidano solo al controllo preventivo nel codice, perché
questo lascia aperta una **race condition**: tra il controllo "esistono righe
collegate?" e la cancellazione, un'altra richiesta può inserirne una. L'unica
garanzia atomica è il **vincolo del database** (es. foreign key senza cascade).

Il pattern conseguente è **EAFP** (Easier to Ask Forgiveness than Permission):
si tenta l'operazione e, se il database la rifiuta, si traduce l'errore di
integrità in un'eccezione di dominio.

```python
from sqlalchemy.exc import IntegrityError

from app.services.exceptions import CategoryHasItemsError


def delete_category(db: Session, user_id: int, category_id: int) -> None:
    category = get_category(db, user_id, category_id)  # 404 se non esiste
    db.delete(category)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise CategoryHasItemsError(
            f"Category {category_id} has items and can't be deleted"
        ) from e
```

Regola pratica: l'**esistenza** si controlla prima con una query (per
distinguere 404 da 409); la **regola di integrità** la fa rispettare il
database.

---

## Cosa ritornano i servizi

- **CRUD** → il modello ORM (`Item`). FastAPI lo serializza con lo schema di
  risposta.
- **Report** → una **dataclass** propria (o `NamedTuple`), non uno schema
  Pydantic. Gli schemas di risposta sono solo per l'API e non devono entrare
  nel livello dati.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Summary:
    income: Decimal
    expense: Decimal
```

Il router mappa poi `Summary` → `SummaryResponse`.

---

## Perché non mettere la logica nel modello o nel router

- Nel **modello** → diventa un "modello grasso" e il servizio un passacarte; la
  regola finisce duplicata e testata da nessuna parte.
- Nel **router** → la logica si lega all'HTTP e non è più riusabile né testabile
  in isolamento; il router smette di essere un traduttore sottile.

Il test attraverso l'HTTP (vedi [13 — Testing](13-testing-pytest.md)) verifica
la regola *attraverso* il servizio, senza bisogno di doppioni.

---

## Esempio di report con join e aggregazione

```python
def get_summary_by_category(
    db: Session, user_id: int, item_type: str, month: int, year: int
) -> list[SummaryByCategoryRow]:
    first_day = date(year, month, 1)
    next_month = date(year + (month // 12), (month % 12) + 1, 1)

    rows = db.execute(
        select(Category.id, Category.name, func.sum(Item.amount))
        .join(Category, Item.category_id == Category.id)
        .where(
            Item.user_id == user_id,
            Item.created_at >= first_day,
            Item.created_at < next_month,
            Category.item_type == item_type,
        )
        .group_by(Category.id, Category.name)
    ).all()

    return [SummaryByCategoryRow(cid, name, total) for cid, name, total in rows]
```

Dettagli SQL in [07 — Query](07-query-sqlalchemy.md).

---

## Insidie

- **`HTTPException` nel servizio**: accoppia la logica al trasporto.
- **Importare FastAPI** per `BackgroundTasks` o simili nel servizio: spezza il
  confine. Le dipendenze web restano nel router.
- **Query nel router "per comodità"**: viola il layer boundary.
- **Commit in più punti** (servizio + dependency): doppio commit.
- **Servizio che ritorna un response schema**: lo schema API entra nel dominio.
- **Eccezioni generiche** (`ValueError`): il router non sa come tradurle.
- **Dimenticare il `rollback`** dopo un errore di commit: la sessione resta
  incoerente e avvelena la richiesta successiva.
