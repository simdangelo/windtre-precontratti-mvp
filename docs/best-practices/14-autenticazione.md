# 14 — Autenticazione

Come si protegge una route e come si isolano i dati per utente. Il meccanismo
scelto (sessione con cookie, JWT, OIDC) è una decisione a sé; il **pattern** per
eseguirla in FastAPI è sempre lo stesso.

---

## Auth come dependency, non come middleware

Una **dependency** è per-route: la dichiari solo sulle route che la vogliono,
gira dentro il contesto della route, e in caso di fallimento produce un `401`
pulito. Un **middleware** è globale: gira per ogni richiesta, anche per login,
registrazione, health check e 404, costringendoti a elencare eccezioni.

Il pattern idiomatico: **auth come dependency**, middleware solo per
preoccupazioni di trasporto che valgono per tutto (logging, header di sicurezza,
allow-list host).

---

## La dependency "utente corrente"

Una funzione che legge la credenziale dalla `Request` (cookie o header), risolve
l'utente e lo ritorna; se non c'è, solleva `401`.

```python
# app/api/dependencies.py
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import get_user_by_token

SESSION_COOKIE_NAME = "session_token"


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_by_token(db, token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

Ogni route protetta diventa minimale:

```python
@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user
```

> Le route che **non** dichiarano la dependency sono pubbliche. È un vantaggio,
> ma è anche il rischio: dimenticarla su una route privata la lascia aperta.

---

## Cookie di sessione vs JWT

Due meccanismi, due trade-off.

### Sessione lato server + cookie opaco (scelta del riferimento pynance)

- Al login si genera un token casuale (`secrets.token_urlsafe(32)`) e lo si
  salva in una tabella `sessions` con scadenza.
- Il browser riceve il token in un **cookie `HttpOnly`**.
- A ogni richiesta la dependency cerca la sessione nel database.

Vantaggi: revoca immediata (cancelli la riga), il token non contiene dati,
niente segreti nel client. Costo: una query per richiesta e una tabella in più.

### JWT (scelta del tutorial)

- Al login si firma un token con i claim (`sub`, `exp`).
- Il client lo rimanda in `Authorization: Bearer <token>`.
- La dependency verifica firma e scadenza.

Vantaggi: stateless, nessuna query per validare, scala su più servizi. Costi:
non revocabile senza blacklist, il contenuto è leggibile (firmato, non cifrato),
richiede gestione della chiave.

### Quale scegliere

Per un'app con un backend e dati per-utente, la **sessione con cookie
`HttpOnly`** è più semplice e più sicura dal punto di vista del client (il
JavaScript non tocca mai il token, quindi niente XSS che lo ruba). I JWT
convengono in architetture distribuite/stateless.

### Cookie: i flag da non dimenticare

```python
response.set_cookie(
    key=SESSION_COOKIE_NAME,
    value=session.token,
    httponly=True,          # JavaScript non può leggerlo -> mitiga XSS
    secure=settings.secure_cookies,  # solo HTTPS in produzione
    samesite="lax",         # mitigazione CSRF
    max_age=settings.access_session_expire_days * 24 * 60 * 60,
)
```

- `HttpOnly`: obbligatorio.
- `Secure`: obbligatorio in produzione (HTTPS).
- `SameSite`: `lax` come default ragionevole.
- Il **nome del cookie** è una costante definita una volta e condivisa tra chi
  lo imposta (login) e chi lo legge (dependency): se divergono, il login
  "funziona" ma nessuna route riconosce la sessione.

---

## Hashing delle password

Mai testo in chiaro, mai hash veloci e datati (`md5`, `sha1`, `sha256` nudo).
Si usa una libreria dedicata con algoritmo moderno (Argon2id via `pwdlib`):

```python
# app/services/security.py
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)
```

La verifica usa un confronto a tempo costante interno alla libreria: non
confrontare le stringhe con `==`.

---

## Scoping dei dati per utente

Il problema di sicurezza più importante non è il login: è che **i dati di un
utente non finiscano mai in mano a un altro**. Ogni entità posseduta ha una
colonna `user_id` (FK verso `users`).

Tre regole per ogni operazione:

- **Create** — `user_id` dal token, **mai** dal body della richiesta. Il client
  non sceglie di chi è una riga.
- **Read / List** — `WHERE user_id = :current_user_id` **sempre**, anche nei
  join.
- **Update / Delete** — cerca la riga già filtrata per proprietario: se non
  esiste (perché non è tua, o perché non c'è), comportati come se non esistesse.

**404, non 403**: per dati privati, "non è tuo" si tratta come "non esiste", così
non si rivela l'esistenza della riga. Il `403` va bene solo se l'esistenza
dell'entità non è informazione sensibile.

**Attenzione ai riferimenti**: se `create` accetta un `category_id` dal body,
devi verificare che **anche quella categoria** appartenga all'utente —
altrimenti si agganciano dati a entità altrui.

---

## Verso l'SSO aziendale (OIDC)

La roadmap del progetto prevede autenticazione OIDC/SSO aziendale. Quando
arriverà, il pattern non cambia: cambia solo **cosa** legge la dependency.

- Invece del cookie, si verifica un **JWT** (firma tramite JWKS dell'identity
  provider, controllo di `exp` e issuer).
- I **gruppi** del token (es. `g-very-mobile`) si mappano ai segmenti
  autorizzati.
- Lo **scoping per segmento** diventa un filtro obbligatorio in ogni query,
  esattamente come lo scoping per utente.

Gli helper `python-jose`/`PyJWT` servono solo a questo punto; il confine
(router con `CurrentUser`, servizi scoped) resta identico.

---

## Test dell'autenticazione

Nei test si può:

- **sovrascrivere la dependency** con `app.dependency_overrides` per iniettare un
  utente finto, oppure
- **percorrere il flusso vero**: registra, fai login, usa il cookie.

Il secondo modo esercita davvero l'auth ed è preferibile per i test
end-to-end; il primo è utile per i test mirati su un aspetto diverso
dell'autenticazione.

---

## Insidie

- **Route private senza la dependency**: restano pubbliche per dimenticanza.
- **`user_id` preso dal body** nella create: un utente crea righe per un altro.
- **`WHERE user_id` dimenticato** in una query isolata: fuga di dati.
- **Password in chiaro o hash deboli**.
- **Confronto password con `==`**: timing attack.
- **Cookie senza `HttpOnly`/`Secure`**: XSS e invio su HTTP.
- **Nome del cookie duplicato** in login e dependency, con valori divergenti.
- **`403` dove serve `404`**: rivela l'esistenza di dati altrui.
- **Segreti di firma con default** nel codice (JWT): chiave nota = token
  falsificabili.
