# Operatività, sicurezza, qualità e roadmap

## Eseguire il prototipo locale

Il progetto dichiara Python `>=3.13` nel `pyproject.toml`, ma l'immagine Docker usa Python 3.11. Scegliere e documentare una singola baseline prima di introdurre lockfile o CI. Dopo aver creato un virtual environment, installare le dipendenze dal file che il Dockerfile usa realmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`requirements.txt` include FastAPI, Uvicorn, SQLAlchemy, Pydantic, OpenPyXL, python-docx, Spire.XLS, pypdf, requests, pytest e python-dotenv. Il comando Uvicorn fallirà con `command not found` se l'ambiente virtuale non è attivo o se l'installazione non è stata completata. In quel caso usare `python -m uvicorn ...` dopo l'installazione, così il binario proviene con certezza dallo stesso interprete.

All'avvio visitare `/` per la dashboard e `/docs` per OpenAPI. Il database viene creato nella directory corrente; per una prova ripetibile rimuovere solo un database locale dedicato, mai dati di un ambiente condiviso. I file generati sono temporanei e non sono un archivio di progetto.

## Variabili d'ambiente e segreti

La Sintesi PDF richiede quattro valori: `MS_GRAPH_TENANT_ID`, `MS_GRAPH_CLIENT_ID`, `MS_GRAPH_CLIENT_SECRET` e `MS_GRAPH_DRIVE_ID`. Sono accettati gli equivalenti `ONEDRIVE_*`. `python-dotenv` tenta di caricare `.env`; il file è correttamente ignorato da Git.

In ambiente cloud i valori non devono essere passati come file immagine, parametri di build o log. Usare un secret manager, una service identity con accesso minimo al segreto e un'app Azure AD limitata al drive/cartella scratch. Il client trasmette il client secret alla token endpoint: è necessario ruotarlo, osservare gli errori di autenticazione e definire una retention per gli item che non vengono cancellati in OneDrive.

## Docker e limiti del container

```bash
docker build -t pre-contratti-app .
docker run --rm -p 8080:8080 --env-file .env pre-contratti-app
```

Il Dockerfile installa LibreOffice e font, copia il codice in `/app` e i template in `/gcs/templates/`, poi esegue come `appuser` sulla porta 8080. Avvia quattro worker Uvicorn. Il file SQLite e la workspace temporanea sono nel filesystem effimero e non hanno volume persistente; con più worker non costituiscono una persistenza sicura. LibreOffice aiuta solo la catena XLSX: la Sintesi PDF continua a fallire senza Graph.

Il Dockerfile non include healthcheck, scan delle dipendenze, utente/gruppo con ownership delle cartelle in `/gcs`, configurazione dei log o deployment Cloud Run. Sono normali assenze in un prototipo, ma impediscono di trattarlo come artefatto production-ready.

## Valutazione di sicurezza

| Area | Stato attuale | Conseguenza | Correzione necessaria |
| --- | --- | --- | --- |
| Autenticazione | Nessun JWT/OIDC | Chiunque raggiunga l'API accede ai dati | Middleware OIDC con issuer, audience, scadenza e firma verificati |
| Autorizzazione | Nessun controllo server-side | Un UUID consente leggere/modificare ogni segmento | Policy centralizzata su `user_segment_roles` per ogni query e comando |
| CORS | `allow_origins=["*"]`, credenziali abilitate | Configurazione non appropriata in produzione | Lista di origin espliciti e cookie/token policy coerente |
| Download locale | Nome input concatenato al path; fallback mock | Possibile traversal e mascheramento errori | Risolvere path, consentire solo artefatti registrati, restituire 404 reale |
| Storage | URI GCS costruiti, non firmati | Nessuna confidenzialità o tracciabilità effettiva | Bucket privato, IAM, signed URL a breve vita e metadati persistiti |
| Audit | `changed_by` mai impostato | Audit non attribuibile | Actor da claim verificato, reason e immutabilità |
| Input rich text | HTML/URL interpretati in modo leggero | Link indesiderati o contenuto non governato | Sanitizzazione, allowlist URL e autorizzazione editoriale |

## Strategia di test

La suite `tests/test_suite.py` esamina funzioni importanti: normalizzazione del nome, date, PO Very Mobile, limite righe, codice AGCOM, pagamento, due layout DOCX, markup HTML/Markdown e bulk update. Il test di layout genera un DOCX temporaneo e controlla righe, run formattate, hyperlink e tooltip. Il test bulk invoca `on_startup`, usa il database locale e fa rollback; non crea un database temporaneo isolato.

Eseguire i test con `pytest tests/`. Nel contesto analizzato il comando non è disponibile nel PATH, quindi la prima azione operativa è installare le dipendenze nel venv. Non dichiarare una suite verde finché non viene eseguita nello stesso ambiente che esegue l'applicazione.

La copertura da aggiungere dovrebbe seguire il rischio:

1. Test API con TestClient: 401/403, 404 tabelle, validazione update, lifecycle e CSV con quoting.
2. Test unitari Graph con HTTP mock: token cache, redirect, Retry-After, errori permanenti e cleanup.
3. Golden test su template DOCX/XLSX reali, controllando formule, immagini, note, nomi e contenuto estratto.
4. Test job: idempotenza, concorrenza, retry, errori conversione e persistenza dello stato.
5. Test di accettazione manuali: Adobe, vademecum AGCOM, PDF/UA checker e screen reader con i template approvati.
6. Test E2E di isolamento: utenti di segmenti diversi non possono enumerare, leggere, modificare o scaricare dati altrui.

## Osservabilità e gestione degli incidenti

Il runtime usa `print` per varie condizioni e non espone lo stato delle generazioni. Un'architettura operativa necessita di un identificativo job correlato a offer, versione e actor; log strutturati senza segreti; metriche su coda, latenza, errore conversione, dimensione PDF e retry Graph; alert su fallimenti e oggetti OneDrive non ripuliti. Il record storico dovrebbe contenere hash, dimensione, versione template, esito e timestamp di ogni artefatto, non soltanto URL.

In caso di errore di generazione, non distribuire il fallback mock. Conservare errore tecnico e causa business in un job consultabile, rendere ritentabile l'operazione e impedire la pubblicazione di output non validati. L'operatore deve poter distinguere “job accettato”, “in esecuzione”, “fallito” e “completato”, non soltanto ricevere un messaggio HTTP di accodamento.

## Roadmap tecnica prioritaria

### Fase 0: chiudere le decisioni di dominio

Approvare configurazione per segmento, stati, naming, output selezionabili, punti prezzo CB, campi fissi/variabili, owner del PDF/UA e criteri di accettazione. Correggere il DDL Spanner e allinearlo al modello SQLAlchemy. Questa fase evita di implementare regole contraddittorie, oggi distribuite tra requisito e documenti di design.

### Fase 1: fondazioni sicure

Introduzione di OIDC, user provisioning, enforcement RBAC e audit actor. Migrazione a Spanner o altro database approvato tramite migration versionate e test di compatibilità. Definizione di storage GCS privato e gestione segreti. L'applicazione non deve diventare accessibile a utenti reali prima di questo punto.

### Fase 2: job e artefatti affidabili

Estrarre la generazione in un worker stateless, con Cloud Tasks o equivalente, idempotency key, retry controllati e stato durabile. Registrare ogni artefatto, mantenere versioni immutabili e fornire download autorizzati. Applicare come errori bloccanti le policy Adobe, non come warning.

### Fase 3: modellazione dei template

Versionare template, configurazioni per segmento e catalogo campi. Implementare note fisse/variabili e campo libero. Sostituire euristiche su label con campi semantici. Validare dinamicamente capacità del template e formule XLSX. Il renderer deve essere testato con esempi reali autorizzati.

### Fase 4: esperienza utente e UAT

Sostituire le persone mock con sessione reale, mostrare solo le offerte autorizzate, consentire selezione esplicita di Sintesi/Trasparenza e mostrare job/output. Completare UAT con marketing, legal, AGCOM e accessibilità. Automatizzare build, test, scansioni e deploy in CI/CD prima del rilascio.

## Definition of Done per un rilascio

Un rilascio può essere considerato pronto quando il team può dimostrare, con artefatti e test, che un editor autenticato agisce solo sul proprio segmento; che una modifica selezionata genera esattamente gli output richiesti e recuperabili; che le versioni precedenti restano disponibili; che un PDF fuori policy non passa inosservato; che i template reali rispettano formule, contenuto e accessibilità; e che ogni errore è osservabile e ritentabile. Questo criterio è più utile di una semplice verifica che la dashboard si apra: misura il processo regolato che il prodotto è chiamato a sostenere.