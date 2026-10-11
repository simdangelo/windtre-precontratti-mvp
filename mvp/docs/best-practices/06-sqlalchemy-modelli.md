# 06 — SQLAlchemy: i modelli

Un modello SQLAlchemy mappa una classe Python a una tabella. I modelli sono
**contenitori di dati**, non oggetti di dominio: la logica sta nei servizi.

---

## Un file per tabella

Ogni entità vive nel proprio modulo, e il package espone la facciata:

```python
# app/models/__init__.py
from app.models.category import Category
from app.models.item import Item
from app.models.types import ItemStatus
from app.models.user import User

__all__ = ["Category", "Item", "ItemStatus", "User"]
```

La `Base` è dichiarata **una sola volta**, in `app/database.py` (vedi
[05 — Database](05-database-engine-sessioni-e-postgres.md)), e importata dai
modelli. Gli enum condivisi stanno in `app/models/types.py`.

---

## Stile 2.0: `Mapped` e `mapped_column`

```python
# app/models/item.py
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.category import Category


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    category: Mapped[Category] = relationship()
```

Da leggere: `Mapped[T]` è il **tipo Python** dell'attributo; `mapped_column(...)`
è la **configurazione della colonna** (tipo DB, vincoli, default).

---

## Regole sulle colonne

- **`__tablename__` sempre esplicito** e al plurale (`items`, `categories`).
  Non affidarti al nome auto-generato.
- **La nullabilità segue l'annotazione**: `Mapped[str]` è `NOT NULL`,
  `Mapped[str | None]` è nullable. Non ripetere `nullable=False` se
  l'annotazione è già `str`.
- **Stringhe con lunghezza**: `String(255)` per campi con limite noto;
  `Text` per contenuti lunghi liberi.
- **Denaro con `Numeric(12, 2)` + `Decimal`**, mai `Float`: i float
  introducono errori di arrotondamento.
- **Date/ora timezone-aware**: `DateTime(timezone=True)` con
  `default=lambda: datetime.now(UTC)`. Mai `datetime.now()` locale naive.
- **Chiave primaria**: `int` auto-incrementale (`mapped_column(primary_key=True)`)
  oppure UUID generato **lato Python** (`default=uuid4`), non lato database, per
  restare portabili (Spanner non supporta `gen_random_uuid()`).
- **Indici** su colonne usate nei filtri/join (`index=True` o `Index(...)`).
- **`default=` vs `server_default=`**:
  - `default=` → applicato da SQLAlchemy in Python (funziona in `create_all` e
    nei test);
  - `server_default=` → scritto nel DDL, applicato dal database.
  Per `datetime.now(UTC)` si preferisce il `default` Python.

---

## Chiavi esterne e relazioni

Sono due cose separate che lavorano insieme:

- `ForeignKey("categories.id")` → vincolo **a livello database**;
- `relationship()` → navigazione **a livello Python** (`item.category`).

```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    items: Mapped[list["Item"]] = relationship(back_populates="category")


class Item(Base):
    __tablename__ = "items"
    # ...
    category: Mapped[Category] = relationship(back_populates="items")
```

**Cascade**: partire sempre dalla relazione più semplice che funziona. Il
`cascade` si aggiunge solo quando serve davvero, perché è facile cancellare (o
orfanare) figli per errore.

---

## Vincoli

`UniqueConstraint` (e `CheckConstraint`) si dichiarano in `__table_args__`:

```python
from sqlalchemy import UniqueConstraint


class Category(Base):
    __tablename__ = "categories"
    # ...
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_id"),
    )
```

Con più utenti, i vincoli di unicità diventano **composti per proprietario**:
`UNIQUE (user_id, name)`, altrimenti il primo utente blocca il nome a tutti.

---

## Enum: sì, si possono usare nelle tabelle

Sì, e nella maggior parte dei casi **si devono** usare per i campi a vocabolario
chiuso (stato, tipo, frequenza). Evitano stringhe libere e magic value, e
danno il tipo sia a Python sia al database. Ci sono però due decisioni da
prendere consapevolmente.

### 1. Definire l'enum in Python: `StrEnum`

Gli enum condivisi stanno in `app/models/types.py` e si definiscono con
`StrEnum` (Python 3.11+): il **valore** del membro è già una stringa, quindi si
serializza e si confronta senza `.value`.

```python
from enum import StrEnum, auto


class ItemStatus(StrEnum):
    DRAFT = auto()        # valore: "draft"
    PUBLISHED = auto()    # valore: "published"
    ARCHIVED = auto()     # valore: "archived"
```

> `auto()` genera valori **minuscoli** (il nome del membro in lower case). Se
> vuoi valori diversi, assegnali esplicitamente (`DRAFT = "draft"`).

### 2. Mapparlo sulla colonna: `Enum(...)`

Sul modello si usa il tipo `Enum` di SQLAlchemy con l'enum Python:

```python
from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import ItemStatus


class Item(Base):
    __tablename__ = "items"

    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, name="item_status"),
        nullable=False,
    )
```

**Per default SQLAlchemy usa un enum nativo del database** (in Postgres crea un
tipo `CREATE TYPE item_status AS ENUM (...)`). Va bene, ma ha due conseguenze:

- **`values_callable`**: con un `StrEnum` conviene forzare il salvataggio dei
  **valori** (`"draft"`) invece dei **nomi** (`"DRAFT"`), altrimenti nel DB
  finiscono stringhe maiuscole diverse da quelle che l'API usa.

```python
from enum import Enum as PyEnum

Enum(
    ItemStatus,
    name="item_status",
    values_callable=lambda e: [member.value for member in e],
)
```

- **Nativo vs non nativo**: `native_enum=False` salva un `VARCHAR` e può
  aggiungere un `CHECK` con i valori ammessi. È più portabile (Cloud Spanner
  non ha tipi enum) e più semplice da far evolvere, al costo di un controllo
  leggermente meno forte.

| | `native_enum=True` (default) | `native_enum=False` |
|---|---|---|
| Tipo nel DB | enum nativo | `VARCHAR` + eventuale `CHECK` |
| Validazione DB | forte, dal tipo | forte solo col check |
| Evolvere i valori | `ALTER TYPE` (difficile rimuovere valori) | nuovo valore = stringa nuova |
| Portabilità | bassa | alta |

**Scelta del progetto:** dato che il target potrebbe passare a Cloud Spanner,
si preferisce `native_enum=False` con `length` esplicita:

```python
status: Mapped[ItemStatus] = mapped_column(
    Enum(
        ItemStatus,
        name="item_status",
        native_enum=False,
        length=32,
        values_callable=lambda e: [member.value for member in e],
    ),
    nullable=False,
)
```

### 3. Enum o tabella di lookup?

Il campo è un **vocabolario chiuso e stabile** (stato di un'offerta, tipo di
transazione)? Enum. È un insieme **destinato a crescere** e gestito dagli utenti
(categorie, segmenti)? Tabella dedicata con FK. Criterio: l'enum va bene finché
modificarlo è una decisione di *sviluppo* (rilasci), non un'operazione di
*runtime*.

### 4. Pydantic e API

Pydantic valida l'enum sul **valore**. Nel JSON deve viaggiare `"published"`,
non `"PUBLISHED"`. Un valore fuori vocabolario produce un `422` automatico.
Esporli come enum (non come `str`) dà validazione e documentazione OpenAPI
gratis.

### Insidie sugli enum

- **Nomi vs valori**: con `StrEnum` + `auto()` il valore è minuscolo, il nome
  maiuscolo. Se il client manda `"PUBLISHED"`, la validazione fallisce.
- **`values_callable` dimenticato**: nel DB finiscono i **nomi** (`DRAFT`) e le
  query per valore non trovano nulla.
- **Enum nativo su Postgres**: rimuovere o rinominare un valore richiede
  `ALTER TYPE` e non è sempre fattibile; aggiungerlo è più semplice. Se il
  vocabolario è instabile, meglio `native_enum=False` o una lookup table.
- **Enum nativo su Spanner**: non supportato. Usa `native_enum=False`.
- **Migrazioni e enum**: le migrazioni autogenerate non rilevano bene i cambi
  ai valori di un enum; vanno revisionate a mano (in questo progetto le
  migrazioni sono fuori scope per ora).
- **Non confondere enum e tabella**: un insieme che gli utenti possono
  estendere non è un enum.

---

## I modelli sono muti

Concesso: una **proprietà derivata semplice** che calcola un valore da altri
campi.

```python
@property
def display_name(self) -> str:
    return f"{self.name} ({self.category.name})"
```

Non concesso: regole di validazione, computazioni tra entità, controlli "si può
cancellare?". Quella è logica di business e appartiene ai servizi. Un modello
grasso e un servizio passacarte è il modo in cui la logica finisce duplicata e
non testata.

> Occhio: una property che legge una relazione (`self.category.name`) può
> innescare un lazy load e quindi un **N+1** quando serializzi una lista. Vedi
> [07 — Query](07-query-sqlalchemy.md).

---

## Creazione dello schema

I modelli non creano le tabelle da soli. Due strumenti:

- `Base.metadata.create_all(engine)` → crea le tabelle dai modelli correnti.
  Comodo e veloce, **ideale per i test**. Non traccia la storia: cambiare un
  modello non altera una tabella esistente.
- **Migrazioni** → la risposta di produzione per evolvere lo schema in modo
  versionato. *In questo progetto le migrazioni sono fuori scope per ora.*

---

## Esempio completo

```python
# app/models/user.py
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
```

---

## Insidie

- **Dimenticare `__tablename__`**: SQLAlchemy inferisce un nome mai desiderato.
- **`Mapped[list[Model]]` senza pensare ai cascade**: cancellazioni a cascata
  indesiderate, o figli orfani.
- **Default mutabili**: `default=[]` è condiviso tra istanze. Usa
  `default_factory`/callable.
- **`Float` per il denaro**: usa `Numeric` + `Decimal`.
- **datetime naive**: bug di fuso orario difficili da rivedere. Sempre
  `timezone=True` + UTC.
- **Logica di business sul modello**: finisce testata da nessuna parte e
  duplicata nei servizi.
- **UUID generato dal database**: non portabile verso Spanner. Genera in Python.
- **Indici dimenticati** sulle FK usate nei filtri: query lente a volume.
