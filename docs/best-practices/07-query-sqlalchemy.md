# 07 — Query con SQLAlchemy

Come si interroga il database nello stile 2.0, quali pattern seguire e i due
trabocchetti che causano più danni: N+1 e `db.query()`.

---

## Lo stile 2.0: `select()` + `execute()`

`db.query()` è legacy. Il modo 2.0 costruisce uno statement e lo esegue:

```python
from sqlalchemy import select

item = db.execute(
    select(Item).where(Item.id == item_id, Item.user_id == user_id)
).scalar_one_or_none()

items = db.execute(
    select(Item).where(Item.user_id == user_id).order_by(Item.created_at.desc())
).scalars().all()
```

### Come estrarre il risultato

| Metodo | Quando |
|--------|--------|
| `.scalar_one_or_none()` | cerchi una riga che può non esistere (lookup) |
| `.scalar_one()` | sai che esiste e deve essere unica (altrimenti errore) |
| `.scalars().all()` | lista di entità |
| `.all()` | lista di tuple (colonne/aggregati) |
| `.scalar()` | un singolo valore scalare (es. `func.count()`) |

---

## Filtri

I `.where()` si concatenano in **AND implicito**:

```python
query = (
    select(Item)
    .where(Item.user_id == user_id)
    .where(Item.status == ItemStatus.PUBLISHED)
)
```

Per OR e condizioni composte si usa `or_`/`and_` **di SQLAlchemy**:

```python
from sqlalchemy import and_, or_

conditions = [Item.user_id == user_id]
if filters.q:
    conditions.append(Item.name.ilike(f"%{filters.q}%"))
if filters.category_id:
    conditions.append(Item.category_id == filters.category_id)

query = select(Item).where(*conditions)
```

> **Trappola:** l'`and`/`or` di Python **non costruiscono SQL**.
> `(Item.a == 1) and (Item.b == 2)` valuta la verità degli oggetti in Python e
> produce filtri sbagliati (spesso vuoti). Passa le condizioni come argomenti
> separati a `.where()` (AND) o usa `and_`/`or_`.

Altri operatori utili: `.in_(lista)`, `.is_(None)` (mai `== None`),
`.ilike("%x%")` per ricerca case-insensitive.

---

## Join e aggregazioni

```python
from sqlalchemy import func

rows = db.execute(
    select(Category.name, func.sum(Item.amount))
    .join(Category, Item.category_id == Category.id)
    .where(Item.user_id == user_id)
    .group_by(Category.name)
).all()
```

Regole:

- Ogni colonna non aggregata nel `SELECT` deve comparire nel `GROUP BY`,
  altrimenti Postgres rifiuta la query.
- `func.sum`, `func.count`, `func.extract("year", ...)` sono i mattoni dei
  report.
- Per contare in una paginazione: `select(func.count()).select_from(Item).where(...)`.

---

## Filtri per intervallo di date (index-friendly)

Meglio confrontare le date con un intervallo calcolato in Python che usare
`extract` in `WHERE`:

```python
first_day = date(year, month, 1)
next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
first_day_next_month = date(next_year, next_month, 1)

conditions = [
    Item.user_id == user_id,
    Item.created_at >= first_day,
    Item.created_at < first_day_next_month,
]
```

`extract('month', ...)` in `WHERE` impedisce l'uso dell'indice; il confronto
diretto lo sfrutta.

---

## Eager loading e il problema N+1

Le relazioni SQLAlchemy sono **lazy** per default: `item.category` esegue una
query alla prima lettura. In un loop su una lista, questo diventa 1 + N query:

```python
# N+1
items = db.execute(select(Item)).scalars().all()
for i in items:
    print(i.category.name)   # una query per item!
```

La correzione è il **eager loading** con `selectinload` (una seconda query
`IN (...)`, costo fisso):

```python
from sqlalchemy.orm import selectinload

items = db.execute(
    select(Item).options(selectinload(Item.category)).where(Item.user_id == user_id)
).scalars().all()
```

| Strategia | Cosa fa | Quando |
|-----------|---------|--------|
| lazy (default) | carica all'accesso | oggetto singolo, relazione raramente letta |
| `selectinload` | seconda query `IN (...)` | **liste** di oggetti di cui leggi la relazione |
| `joinedload` | JOIN nella stessa query | quando serve sempre, risultati piccoli |

> **Firma dell'N+1**: un accesso a relazione dentro un `for` su oggetti ORM.
> Attenzione alle **property derivate** che leggono relazioni: l'N+1 si nasconde
> dietro un `item.display_name` che sembra un campo normale.

Per accorgersene: `create_engine(url, echo=True)` stampa ogni query; conta le
righe per richiesta. Un'alternativa è asserire il numero di query nei test.

---

## Paginazione

```python
query = (
    select(Item)
    .where(Item.user_id == user_id)
    .order_by(Item.created_at.desc())
    .offset(skip)
    .limit(limit)
)
```

Per un totale affidabile serve una seconda query di `count`. `skip`/`limit`
devono avere limiti massimi validati a livello di endpoint (vedi
[11 — Router](11-fastapi-router-ed-endpoint.md)).

---

## SQL grezzo

Da evitare per il CRUD: perdi tipi, eager loading e portabilità. Quando serve
(caso raro), usa `text()` con **parametri legati**, mai concatenazione di
stringhe (SQL injection):

```python
from sqlalchemy import text

db.execute(
    text("SELECT * FROM items WHERE user_id = :uid"),
    {"uid": user_id},
)
```

---

## Selezione delle colonne

Per liste che servono solo pochi campi, seleziona le colonne invece dell'intera
entità: meno dati trasferiti e meno oggetti da idratare.

```python
rows = db.execute(select(Item.id, Item.name).where(Item.user_id == user_id)).all()
```

Per il CRUD che poi modifica l'entità, invece, serve l'oggetto completo.

---

## Insidie

- **`db.query()`**: stile legacy, `Result` diverso. Usa `db.execute(select(...))`.
- **`and`/`or` di Python nelle condizioni**: filtrano in Python invece che in
  SQL, con risultati sbagliati.
- **N+1 per lazy load**: la lista è lenta solo a volume, invisibile in review.
- **`== None`**: usa `.is_(None)`.
- **Colonne selezionate senza `GROUP BY`**: errore Postgres.
- **`extract` in `WHERE` su date**: niente indice.
- **`limit` senza massimo**: un client scarica l'intera tabella.
- **SQL costruito per concatenazione**: SQL injection.
- **Filtri non scoped per utente/segmento**: fuga di dati (vedi
  [14 — Autenticazione](14-autenticazione.md)).
