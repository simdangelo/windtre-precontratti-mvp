# 04 — Configurazione con pydantic-settings

Come si legge la configurazione dell'applicazione: un unico oggetto tipizzato,
validato all'avvio, popolato da variabili d'ambiente e da un file `.env`.

---

## Perché non `os.environ` sparso

L'accesso grezzo alle variabili d'ambiente si sparpaglia in tutto il codice:

```python
# in giro per il progetto, non verificato
import os

engine = create_engine(os.environ["DATABASE_URL"])
secret = os.environ["SECRET_KEY"]
```

Problemi: ogni valore è una stringa (niente tipi), un refuso nella chiave
esplode solo a runtime, non c'è un posto unico che elenca *quale* configurazione
esiste, e i segreti finiscono facilmente nei log.

Un oggetto `Settings` risolve tutto:

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: SecretStr
    debug: bool = False


settings = Settings()
```

Ora `settings.database_url` è una `str` che sai esistere (la validazione gira
all'import), `settings.secret_key` è una `SecretStr` che si redige da sola, e i
type checker conoscono il tipo di ogni setting.

---

## Come funziona

- Ogni campo mappa una variabile d'ambiente con lo stesso nome
  (case-insensitive).
- `env_file=".env"` fa leggere anche dal file `.env`; le variabili d'ambiente
  reali hanno precedenza.
- Un campo **senza default e senza valore → errore di validazione all'import**.
  È la feature che intercetta subito una `DATABASE_URL` mancante.
- I campi opzionali hanno un default.

### Precedenza

```
variabili d'ambiente reali  >  file .env  >  default della classe
```

Questo è esattamente ciò che serve nei test: basta impostare una variabile
d'ambiente per sovrascrivere il `.env` senza toccare file.

### `SecretStr`

Credenziali e API key vanno tipizzate `SecretStr`, non `str`: la stampa mostra
`**********` e il valore reale si ottiene solo esplicitamente con
`.get_secret_value()`.

```python
from pydantic import SecretStr

db_password: SecretStr

# ...
raw = settings.db_password.get_secret_value()
```

---

## Struttura nel progetto

```python
# app/config.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+psycopg://app_user:password@localhost:5432/app_db"

    # Microsoft Graph / OneDrive (opzionali: se assenti si usa il fallback)
    ms_graph_tenant_id: str = ""
    ms_graph_client_id: str = ""
    ms_graph_client_secret: SecretStr = SecretStr("")
    ms_graph_drive_id: str = ""

    # Applicazione
    debug: bool = False
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]


settings = Settings()
```

La **proprietà calcolata** è utile quando la stessa configurazione arriva in
forme diverse da ambienti diversi (es. un unico `DATABASE_URL` in produzione e
variabili `POSTGRES_*` in locale):

```python
class Settings(BaseSettings):
    postgres_user: str = ""
    postgres_password: SecretStr = SecretStr("")
    postgres_host: str = ""
    postgres_port: str = ""
    postgres_db: str = ""
    database_url_env: str = Field(default="", validation_alias="DATABASE_URL")

    @property
    def database_url(self) -> str:
        if self.database_url_env:
            # normalizza lo schema del driver atteso dall'app
            if self.database_url_env.startswith("postgresql://"):
                return self.database_url_env.replace(
                    "postgresql://", "postgresql+psycopg://", 1
                )
            return self.database_url_env
        return (
            f"postgresql+psycopg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
```

`validation_alias="DATABASE_URL"` permette di tenere il nome del campo in
minuscolo (convenzione Python) mappando la variabile d'ambiente in maiuscolo.

---

## Dove vive il `.env`

`pydantic-settings` legge `.env` **relativamente alla working directory**: il
file deve stare dove gira l'applicazione (radice del progetto). Il `.env` è
**gitignorato** perché contiene segreti; si committa solo `.env.example` con le
chiavi e valori fittizi.

```bash
# .env.example — committato
DATABASE_URL=
MS_GRAPH_TENANT_ID=
MS_GRAPH_CLIENT_ID=
MS_GRAPH_CLIENT_SECRET=
MS_GRAPH_DRIVE_ID=
```

---

## Trade-off

- **`pydantic-settings` vs `os.environ`**: tipizzato, validato, centralizzato e
  auto-documentante. Scelta standard per FastAPI.
- **`pydantic-settings` vs file di config YAML/TOML**: le variabili d'ambiente
  sono la via 12-factor, si passano bene ai container, e non finiscono
  committate. I file di config tendono a derivare tra ambienti e sono lo
  strumento sbagliato per i segreti.
- **`pydantic-settings` vs `python-dotenv` da solo**: `python-dotenv` carica
  `.env` in `os.environ`, senza tipi né validazione. `pydantic-settings` parte
  dalla stessa idea e ci mette sopra la validazione Pydantic.

---

## Insidie

- **Campo obbligatorio mancante → l'app muore all'import.** È il comportamento
  corretto, ma va previsto: `.env` o variabili d'ambiente devono esistere prima
  che qualsiasi cosa giri.
- **Dimenticare un campo in `Settings`**: resta invisibile all'app. La classe è
  il contratto; ogni variabile usata va dichiarata.
- **Default per un segreto**: mai dare un default che finisce committato a una
  chiave reale. I segreti sono obbligatori (nessun default) o vuoti.
- **`.env` committato**: fuga di segreti.
- **Credenziale tipizzata `str`** invece di `SecretStr`: la redazione salta.
- **`import os` + `load_dotenv()` sparso**: il refactor lo elimina a favore di
  `app.config.settings`.
- **Leggere `settings` a livello di modulo ma modificarlo nei test**: essendo un
  singleton, le modifiche si propagano. Nei test si sovrascrivono le variabili
  d'ambiente **prima** dell'import (vedi [13 — Testing](13-testing-pytest.md)).
- **Path di `.env` relativo alla CWD**: se l'app viene lanciata da un'altra
  directory il file non si trova. Lancia sempre dalla radice del progetto.
