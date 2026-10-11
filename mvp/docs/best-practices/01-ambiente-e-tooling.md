# 01 — Ambiente e tooling

Questa è la base di tutto: se l'ambiente non è riproducibile e i controlli
statici non girano, ogni altra best practice è teorica. L'obiettivo è che una
macchina nuova passi da zero a "test verdi" con pochi comandi, e che l'ambiente
di produzione contenga solo ciò che serve a far girare il programma.

---

## Python e `uv`

Il progetto usa un **ambiente virtuale** (`.venv`) gestito da `uv`. L'ambiente
virtuale isola le dipendenze del progetto dal resto della macchina; `uv` lo
crea e lo ricrea a partire da un file di blocco.

### Perché `uv` e non `pip`/`poetry`

- È un singolo binario veloce (scritto in Rust) che sostituisce `pip` +
  `virtualenv` + `pip-tools`.
- Legge il `pyproject.toml` standard (PEP 621) e produce `uv.lock`.
- Distingue dipendenze runtime e di sviluppo (PEP 735), così i tool di sviluppo
  non finiscono in produzione.
- `uv run` garantisce che ogni comando usi l'ambiente giusto.

### La regola d'oro

> Mai `python` o `pip` nudi. Sempre `uv run ...`.

```bash
# CORRETTO
uv run pytest
uv run uvicorn app.main:app --reload
uv run mypy app tests

# SBAGLIATO
pytest                 # usa un interprete qualsiasi del sistema
pip install requests   # installa nell'ambiente sbagliato, aggira il lock
```

### Comandi del ciclo quotidiano

```bash
uv sync              # crea/aggiorna .venv perché combaci col lock
uv add <pacchetto>   # aggiunge una dipendenza runtime
uv add --dev <tool>  # aggiunge uno strumento di sviluppo
uv lock              # ricalcola il lockfile
uv sync --no-dev     # solo dipendenze runtime (build di produzione)
```

### `.python-version`

Il file `.python-version` fissa la versione dell'interprete che `uv` deve usare.
Va committato, così tutte le macchine usano la stessa versione. `requires-python`
nel `pyproject.toml` è il **pavimento**, non un pin: si scrive `>=3.13`, non
`==3.13`.

---

## `pyproject.toml`: un solo file di configurazione

`pyproject.toml` è la fonte di verità: metadati, dipendenze e configurazione di
**tutti** i tool. Non devono esistere file paralleli (niente `requirements.txt`,
`.flake8`, `setup.cfg`).

La struttura che seguiamo:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "windtre-sintesi-trasparenze"
version = "0.1.0"
readme = "README.MD"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.135",
    "pydantic>=2.13.5",
    "pydantic-settings>=2.13.1",
    "sqlalchemy>=2.0.52",
    # ...
]

[dependency-groups]
dev = [
    "mypy>=2.3.0",
    "pre-commit>=4.0",
    "pytest>=9.1.1",
    "ruff>=0.16.1",
    # stub di tipo per le librerie non tipizzate
    "types-requests>=2.33",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "DTZ"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.13"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

**Regole:**

- **`name` normalizzato** (minuscolo, trattini, PEP 503) e **coerente con la
  cartella del codice** dichiarata in `[tool.hatch.build.targets.wheel]`.
- **`requires-python` come pavimento** (`>=3.13`).
- **Dipendenze come intervalli** (`>=`): la versione esatta la sceglie il
  lockfile, non la si scrive a mano.
- **Un solo posto per i tool**: tutto sotto `[tool.*]`.
- **`readme` deve esistere davvero**, altrimenti l'installazione fallisce (nel
  nostro caso è `README.MD`, con l'estensione in maiuscolo).

---

## `ruff` — lint e formattazione

`ruff` fa due lavori distinti, con due comandi distinti:

```bash
uv run ruff check .   # linter: trova problemi (nomi non definiti, import inutili, pattern sospetti)
uv run ruff check . --fix  # molti problemi li corregge da solo
uv run ruff format .  # formatter: riscrive lo stile, non cambia il significato
```

### Le regole che attiviamo

| Codice | Cosa copre |
|--------|-----------|
| `E` | errori di stile pycodestyle |
| `F` | pyflakes: bug veri (import/variabili inutilizzati, nomi non definiti) |
| `I` | ordinamento degli import (assorbe isort) |
| `UP` | idiomi Python moderni (es. `X | None` invece di `Optional[X]`) |
| `B` | bugbear: pattern che profumano di bug |
| `DTZ` | datetime naive: obbliga a usare `datetime.now(UTC)` |

`line-length = 100` deve combaciare con la convenzione del progetto: se linter e
formatter dichiarano lunghezze diverse, si contraddicono.

---

## `mypy` — type checking in modalità strict

`mypy` verifica che le annotazioni di tipo siano coerenti **senza eseguire il
codice**. In modalità `strict`:

- niente `Any` implicito,
- annotazioni obbligatorie sulle funzioni,
- controllo anche sul codice non annotato delle librerie tipizzate.

```bash
uv run mypy app tests
```

Per le librerie non tipizzate servono gli **stub** (`types-requests`,
`types-openpyxl`, …) nel gruppo `dev`, altrimenti mypy segnala `import-untyped`.

**Regole:**

- Type hints su ogni firma e variabile.
- `Any` solo se davvero inevitabile, con una spiegazione.
- `# type: ignore` solo con la spiegazione del perché (idealmente con il codice
  d'errore specifico, es. `# type: ignore[call-arg]`).

---

## VS Code

Estensioni da installare:

| Estensione | ID | A cosa serve |
|-----------|----|--------------|
| Ruff | `charliermarsh.ruff` | lint + format (sostituisce Black/isort/flake8) |
| Python | `ms-python.python` | supporto linguaggio, interprete, debug |
| Mypy Type Checker | `ms-python.mypy-type-checker` | errori di tipo evidenziati nell'editor |

Configurazione consigliata (`.vscode/settings.json`, personale o di workspace):

```jsonc
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

L'estensione Ruff legge la configurazione da `pyproject.toml`: non va
replicata nei settings. Lo stesso vale per mypy.

---

## `pre-commit` — i controlli automatici prima del commit

`pre-commit` registra degli **hook Git** che girano prima di ogni commit e lo
bloccano se falliscono. Sposta la disciplina dalla memoria dello sviluppatore
all'automatismo.

Configurazione (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.1
    hooks:
      - id: ruff
      - id: ruff-format
        args: [--check]

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy app tests
        language: system
        pass_filenames: false
```

Due tipi di hook:

- **Mirror hooks** (es. ruff): pre-commit installa il tool in un ambiente
  isolato. Va bene per tool che non devono importare il progetto.
- **Hook locali** (`language: system`, es. mypy): eseguono nel tuo ambiente
  perché il type checker deve **vedere le dipendenze del progetto**.

```bash
pre-commit install              # una volta per repo, obbligatorio
uv run pre-commit run --all-files   # primo giro su tutto il codice
uv run pre-commit autoupdate    # aggiorna le revisioni degli hook
```

> `pre-commit` è il controllo **locale**; la CI (quando arriverà) è il controllo
> **autorevole**. Servono entrambi: il primo per il feedback veloce, la seconda
> perché nessuno può aggirarla.

---

## `.env` e `.env.example`

- **`.env`** contiene i valori reali (inclusi segreti) ed è **gitignorato**.
  Mai committarlo.
- **`.env.example`** è committato e documenta le variabili richieste, con valori
  vuoti o fittizi.

```bash
# .env.example
DATABASE_URL=
MS_GRAPH_TENANT_ID=
MS_GRAPH_CLIENT_ID=
MS_GRAPH_CLIENT_SECRET=
```

Per leggere queste variabili si usa `pydantic-settings` (vedi
[04 — Configurazione](04-pydantic-settings-env.md)), non `os.environ` sparso.

---

## Trade-off

- **`uv` vs `pip` nudo**: `uv` aggiunge un livello di astrazione, ma nasconde
  meno di quanto sembri — i concetti (venv, lockfile, pinning) sono gli stessi.
- **`pre-commit` vs CI**: il primo è veloce e locale ma aggirabile; la seconda è
  autorevole ma più lenta. A breve termine si parte da `pre-commit`, con la CI
  come debito da saldare.

---

## Insidie

- **Usare `python`/`pip` nudi** dopo aver adottato `uv`: si installa
  nell'interprete sbagliato o si aggira il lockfile.
- **Non committare `uv.lock`**: addio riproducibilità ("sulla mia macchina
  funziona").
- **Dimenticare `uv sync` dopo aver modificato il `pyproject.toml`**: il venv
  resta disallineato.
- **Tenere `requirements.txt` *e* `pyproject.toml`**: due fonti di verità che
  prima o poi divergono. Se ne tiene una sola.
- **`pre-commit` configurato ma non installato**: gli hook non girano e il
  commit "sporco" passa.
- **Hook con `--fix` mai eseguiti su tutto il repo**: il primo commit riscrive
  mezzo progetto. Regola: configurare, `run --all-files`, poi committare.
- **mypy senza `strict = true`**: finta sicurezza, perché il codice non
  annotato viene saltato.
- **`line-length` disallineato** tra linter e formatter: check rossi a raffica.
- **`.vscode/` committato per sbaglio**: le preferenze personali non sono
  configurazione di progetto (il `.gitignore` lo esclude già).
