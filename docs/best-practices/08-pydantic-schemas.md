# 08 — Pydantic: gli schemas

Pydantic definisce gli **schemas**: modelli tipizzati che validano l'input e
modellano l'output dell'API. Sono il contratto tra il mondo esterno e il codice.

---

## Cosa fa Pydantic

Trasforma una dichiarazione di classe in un **validatore**: alla costruzione,
ogni campo viene controllato contro la sua annotazione e convertito dove ha
senso.

```python
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    quantity: int


item = Item(name="book", quantity="3")  # "3" -> 3 (coercizione)
```

- Tipo sbagliato non convertibile → `ValidationError`.
- Campi mancanti obbligatori → errore immediato.
- Campi extra ignorati di default (v2).

In FastAPI, un input che non valida produce automaticamente `422 Unprocessable
Entity`: non serve scrivere codice per gli errori di **forma**.

---

## La convenzione Base / Create / Update / Response

```python
from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ItemCreate(ItemBase):
    category_id: int


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None


class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
```

| Schema | Ruolo |
|--------|-------|
| `Base` | campi condivisi |
| `Create` | cosa l'API accetta in creazione (mai `id`/timestamp) |
| `Update` | tutti i campi opzionali (aggiornamento parziale) |
| `Response` | cosa l'API restituisce, con `from_attributes=True` |

Questa separazione impedisce al client di impostare campi che non gli
competono (`id`, `created_at`) e impedisce di far trapelare interni.

---

## `from_attributes` — dagli oggetti ORM alla risposta

```python
class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
```

Con `from_attributes=True`, `ItemResponse.model_validate(item_orm)` legge `.id`
e `.name` dall'oggetto ORM. È la cucitura tra modello SQLAlchemy e schema di
risposta: FastAPI la usa per serializzare automaticamente quando dichiari
`response_model`.

Senza `from_attributes=True`, `model_validate(oggetto_orm)` fallisce e saresti
costretto a costruire dizionari a mano.

---

## Aggiornamenti parziali: `exclude_unset`

```python
# nel servizio
for field, value in update.model_dump(exclude_unset=True).items():
    setattr(item, field, value)
```

`model_dump(exclude_unset=True)` restituisce **solo i campi che il chiamante ha
davvero fornito**. È il trucco standard per il PATCH: sai *cosa* è cambiato e
scrivi solo quello, senza sovrascrivere con `None` i campi non inviati.

---

## Vincoli e tipi

```python
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    owner_email: EmailStr
```

- `Field(...)` dichiara i vincoli accanto all'annotazione.
- `EmailStr` richiede l'extra `pydantic[email]` (`email-validator`).
- `default_factory=list` per i default mutabili (mai `default=[]`).
- Il denaro si costruisce da stringhe: `Decimal("12.34")`, mai da float.

---

## Una facciata come per i modelli

Un file per entità (`schemas/item.py`, `schemas/category.py`), ed
`__init__.py` che ri-esporta:

```python
# app/schemas/__init__.py
from app.schemas.category import CategoryCreate, CategoryResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

__all__ = [
    "CategoryCreate",
    "CategoryResponse",
    "ItemCreate",
    "ItemResponse",
    "ItemUpdate",
]
```

---

## Trade-off

- **Schemi separati vs un unico modello per tutto**: separare richiede più
  classi ma protegge da input malevoli e da output che espone interni. Per
  un'app reale è il default.
- **Coercizione vs strict**: Pydantic v2 converte (`"3"` → `3`), comodo al
  confine API. Dove la coercizione è pericolosa si usa `Field(strict=True)`.

---

## Insidie

- **`from_attributes` dimenticato su un response schema**: `model_validate`
  fallisce.
- **Riusare `Create` come `Response`**: il client può impostare `id`/timestamp e
  si espongono campi interni.
- **Default mutabili**: `Field(default=[])` condivide la stessa lista tra
  istanze. Sempre `default_factory`.
- **Pensare che Pydantic rivalidi a ogni assegnazione**: valida alla
  costruzione, non su `item.name = 123` (a meno di `validate_assignment=True`).
- **`Decimal` da float**: `Decimal(12.34)` reintroduce l'errore del float. Da
  stringa: `Decimal("12.34")`.
- **Nome di campo uguale a un tipo importato** (es. `date: date | None = None`):
  con la valutazione lazy delle annotazioni può rompersi all'import. Evita di
  chiamare i campi come i tipi (`date`, `type`, ...).
- **`StrEnum` validato sul valore**: JSON deve mandare `"published"`, non
  `"PUBLISHED"`.
- **Response schema usato come input del servizio**: gli schemas di risposta
  sono solo per l'API; i servizi ricevono i `*Create`/`*Update` e ritornano
  modelli ORM o tipi propri.
