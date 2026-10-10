# Domande da porre al committente — WINDTRE Sintesi & Trasparenze

## Come usare questo file

Per ogni domanda è indicato:

- **Argomento (per Excel)**: una riga sintetica da copiare nel foglio riepilogativo.
- **Problema / contesto (per me)**: cosa dire al committente, perché la domanda nasce, e quali evidenze ho trovato nel codice o nella documentazione.
- **Risposta già nota (se presente)**: quando la repo o i documenti danno già una risposta parziale; in quel caso la domanda serve a confermarla o a chiarire i dettagli operativi.

Le domande sono raggruppate per area tematica, in ordine logico di conversazione: architettura → sicurezza → frontend → API/casi d'uso → dati/template → rendering → PDF/storage → DevOps → operatività → compliance → scope/timeline.

---

## 1. Stack tecnologico e architettura target

### 1.1 Necessità di Cloud Spanner

**Argomento (Excel)**: Conferma stack DB: Spanner è obbligatorio o valutiamo alternative?

**Problema / contesto**: L'`implementation_plan.md` e l'`hld_presentation.md` propongono Cloud Spanner PostgreSQL dialect come database target, motivandolo con ACID, JSON nativo e scalabilità. Tuttavia il codice attuale usa SQLite locale (`sqlite:///./pre_contratti.db` in `app/main.py` e `app/api_routes.py`), non esiste alcun client GCP nei `requirements.txt`, e la frequenza d'uso del sistema è bassa (3-4 canvas all'anno più modifiche regolamentari). Spanner ha un costo operativo e di licenza non trascurabile rispetto a Cloud SQL PostgreSQL o altre soluzioni più semplici.

**Risposta già nota**: Il codice è SQLite, ma il target progettuale è Spanner. Non risulta documentata una valutazione comparativa con altri database. La scelta sembra guidata dall'esistenza di uno "Spanner instance" già disponibile presso il cliente.

**Domanda da porre**: Spanner è un vincolo aziendale (es. "usiamo già Spanner, punto") o possiamo valutare alternative più leggere? Se è vincolante, qual è il nome del database/istanza Spanner da utilizzare e chi ci dà le credenziali?

---

### 1.2 HLD: direttiva vincolante o visione di destinazione?

**Argomento (Excel)**: HLD è vincolante per questa milestone o è il target a lungo termine?

**Problema / contesto**: I documenti `implementation_plan.md`, `hld_presentation.md` e `GEMINI.md` descrivono un'architettura serverless completa (Cloud Run, Cloud Tasks, GCS, Spanner, Next.js SPA, OIDC). Il codice attuale è invece una FastAPI monolitica con SQLite, `BackgroundTasks` in-process, HTML statico e nessuna autenticazione. C'è un forte disallineamento tra blueprint e runtime.

**Risposta già nota**: Il codice attuale (`app/main.py`, `app/api_routes.py`, `Dockerfile`) è una FastAPI monolitica con SQLite e `BackgroundTasks` in-process. I documenti di design (`implementation_plan.md`, `hld_presentation.md`, `GEMINI.md`) descrivono invece un'architettura serverless con Cloud Run, Cloud Tasks, GCS, Spanner e OIDC. I due livelli non coincidono.

**Domanda da porre**: L'HLD deve essere realizzato in questa fase, oppure la milestone attuale è portare a termine una POC/Pilot funzionante e l'HLD rimane la direzione per fasi future? Qual è lo scope contrattuale esatto?

---

### 1.3 Framework e linguaggio

**Argomento (Excel)**: Conferma stack runtime: Python 3.11/3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2.

**Problema / contesto**: `pyproject.toml` richiede Python 3.13, mentre il `Dockerfile` usa Python 3.11. Il codice è compatibile con entrambe le versioni, ma la divergenza va allineata per non generare confusione in CI/CD e in produzione.

**Risposta già nota**: Il codice funziona su 3.11 e sembra compatibile con 3.13. Non ci sono librerie bloccanti su una sola versione.

**Domanda da porre**: Fissiamo una versione Python unica e supportata (3.11 LTS o 3.13)? Chi decide e aggiorna il `Dockerfile`/`pyproject.toml`?

---

### 1.4 Modello dati: schema relazionale, colonne e numero di tabelle

**Argomento (Excel)**: Conferma modello dati: numero di tabelle, relazioni, nomi colonne, vincoli.

**Problema / contesto**: Il DDL in `app/database/spanner_schema.sql` e gli ORM in `app/database_models.py` prevedono 7 tabelle principali: `segments`, `users`, `user_segment_roles`, `offers`, `offer_state_history`, `dynamic_tables`, `global_configs`. Esistono però discrepanze tra DDL e codice:

- `spanner_schema.sql` ha un errore sintattico in `offer_state_history`: una riga isolata `UUID,` senza nome colonna (probabilmente dovrebbe essere `changed_by UUID`).
- Il DDL usa `UUID` come tipo, mentre `app/database_models.py` usa `Uuid(as_uuid=True)` di SQLAlchemy; la generazione avviene lato applicazione con `uuid4()`.
- `offers` contiene tre campi di prezzo di attivazione (`activation_price_gia_clienti`, `activation_price_nuovi_nativi`, `activation_price_nuovi_portabilita`) usati per derivare la clientela, ma il requisito originale sembra prevedere una modellazione più flessibile.
- `dynamic_tables` memorizza `structural_content` e `note_links` come JSON nativo, il che dà flessibilità ma rinuncia a vincoli relazionali sui singoli campi padre-figlio.
- `global_configs` esiste ma non viene letto dal codice.
- Non esiste una tabella per tracciare i file generati (solo URI nello storico), né una tabella per audit log generico delle modifiche.

**Risposta già nota**: Schema presente ma con errori DDL e parti non utilizzate dal runtime. Il codice attuale usa SQLite con lo stesso schema ORM.

**Domanda da porre**: Il modello dati a 7 tabelle è definitivo o va rivisto? In particolare: correggiamo l'errore DDL su `changed_by` in `offer_state_history`? Serve una tabella separata per i file generati? I campi `note_links` e `structural_content` come JSON vanno bene o preferite normalizzare alcune parti? `global_configs` deve diventare operativo (es. per RDA) o possiamo rimuoverlo se non serve?

---

## 2. Autenticazione, autorizzazione e identity

### 2.1 Chi autentica gli utenti?

**Argomento (Excel)**: Modalità di autenticazione: OIDC/Google Identity, credenziali DB interne, altro?

**Problema / contesto**: Esiste una tabella `users` e una tabella `user_segment_roles` nel modello dati, ma nessun endpoint richiede autenticazione. La dashboard `admin_dashboard.html` ha solo un dropdown "Simula Segmento IAM" che scrive su `localStorage`: è una simulazione client-side, non sicurezza. L'HLD parla di OIDC + Google Workspace Groups.

**Risposta già nota**: `app/database_models.py` definisce `User` e `UserSegmentRole`, ma `app/api_routes.py` non ha middleware di autenticazione né `Depends()` per il current user. In `admin_dashboard.html` la selezione del segmento avviene tramite dropdown che scrive su `localStorage`, quindi è solo una simulazione lato client. `GEMINI.md` e `implementation_plan.md` indicano OIDC + Google Workspace Groups come target.

**Domanda da porre**: Gli utenti si autenticheranno tramite Google Workspace / Identity Platform (OIDC), oppure serve un login interno con utenza/password? In entrambi i casi, chi fornisce la configurazione Identity Provider (tenant, client ID, secret) e chi gestisce il mapping tra utenti Google e segmenti WINDTRE?

---

### 2.2 Ruoli e segregazione per segmento

**Argomento (Excel)**: Definizione ruoli (editor/viewer/admin) e segregazione per segmento.

**Problema / contesto**: `user_segment_roles` prevede tre ruoli (`editor`, `viewer`, `admin`) e una relazione N:N utente-segmento. Nel codice i router non applicano alcun controllo: `GET /api/offers` restituisce tutte le offerte, `PUT /api/offers/{id}/tables/{...}` non verifica che l'utente appartenga al segmento dell'offerta.

**Risposta già nota**: Il modello dati è pronto, l'enforcement manca completamente.

**Domanda da porre**: Quali operazioni possono fare editor, viewer e admin? Gli admin possono modificare offerte di qualsiasi segmento o solo gestire configurazioni? Il controllo deve essere server-side obbligatorio?

---

### 2.3 Tabella `users` interna vs identity provider esterno

**Argomento (Excel)**: La tabella `users` deve essere popolata manualmente o sincronizzata con Google?

**Problema / contesto**: La tabella `users` contiene email, nome, cognome e stato attivo. Se si usa Google Identity, occorre decidere se sincronizzare gli utenti in DB o se risolvere ruoli e segmenti direttamente dai Google Groups all'accesso. Se invece si usano credenziali interne, serve un meccanismo di provisioning password.

**Risposta già nota**: La tabella esiste ma non è popolata nè utilizzata dal runtime.

**Domanda da porre**: Gli utenti vengono creati a mano in una console admin, importati da CSV, o sincronizzati automaticamente con Google Workspace? Chi è il responsabile del provisioning?

---

## 3. Frontend

### 3.1 Chi sviluppa il frontend e con quale tecnologia?

**Argomento (Excel)**: Frontend: Next.js/React SPA separata o evoluzione della dashboard HTML esistente?

**Problema / contesto**: L'HLD prevede una SPA React/Next.js servita da GCS+CDN. Il codice attuale è un singolo file `admin_dashboard.html` in vanilla HTML/CSS/JS, servito da FastAPI. Non esiste alcun processo di build frontend.

**Risposta già nota**: La dashboard HTML è una demo; l'architettura target è SPA separata.

**Domanda da porre**: Il frontend è nelle nostre responsabilità o è curato dal cliente/altra squadra? Se è nostro, partiamo dalla dashboard HTML esistente per accelerare la consegna o facciamo subito Next.js/React? Chi fornisce il design system/brand kit WINDTRE?

---

### 3.2 Hosting del frontend

**Argomento (Excel)**: Hosting frontend: GCS+CDN, Cloud Run con FastAPI, altro?

**Problema / contesto**: L'HLD dice GCS+CDN. Il codice attuale serve il frontend da FastAPI (`admin_dashboard.html` copiato in root nel `Dockerfile`). Se restiamo su FastAPI, CORS e routing sono più semplici ma il backend si occupa anche di asset statici.

**Risposta già nota**: Il Dockerfile attuale monta il file HTML nel container; non c'è pipeline di deploy su GCS.

**Domanda da porre**: Confermate GCS+CDN per la SPA? Se sì, chi gestisce il bucket, i permessi e l'eventuale Cloud CDN? Se no, il frontend resta embedded in FastAPI?

---

## 4. API, router e casi d'uso

### 4.1 Endpoint REST: chi li ha scelti e vanno bene così?

**Argomento (Excel)**: Conferma design API REST e eventuale versioning (`/api/v1/...`).

**Problema / contesto**: Gli endpoint sono già implementati sotto `/api/offers` (`GET`, `POST`, `PUT`, transizioni, compile, bulk-update, mapping). Non c'è versionamento esplicito. Se in futuro il frontend e altri client dipendono da questi contratti, cambiarli diventa costoso.

**Risposta già nota**: In `app/api_routes.py` gli endpoint sono già implementati sotto `/api/offers` e FastAPI genera automaticamente Swagger/OpenAPI. Non è presente un prefisso di versione esplicito.

**Domanda da porre**: Gli endpoint attuali sono già stabilizzati e consumati da altri sistemi, oppure possiamo ancora rivederli (naming, versionamento, payload)? Serve una prima versione `/api/v1/`?

---

### 4.2 Mappatura completa dei casi d'uso

**Argomento (Excel)**: Lista completa dei casi d'uso da supportare (CRUD, transizioni, generazione, pubblicazione, notifiche).

**Problema / contesto**: Attualmente sono implementati: creazione, lettura, modifica metadati, modifica tabelle padre-figlio, transizioni stato, generazione manuale, bulk update, export CSV Adobe. Mancano: eliminazione offerta, pubblicazione su canali esterni, notifiche email, selezione selettiva di output (solo Sintesi, solo Trasparenza), gestione multi-prezzo.

**Risposta già nota**: `app/api_routes.py` espone creazione, lettura, modifica metadati, modifica tabelle, transizioni di stato, generazione manuale, bulk update e export CSV Adobe. Mancano endpoint per eliminazione offerta, pubblicazione su canali esterni, notifiche e generazione selettiva (solo Sintesi o solo Trasparenza).

**Domanda da porre**: Ci fornite una checklist definitiva dei casi d'uso che devono essere in produzione alla prima consegna? In particolare: serve l'eliminazione logica/fisica delle offerte? Serve generare solo Sintesi o solo Trasparenza su richiesta? Le notifiche email a fine generazione sono obbligatorie?

---

### 4.3 Eliminazione offerta

**Argomento (Excel)**: Eliminazione offerte: logica, fisica, permessi.

**Problema / contesto**: Non esiste un endpoint `DELETE /api/offers/{id}`. Il modello dati ha `ON DELETE CASCADE` su tabelle figlie e storico, quindi eliminare un'offerta è tecnicamente possibile via ORM, ma non esposto.

**Risposta già nota**: Nessuna API di cancellazione implementata.

**Domanda da porre**: Serve poter eliminare un'offerta? Se sì, chi può farlo (solo admin?) e l'eliminazione deve essere logica (flag `is_deleted`) o fisica? Considerate che lo storico e i file generati potrebbero dover essere conservati per audit.

---

### 4.4 Pubblicazione su canali esterni

**Argomento (Excel)**: Pubblicazione automatica su Adobe/siti/AGCOM o solo preparazione file?

**Problema / contesto**: L'applicazione genera file in `/tmp/compilation_workspace` e costruisce URL GCS come stringhe, ma non fa upload reali. Non esistono endpoint per pubblicare su Adobe, siti WINDTRE/Very Mobile o portale AGCOM.

**Risposta già nota**: `app/services/document_service.py` costruisce URL GCS (`https://storage.googleapis.com/w3-precontratti-outputs/...`) ma non esegue upload reali. I file restano in `/tmp/compilation_workspace` e vengono serviti da `StreamingResponse`. L'export CSV Adobe è implementato, ma non esistono endpoint o logica per pubblicare su siti WINDTRE/Very Mobile o portale AGCOM.

**Domanda da porre**: Confermate che il sistema si ferma alla preparazione dei file + CSV di mapping, e l'upload sui canali esterni resta manuale? Oppure in una fase successiva servirà l'upload automatico (GCS, Adobe, FTP AGCOM)?

---

### 4.5 Multi-prezzo

**Argomento (Excel)**: Gestione multi-prezzo: rimossa dalla POC ma prevista dal requisito.

**Problema / contesto**: Il requisito originale parla di campagne multi-prezzo (es. CB Mobile). `implementation_plan.md` menzionava `price_points` JSON, ma `GEMINI.md` e il codice attuale hanno rimosso `price_points` dichiarando che "All multi-pricing campaigns are now structured inside the dynamic tables of the `PREZZO` block". Tuttavia la logica di `PREZZO` non sembra strutturata per rappresentare più punti prezzo in modo esplicito.

**Risposta già nota**: Il campo `price_points` è stato rimosso dai modelli.

**Domanda da porre**: Il multi-prezzo è un requisito reale della prima fase? Se sì, come lo modelliamo: dentro la tabella dinamica `PREZZO` con una convenzione padre-figlio, oppure reintroduciamo un campo strutturato `price_points`?

---

## 5. Dati, template e regole di business

### 5.1 Limiti padre-figlio per segmento e per tabella

**Argomento (Excel)**: Conferma limiti di righe padre-figlio per segmento e per tabella (PREZZO, COSTI, SERVIZI, DURATA).

**Problema / contesto**: `offer_service.py` ha una `LIMIT_MAPPING` semplificata con solo 6 segmenti su 9; `W3_FIX_GA_MB`, `W3_FIX_CB_MB` e `W3_ETN_CNS` ricadono nel default 15. Inoltre il limite è calcolato sul totale delle righe di una tabella, mentre il requisito originale sembra indicare massimi diversi per ogni tabella all'interno dello stesso segmento.

**Risposta già nota**: `LIMIT_MAPPING` attuale:
- W3_MOB_GA_CNS = 12
- W3_MOB_CB_CNS = 15
- W3_MOB_GA_MB = 11
- W3_FIX_GA_CNS = 14
- W3_FIX_CB_CNS = 14
- VERY_MOBILE = 3
- default = 15 per gli altri.

**Domanda da porre**: I limiti del requisito sono per tabella (es. `PREZZO` max X, `COSTI` max Y) o per offerta nel complesso? Ci fornite una tabella aggiornata e definitiva per tutti e 9 i segmenti?

---

### 5.2 Template Word ed Excel: quanti, chi li crea, come si versionano

**Argomento (Excel)**: Template: numero, proprietà, versionamento e processo di approvazione.

**Problema / contesto**: Nella repo esistono due template: `templates/w3_meta_template.docx` e `templates/template_trasaparenza.xlsx`. I documenti dicono che i template sono condivisi tra i 9 segmenti, con differenziazione via contenuto dinamico. Non esiste un meccanismo di versionamento dei template nè un audit "questo PDF è stato generato con la versione X del template".

**Risposta già nota**: Un template Word e un template Excel condivisi per tutti i segmenti. I bollini tecnologia sono asset grafici separati.

**Domanda da porre**: I due template esistenti sono già quelli definitivi approvati da compliance, oppure sono placeholder? Very Mobile ha un template diverso? Chi è il "template author" aziendale e come viene tracciata una modifica ai template (versione, data, approvatore)?

---

### 5.3 Note fisse e variabili

**Argomento (Excel)**: Gestione note: parte fissa (read-only) e parte variabile (editabile).

**Problema / contesto**: `implementation_plan.md` e `GEMINI.md` descrivono una suddivisione delle note in "fixed part" e "variable part". Nel codice esiste solo il campo `note_links` JSON su `dynamic_tables`, senza distinzione semantica tra fisse e variabili.

**Risposta già nota**: Il modello dati non riflette ancora questa distinzione.

**Domanda da porre**: La distinzione note fisse/variabili è necessaria nella prima versione? Se sì, dove risiedono le note fisse (a livello di tabella, di segmento, globali?) e chi le aggiorna?

---

### 5.4 Coefficiente RDA per giga EU

**Argomento (Excel)**: Coefficiente RDA: dove si configura e chi lo aggiorna annualmente.

**Problema / contesto**: `GEMINI.md` menziona il calcolo degli EU Gigabytes basato su un coefficiente RDA globale. Esiste la tabella `global_configs` nel DDL, ma il codice non la legge e non esegue alcun calcolo.

**Risposta già nota**: La tabella `global_configs` esiste; la logica di calcolo non è implementata.

**Domanda da porre**: Il calcolo RDE/EU giga deve essere implementato in questa fase? Se sì, chi fornisce il valore del coefficiente e chi ne autorizza l'aggiornamento ogni anno?

---

## 6. Rendering, documenti e PDF

### 6.1 Motorino DOCX: placeholder indicizzati vs loop Jinja

**Argomento (Excel)**: Template Word: conferma approccio placeholder indicizzati con limite di righe predefinite.

**Problema / contesto**: `implementation_plan.md` e `low_level_design.md` descrivono un motore `docxtpl` con loop Jinja che espandono dinamicamente le righe. Il codice effettivo in `app/document_generator.py` usa `python-docx` e cerca placeholder indicizzati (`{{SERVIZI_parent_0_label}}`, `{{SERVIZI_parent_0_value}}`, ecc.), poi rimuove le righe vuote. Questo implica che il template deve contenere già tutte le righe massime possibili; righe JSON in eccesso non verranno renderizzate.

**Risposta già nota**: Ho verificato il codice: il renderer non duplica righe, usa placeholder posizionali e rimuove quelle irrisolte. È documentato nella nuova sezione di `03_RENDERING_E_TEMPLATE.md`.

**Domanda da porre**: Siete consapevoli che il template Word deve essere preparato con il numero massimo di righe per tabella? Se in futuro AGCOM richiede più righe, occorrerà aggiornare il template. Va bene questo compromesso o volete investire in un vero motore di espansione XML?

---

### 6.2 Excel e formule: insert_rows non ricalcola i range

**Argomento (Excel)**: Template Excel: verifica impatto di `insert_rows` su formule e range.

**Problema / contesto**: Il renderer per la Trasparenza usa `openpyxl.sheet.insert_rows()` per inserire le righe padre-figlio sotto il marker `[INIZIO_TABELLA_PREZZI]`. `openpyxl` non aggiorna automaticamente formule, named ranges, tabelle Excel (table objects) o grafici che puntano a range che si sono spostati.

**Risposta già nota**: Il codice non ricalcola/riscrive formule dopo `insert_rows`. Questo non è menzionato esplicitamente nei documenti di design.

**Domanda da porre**: I template Excel AGCOM contengono formule, tabelle strutturate o grafici? Se sì, dobbiamo prevedere un passaggio di riscrittura dei range dopo l'inserimento delle righe; altrimenti le formule si romperanno.

---

### 6.3 PDF Sintesi: dipendenza obbligatoria da Microsoft Graph

**Argomento (Excel)**: PDF Sintesi: conferma obbligo Microsoft Graph e gestione credenziali.

**Problema / contesto**: La conversione PDF della Sintesi usa esclusivamente Microsoft Graph/OneDrive (`?format=pdf`). Il `Dockerfile` installa LibreOffice, ma il codice di `document_generator.py` per la Sintesi non ha fallback locale. Se le credenziali Graph non sono disponibili o il servizio non risponde, la generazione della Sintesi fallisce.

**Risposta già nota**: Graph è implementato con retry esponenziale. Per la Trasparenza esistono fallback (Graph → Spire.XLS → LibreOffice); per la Sintesi no.

**Domanda da porre**: Le credenziali Microsoft Graph sono già disponibili? Chi le gestisce (tenant ID, client ID, client secret, drive ID)? È accettabile che la generazione Sintesi fallisca senza Graph, oppure servirebbe un fallback locale anche per la Sintesi?

---

### 6.4 Licenze e costi di terze parti

**Argomento (Excel)**: Licenze e costi: Spire.XLS, Microsoft Graph, font, LibreOffice.

**Problema / contesto**: Il codice usa Spire.XLS come fallback per la Trasparenza. Spire.XLS è una libreria commerciale con licenza a pagamento per uso non di valutazione. Microsoft Graph ha limiti e costi associati. I font Microsoft sono installati nel container tramite pacchetti open source, ma la compliance sulle licenze dei font va verificata.

**Risposta già nota**: `requirements.txt` include `Spire.XLS`; il `Dockerfile` installa font Liberation e DejaVu.

**Domanda da porre**: Avete già le licenze Spire.XLS necessarie per produzione? Qual è il budget/limiti per le chiamate Microsoft Graph? I font installati nel container soddisfano i requisiti di brand e accessibilità?

---

## 7. Storage, deploy e DevOps

### 7.1 Google Cloud Storage: upload reale e URL pubbliche

**Argomento (Excel)**: Storage output: conferma GCS, upload reale, URL pubbliche vs signed URL.

**Problema / contesto**: `document_service.py` costruisce URL del tipo `https://storage.googleapis.com/w3-precontratti-outputs/{offer.id}/{filename}`, ma non effettua alcun upload. I file restano in `/tmp/compilation_workspace` e vengono scaricati tramite `StreamingResponse`. Gli URL nello storico sono quindi fittizi.

**Risposta già nota**: Nessun client GCS nei requirements; nessun upload implementato.

**Domanda da porre**: I file generati devono essere caricati su GCS? Se sì, il bucket esiste già e quali sono i permessi? Gli URL devono essere pubblici, signed o accessibili solo agli utenti autenticati?

---

### 7.2 CI/CD

**Argomento (Excel)**: CI/CD: pipeline, test automatici, deploy su Cloud Run.

**Problema / contesto**: Non esiste alcuna pipeline CI/CD (nessuna cartella `.github/workflows/`, nessun `cloudbuild.yaml`). Il Dockerfile è pronto, ma build, test e deploy sono manuali.

**Risposta già nota**: Nessuna pipeline presente.

**Domanda da porre**: Chi realizza e gestisce la pipeline CI/CD? Preferite GitHub Actions, Cloud Build o altro? Quali ambienti devono essere supportati (sviluppo, staging, produzione)? Il deploy in produzione richiede approvazione manuale?

---

### 7.3 Infrastructure as Code

**Argomento (Excel)**: Infrastructure as Code: Terraform, Pulumi, altro.

**Problema / contesto**: Non esiste alcun manifesto IaC. Il deploy descritto è "Dockerfile → Cloud Run manuale". Per produrre un'infrastruttura ripetibile servono almeno: Cloud Run service, Cloud Tasks queue, GCS bucket, Spanner database, Secret Manager, IAM service account, Cloud CDN per frontend.

**Risposta già nota**: Nessun Terraform/ARM/Pulumi presente.

**Domanda da porre**: Chi scrive e mantiene l'IaC? È incluso nel nostro scope o lo fornisce il cliente/DevOps? Se è nostro, usiamo Terraform o Google Deployment Manager?

---

### 7.4 Secret management

**Argomento (Excel)**: Gestione segreti: Secret Manager, .env, altro.

**Problema / contesto**: Le credenziali Microsoft Graph sono lette da variabili d'ambiente (`MS_GRAPH_*` o `ONEDRIVE_*`). In locale si usa `.env`; in Docker si passa `--env-file`. Non c'è integrazione con Google Secret Manager o altro vault.

**Risposta già nota**: `.env` locale; nessun Secret Manager.

**Domanda da porre**: In produzione i segreti (Graph, eventuali DB, SMTP, licenze) devono risiedere in Google Secret Manager? Chi ha i permessi per crearli e rotarli?

---

## 8. Operatività, osservabilità e qualità

### 8.1 Health check, logging e monitoring

**Argomento (Excel)**: Health check, logging strutturato e monitoring.

**Problema / contesto**: Non esiste un endpoint `/health` che verifichi DB, template o Graph. I log sono print/logging generici, non strutturati JSON. Non c'è monitoraggio né alerting. In `main.py` c'è uno startup hook, ma nessun health endpoint.

**Risposta già nota**: In `app/main.py` non è presente un endpoint `/health` nelle prime righe; `app/api_routes.py` non espone health check. I log sono gestiti con `print` e `logging` standard, non strutturati JSON. Non esiste integrazione con Cloud Logging, Cloud Monitoring o altri sistemi di osservabilità.

**Domanda da porre**: Serve un health check completo (DB, template, Graph)? I log devono essere strutturati JSON per Cloud Logging? Avete requisiti di monitoraggio/alerting specifici (Cloud Monitoring, PagerDuty, ecc.)?

---

### 8.2 Test e qualità

**Argomento (Excel)**: Test: coverage obiettivo, test d'integrazione, E2E, golden test template.

**Problema / contesto**: La test suite ha solo 4 test functions in `tests/test_suite.py`. Non ci sono test API, test di autenticazione/autorizzazione, test E2E, test sui template reali, test di fallback PDF, test di dimensione PDF, test di accessibilità. Non ci sono formatter/linter configurati.

**Risposta già nota**: `pytest tests/` funziona in locale. Mancano molti test.

**Domanda da porre**: Qual è la coverage target minima accettabile? Servono test d'integrazione con DB di test, test E2E sulla dashboard, golden test sui template DOCX/XLSX reali?

---

### 8.3 Ambienti di staging/UAT

**Argomento (Excel)**: Ambienti: sviluppo, staging/UAT, produzione su Google Cloud Platform.

**Problema / contesto**: Attualmente il sistema gira solo in locale (`uvicorn` su SQLite). Per andare in produzione su Google Cloud Platform serve almeno un ambiente di staging/UAT separato da quello di produzione, in modo che gli editor marketing possano provare le funzionalità e i template senza rischiare di pubblicare contenuti reali per errore. Su GCP questo si traduce tipicamente in:

- **Progetti GCP separati**: uno per sviluppo/staging e uno per produzione, così risorse, billing e permessi sono isolati.
- **Cloud Run separati**: due servizi distinti (es. `precontratti-staging` e `precontratti-prod`) con proprie variabili d'ambiente e segreti.
- **Database separati**: due istanze/namespace Spanner (o Cloud SQL se si cambia DB), così i dati di test non contaminano quelli reali.
- **Bucket GCS separati**: uno per gli output di staging e uno per quelli di produzione, per evitare che file di test finiscano nel bucket pubblico.
- **Credenziali Microsoft Graph separate**: le stesse o diverse? In staging si potrebbero usare un drive di test.
- **Accesso utenti**: chi può entrare in staging? Solo gli sviluppatori o anche gli editor marketing?

Non è definito se il cliente abbia già questi progetti/ambienti, chi li amministra e come avviene la promozione del codice da uno all'altro (es. deploy manuale, script, CI/CD).

**Risposta già nota**: Nessun ambiente GCP definito nella repository. Il `Dockerfile` è progettato per Cloud Run, ma non ci sono configurazioni per più ambienti.

**Domanda da porre**: Avete già progetti GCP separati per staging e produzione? Chi gestisce la creazione e l'amministrazione di questi progetti, dei service account e dei permessi IAM? Gli editor marketing faranno UAT in staging con dati reali o con dati di test? Le credenziali Microsoft Graph e i bucket GCS saranno condivisi tra staging e produzione o separati? Qual è il processo per promuovere una release da staging a produzione (approvazione manuale, tag Git, pipeline automatizzata)?

---

## 9. Compliance, accessibilità e audit

### 9.1 Verifica AGCOM e PDF/UA

**Argomento (Excel)**: Verifica conformità AGCOM 228/229/230 e PDF/UA: processo e responsabilità.

**Problema / contesto**: Le regole 228 (ND→Non applicabile), 229 (rimozione righe vuote) e i bollini tecnologia sono codificati. La regola 230 (note ancorate sotto la tabella) è solo documentata. Non esiste un audit automatico PDF/UA post-generazione; la conformità dipende da verifica manuale.

**Risposta già nota**: Requisiti parzialmente codificati; nessun validator automatico.

**Domanda da porre**: Chi è responsabile della verifica finale di conformità AGCOM e PDF/UA? Serve integrare un tool di validazione automatica (es. veraPDF, PAC) o accettate una verifica manuale con screen reader?

---

### 9.2 Audit log e tracciabilità

**Argomento (Excel)**: Audit log: tracciare chi modifica cosa e quando.

**Problema / contesto**: Esiste `offer_state_history` per le transizioni di stato, ma `changed_by` non viene valorizzato. Non esiste un audit log generico delle modifiche ai metadati e alle tabelle dinamiche.

**Risposta già nota**: Lo storico esiste ma senza utente.

**Domanda da porre**: Serve un audit log completo (chi ha creato/modificato un'offerta, chi ha generato un documento, chi ha modificato un template)? Quanto tempo deve essere conservato?

---

### 9.3 GDPR e dati personali

**Argomento (Excel)**: GDPR: dati personali in tabella `users` e log.

**Problema / contesto**: La tabella `users` contiene email, nome e cognome. Gli audit log conterrebbero azioni riconducibili a persone. Se si usa Google Identity, anche i token/id potrebbero transitare.

**Risposta già nota**: Nessuna menzione esplicita a GDPR nei documenti.

**Domanda da porre**: Quali dati personali dovranno essere trattati? Avete un DPO o linee guida privacy da rispettare per log e conservazione dati?

---

## 10. Scope, timeline e modalità di collaborazione

### 10.1 Cosa è incluso esattamente nella consegna

**Argomento (Excel)**: Scope milestone: POC, MVP o produzione completa?

**Problema / contesto**: La repo è una POC funzionante, ma l'HLD descrive una piattaforma enterprise. Serve capire se il committente si aspetta di ricevere un sistema pronto per la produzione, un MVP limitato o semplicemente un consolidamento della POC.

**Risposta già nota**: Il codice attuale è una FastAPI monolitica con SQLite, nessuna autenticazione, nessun upload GCS, nessuna coda distribuita. I documenti di progetto (`implementation_plan.md`, `hld_presentation.md`) descrivono invece una piattaforma enterprise serverless.

**Domanda da porre**: Qual è la milestone di consegna attesa? Funzionalità minime obbligatorie, nice-to-have e fuori scope. Serve un documento di scope firmato o un backlog condiviso?

---

### 10.2 Timeline e canvas commerciali

**Argomento (Excel)**: Timeline: quando deve essere operativo per il prossimo canvas?

**Problema / contesto**: I canvas sono 3-4 all'anno. Se il prossimo canvas è imminente, la timeline condiziona pesantemente le scelte architetturali (es. tenere SQLite+HTML vs migrare subito a Spanner+React).

**Risposta già nota**: I canvas sono 3-4 volte l'anno; le modifiche regolamentari sono imprevedibili.

**Domanda da porre**: C'è una data di go-live obbligatoria (es. prossimo canvas)? Se sì, quando? Questo determina se dobbiamo puntare a un MVP stabile o possiamo fare refactoring architetturale più profondo.

---

### 10.3 Chi fornisce cosa

**Argomento (Excel)**: Responsabilità: chi fornisce template, credenziali, ambiente, utenti, design.

**Problema / contesto**: Molte cose necessarie alla produzione non sono nel codice e non sono di pertinenza dello sviluppo puro: template approvati, credenziali Graph, account Google, ambiente GCP, design system, dati di test.

**Risposta già nota**: N/A.

**Domanda da porre**: Per andare in produzione, chi ci fornisce: i template DOCX/XLSX finali, le credenziali Microsoft Graph, l'ambiente GCP (progetto, billing, IAM), gli account utente/editor di test, il design system per il frontend, un set di offerte reali o fittizie per UAT?

---

## 11. Dubbi extra emersi dall'analisi

### 11.1 CORS in produzione

**Argomento (Excel)**: CORS: configurazione attuale `allow_origins=["*"]` non è sicura per produzione.

**Problema / contesto**: `app/main.py` abilita CORS per qualsiasi origine con credenziali. Questo è accettabile in locale, ma in produzione espone a rischi CSRF se il frontend è su un dominio noto.

**Risposta già nota**: CORS permissivo nel codice.

**Domanda da porre**: Quali saranno gli origini consentite in produzione e staging? Il frontend e il backend condivideranno lo stesso dominio o saranno su domini separati?

---

### 11.2 Download file e path traversal

**Argomento (Excel)**: Sicurezza download: normalizzazione nomi file e prevenzione path traversal.

**Problema / contesto**: `app/api_routes.py` non normalizza il nome file richiesto contro path traversal prima di servire il file da `/tmp/compilation_workspace`. Inoltre `download_compiled_file` crea un file mock se non trova l'output, un comportamento utile alla demo ma pericoloso in produzione perché può mascherare un errore di generazione.

**Risposta già nota**: Questo comportamento è presente nel codice attuale (`app/api_routes.py`) ed è tipico di una demo, non di un sistema di produzione.

**Domanda da porre**: I download devono essere protetti da autenticazione e autorizzazione? Possiamo rimuovere il comportamento "file mock" in produzione?

---

### 11.3 Concordanza nomi file e regola 4-file coesistenza

**Argomento (Excel)**: Naming file e coesistenza versioni NUOVA/COD per WINDTRE e Very Mobile.

**Problema / contesto**: La regola dei 4 file richiede di conservare sia la versione `NUOVA` che la versione `COD_<agcom>` di Sintesi e Trasparenza. Per WINDTRE il codice aggiunge suffix automatici, per Very Mobile no. Tuttavia la coesistenza non è garantita se il nome personalizzato Very Mobile resta identico.

**Risposta già nota**: Implementazione parziale; storage non reale.

**Domanda da porre**: Per Very Mobile, se l'utente non cambia nome personalizzato tra `NUOVA` e `COD`, la versione precedente viene sovrascritta. È accettabile? Oppure forziamo un identificativo univoco interno anche per Very Mobile?

---

### 11.4 Persistenza SQLite con worker multipli

**Argomento (Excel)**: Database locale: SQLite non è adatto a Cloud Run con 4 worker.

**Problema / contesto**: Il `Dockerfile` avvia 4 worker Uvicorn. Con SQLite su filesystem locale, la concorrenza tra processi worker non è sicura; inoltre il filesystem del container è effimero.

**Risposta già nota**: SQLite è solo per demo; target è Spanner.

**Domanda da porre**: Se la milestone prevede il deploy su Cloud Run prima della migrazione a Spanner, usiamo un database condiviso (es. Cloud SQL PostgreSQL) o accettiamo che SQLite sia solo per demo locale?

---

## Riepilogo domande critiche (top 10)

Se il tempo è limitato, queste sono le 10 domande da porre assolutamente:

1. **Scope**: POC, MVP o produzione completa? Qual è la data di go-live?
2. **Database**: Spanner è obbligatorio o possiamo valutare Cloud SQL/alternative?
3. **Autenticazione**: OIDC/Google Identity, login interno o nessuna auth in questa fase?
4. **Frontend**: Next.js/React da noi o da voi, o si mantiene la dashboard HTML?
5. **Template**: I due template esistenti sono definitivi? Chi li approva e versiona?
6. **PDF Sintesi**: Le credenziali Microsoft Graph sono disponibili? Chi le gestisce?
7. **Storage/output**: Carichiamo i file su GCS o ci fermiamo alla preparazione locale + CSV?
8. **CI/CD/IaC**: Chi realizza pipeline e Terraform/Cloud Build?
9. **Limiti padre-figlio**: Ci fornite la tabella definitiva per segmento e per tabella?
10. **Pubblicazione/canali**: Il sistema deve fare upload su Adobe/siti/AGCOM o solo preparare i file?
