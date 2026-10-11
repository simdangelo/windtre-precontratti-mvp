# 09 — Eccezioni personalizzate

Come si progettano le eccezioni di dominio: perché esistono, dove vivono, come
si nominano, come si propagano tra gli strati e come si traducono in risposte
HTTP. Approfondimento di quanto introdotto in
[10 — Service](10-services.md) e [12 — Gestione errori](12-gestione-errori.md).

---

## Perché eccezioni dedicate e non `ValueError` / `None`

Il modo più ingenuo di segnalare un fallimento è restituire `None` o sollevare
un `ValueError`. Entrambi perdono informazione:

- `None` è ambiguo: "non trovato" o "risultato valido ma vuoto"? Chi chiama deve
  indovinare, e un equivoco fa arrivare un `404` dove serviva una lista vuota.
- `ValueError` è un nome generico: chi lo intercetta non sa **quale** regola è
  stata violata, quindi non sa tradurlo nel codice giusto.

Un'eccezione di dominio risolve entrambi: ha un **nome che è la regola**, e non
è un valore sentinella da interpretare.

```python
# ambiguo
def get_item(db, item_id) -> Item | None: ...

# esplicito
def get_item(db, item_id) -> Item:
    item = ...
    if item is None:
        raise ItemNotFoundError(f"Item {item_id} doesn't exist")
    return item
```

---

## Naming

Convenzione: `<Entity><Condition>Error`.

| Situazione | Eccezione |
|-----------|-----------|
| entità assente | `ItemNotFoundError` |
| duplicato | `DuplicateItemError` |
| riferimento esterno assente | `CategoryNotFoundError` |
| vincolo di integrità | `CategoryHasItemsError` |
| credenziali errate | `InvalidCredentialsError` |
| stato non valido per l'operazione | `ItemAlreadyPublishedError` |

Regole:

- Suffisso `Error` (non `Exception`) e nome **specifico**, non generico.
- Il nome descrive la **regola violata**, non il meccanismo.
- Un'eccezione per condizione distinta: se il router deve rispondere con due
  status diversi, servono due eccezioni.

---

## Dove vivono

In un unico modulo, `app/services/exceptions.py`, accanto agli altri elementi
condivisi del dominio. Non sparse nei file dei servizi: chi deve tradurle le
importa da un posto solo.

```python
# app/services/exceptions.py
class ItemNotFoundError(Exception):
    pass


class DuplicateItemError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class CategoryHasItemsError(Exception):
    pass
```

Il modulo è importabile dal router (che deve tradurre) e dai test, senza
introdurre dipendenze verso l'alto.

---

## Gerarchia: piatta o con una base comune?

Entrambe le forme sono legittime. Il trade-off:

- **Classi piatte** (solo `Exception` come base): semplici, e la traduzione nel
  router è un `except` per condizione. È ciò che basta quando ogni errore ha un
  handler specifico. È l'approccio di pynance.
- **Base comune** (`class DomainError(Exception)` da cui ereditano tutte): utile
  quando vuoi **intercettare in un punto solo** tutte le eccezioni di dominio —
  per esempio un `@app.exception_handler(DomainError)` o un `except DomainError`
  in un layer di frontiera — senza elencarle una a una.

La nostra indicazione: **parti piatto**. Introduci una base comune solo se
compare un bisogno reale di catturare l'intera famiglia. Non costruire
gerarchie profonde "per eleganza": ogni livello in più è manutenzione.

```python
# quando/ se serve una base comune
class DomainError(Exception):
    """Base per le eccezioni di dominio."""


class ItemNotFoundError(DomainError):
    pass


# handler globale
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    ...
```

> Una base comune non deve diventare un albero. Due livelli (base + foglie)
> bastano; se ti ritrovi con `ServiceError → EntityError → ItemError →
> ItemNotFoundError`, hai introdotto un tassonomia da riscrivere.

---

## Portare contesto

Un'eccezione può trasportare dati utili alla traduzione o al logging (l'id
dell'entità, il campo violato), senza però diventare un contenitore di
messaggi per l'utente finale. Il messaggio resta per gli sviluppatori; la
risposta HTTP la costruisce il router.

```python
class DuplicateItemError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Item '{name}' already exists")
```

Attenzione a **non mettere segreti o PII** nel messaggio: un'eccezione non
gestita può finire nei log (o, peggio, in una risposta se il messaggio viene
propagato).

---

## Catturare, rilanciare, concatenare

- **Rilancia** con `raise ... from e` per preservare la causa originale:

```python
from sqlalchemy.exc import IntegrityError

try:
    db.commit()
except IntegrityError as e:
    db.rollback()
    raise DuplicateItemError(name) from e
```

- **Non catturare e ignorare**: `except Exception: pass` nasconde i bug.
- **Cattura il più specifico possibile**: `except CategoryNotFoundError`, non
  `except Exception`.
- **Non usare le eccezioni per il flusso normale**: un caso previsto e
  frequente (es. "lista vuota") è un valore di ritorno, non un errore.

---

## La traduzione al confine

Le eccezioni di dominio **non conoscono l'HTTP**. Il router le traduce in
`HTTPException`, una corrispondenza 1:1:

```python
try:
    return item_service.delete_category(db, current_user.id, category_id)
except CategoryNotFoundError as e:
    raise HTTPException(status_code=404, detail="Category doesn't exist") from e
except CategoryHasItemsError as e:
    raise HTTPException(status_code=409, detail="Category has items") from e
```

| Eccezione di dominio | HTTP |
|----------------------|------|
| `XNotFoundError` | `404` |
| `DuplicateXError` | `409` |
| `XHasDependenciesError` | `409` |
| `InvalidCredentialsError` | `401` |
| `XNotAllowedError` | `403` (solo se l'esistenza non è sensibile; altrimenti `404`) |

Se il servizio solleva `HTTPException` direttamente, l'eccezione perde il suo
valore: la logica non è più riusabile fuori dal contesto web. Vedi
[10](10-services.md) e [12](12-gestione-errori.md).

---

## Testare le eccezioni

- **A livello di servizio** (se testi direttamente): `pytest.raises`.

```python
def test_get_item_missing_raises(db_session):
    with pytest.raises(ItemNotFoundError):
        item_service.get_item(db_session, user_id=1, item_id=9999)
```

- **A livello HTTP** (strategia principale del progetto): non interessa *quale*
  eccezione è stata sollevata, ma **il comportamento**: la richiesta produce
  `404`.

```python
def test_get_item_missing_returns_404(client):
    assert client.get("/api/items/9999").status_code == 404
```

Il secondo test è più robusto: non si rompe se domani il servizio solleva
un'eccezione diversa ma con lo stesso esito HTTP.

---

## Insidie

- **Nomi generici** (`ValueError`, `AppError`): la traduzione non può essere
  specifica.
- **Una sola eccezione per troppe condizioni**: il router non può distinguere
  `404` da `409`.
- **Gerarchie profonde**: cerimonia senza ritorno; due livelli bastano.
- **`HTTPException` nel servizio**: accoppia la logica al trasporto.
- **Perdere la causa** (`raise XError("...")` senza `from e`): debugging difficile.
- **Messaggi con segreti o PII**, poi loggati o propagati.
- **`except Exception: pass`** o `except` troppo ampi: nascondono i bug.
- **Eccezioni per il flusso normale**: un caso previsto è un valore, non un
  errore.
- **Eccezioni definite nel router**: la logica di dominio non deve dipendere
  dalla presentazione per esistere.
