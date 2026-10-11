# 02 — Git e commit convention

La cronologia di un repository è documentazione: serve a capire *perché* una
riga di codice esiste, a fare `git bisect`, a generare changelog. Una
convenzione **leggera** basta a renderla utile senza trasformare ogni commit in
burocrazia.

---

## La convenzione: Conventional Commits (leggera)

Formato:

```
<type>(<scope>): <subject>

[corpo opzionale]

[footer opzionale]
```

Esempi:

```
feat(offers): add bulk update endpoint
fix(database): rollback session on IntegrityError
refactor(models): split offer model into one file per entity
docs(best-practices): document test strategy
test(offers): cover 404 on unknown segment
chore(deps): bump fastapi to 0.135
```

### I `type` ammessi

| Type | Quando usarlo |
|------|---------------|
| `feat` | nuova funzionalità per l'utente |
| `fix` | correzione di un bug |
| `refactor` | modifica del codice che non cambia comportamento |
| `perf` | miglioramento di prestazioni |
| `test` | aggiunta/modifica di test |
| `docs` | solo documentazione |
| `style` | formattazione, spazi (nessun cambio di logica) |
| `build` | build, dipendenze, tooling |
| `ci` | pipeline CI |
| `chore` | manutenzione che non rientra nelle altre |

### Le regole minime

- **`subject` all'imperativo, minuscolo, senza punto finale**: "add endpoint",
  non "Added endpoint.".
- **Massimo ~72 caratteri** nella prima riga.
- **`scope` opzionale** ma consigliato: il modulo toccato (`offers`, `db`,
  `auth`).
- **Un commit = un cambio logico**. Non mischiare refactor e feature nello
  stesso commit.
- **Breaking change**: aggiungi `!` dopo il type/scope (`feat(api)!: ...`) e
  spiegalo nel footer.

### Cosa NON fare

```
fix                           # inutile: non dice cosa
WIP                           # non va nella storia condivisa
update code                   # rumore
Added new endpoint for offers # tempo passato, vago
feat: misc changes + format   # due cose diverse in un commit
```

---

## Branch

Convenzione semplice, con prefisso che indica l'intento:

| Prefisso | Uso |
|----------|-----|
| `feat/<descrizione>` | nuova funzionalità |
| `fix/<descrizione>` | correzione di un bug |
| `refactor/<descrizione>` | refactor senza cambio di comportamento |
| `docs/<descrizione>` | documentazione |
| `test/<descrizione>` | aggiunta/modifica test |
| `chore/<descrizione>` | manutenzione, tooling, dipendenze |

I prefissi sono **brevi e allineati ai tipi dei commit** (`feat/`, non
`feature/`). Descrizioni brevi in kebab-case:
`feat/bulk-update-offers`, `fix/session-rollback`. I branch storici della POC
usavano una forma senza slash (es. `feature-mockup`); i nuovi branch seguono la
tabella.

---

## Cosa committare e cosa no

Il `.gitignore` esiste per una ragione: tenere fuori il rumore e i segreti.
Regola pratica:

**Da committare**

- `pyproject.toml` e `uv.lock` (il lock **sì**, è il contratto di
  riproducibilità).
- `.python-version`, `.pre-commit-config.yaml`, `.env.example`.
- codice, test, docs.

**Da NON committare**

- `.env` (segreti), `.venv/`, `*.db` (database locali), `__pycache__/`,
  cache (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`),
  `.vscode/`/`.idea/` (preferenze personali).

Controlla sempre prima di committare:

```bash
git status
git diff --staged
```

---

## Il flusso di lavoro

1. Aggiorna il branch di base e creane uno dal prefisso giusto.
2. Fai commit piccoli e tematici man mano.
3. Prima del commit, gli hook (`pre-commit`) verificano lint/format/types.
4. Apri una PR quando il branch è coerente e i test sono verdi.
5. La review guarda il **diff**, non solo l'ultimo commit.

> `git` è uno strumento delicato: non riscrivere la storia condivisa
> (`push --force`, `rebase` su branch pubblici) e non committare direttamente
> su `main` quando si lavora in squadra.

---

## Perché non essere troppo rigidi

Una convenzione troppo complessa (scope obbligatori con vocabolario chiuso,
linter sui messaggi, template di 30 righe) viene aggirata in due settimane. Il
valore sta nel 90% dei commit: `type(scope): subject` chiaro e atomico. Il resto
lo aggiungi solo se un bisogno reale lo giustifica (es. generare un changelog
automatico).

---

## Insidie

- **Commit giganteschi e misti**: impossibile capire cosa ha causato un bug o
  fare revert chirurgici.
- **`WIP` / messaggi vuoti nella storia condivisa**: la cronologia diventa
  inutilizzabile.
- **Committare `.env` o credenziali**: una volta nella storia, il segreto è
  compromesso anche se lo rimuovi dopo (va ruotato).
- **Non committare `uv.lock`**: ambienti non riproducibili.
- **Commit puramente di formattazione mescolati a logica**: la review si perde
  nel rumore. Separa `style:` da `feat:`/`fix:`.
- **Push forzato su branch condivisi**: riscrive il lavoro altrui.
