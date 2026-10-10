# Architettura, dati e contratti API

## Architettura eseguibile

L'applicazione è un unico processo Python FastAPI. `app/main.py` dichiara l'applicazione, CORS, il motore SQLite, il bootstrap, le route della dashboard e il router `/api`; `app/api_routes.py` apre una propria configurazione engine/session SQLite, equivalente ma indipendente a quella di `main.py`. I servizi eseguono query e mutazioni con SQLAlchemy; il generatore lavora sul filesystem locale e chiama Microsoft Graph quando richiesto.

```mermaid
flowchart TB
  Browser[Browser] --> Root[GET / Dashboard HTML]
  Browser --> Offers[REST /api/offers]
  Offers --> Router[api_routes.py]
  Router --> OfferService[OfferService]
  Router --> DocumentService[DocumentService]
  OfferService --> SQLite[(pre_contratti.db)]
  DocumentService --> SQLite
  DocumentService --> Generator[document_generator.py]
  Generator --> Templates[templates DOCX/XLSX/bollini]
  Generator --> Workspace[/tmp/compilation_workspace]
  Generator --> Graph[Microsoft Graph/OneDrive]
```

FastAPI `BackgroundTasks` avvia il lavoro dopo la risposta HTTP, ma non introduce un broker, retry durabile o processo separato. L'oggetto `Session` della richiesta viene passato alla funzione in background e viene normalmente chiuso dal dependency cleanup: un task lento può quindi usare una sessione non più valida. Questa è una delle principali differenze rispetto al worker Cloud Tasks descritto nei documenti target.

## Bootstrap e dati demo

All'evento di startup il servizio tenta di acquisire un lock in `/app/pre_contratti_db_init.lock`, esegue `Base.metadata.create_all`, inserisce i segmenti se assenti e poi tre offerte demo se non esiste alcuna offerta. Le demo sono una Mobile CB Consumer 5G, una Fisso GA Consumer FTTH e una Very Mobile 4G; ciascuna possiede i quattro identificatori di tabella, anche quando il contenuto di alcune tabelle è vuoto.

Il lock è adatto al path del container ma non al normale sviluppo locale in questa workspace, dove `/app` può non esistere o non essere scrivibile. Il codice cattura l'errore e prosegue; con reload o più worker la protezione è quindi best effort. Il database è relativo alla directory di lavoro: avviare il server da una directory differente crea o usa un file diverso.

## Modello relazionale

| Tabella | PK | Relazioni | Osservazioni |
| --- | --- | --- | --- |
| `segments` | `id` stringa | 1:N `offers`, 1:N `user_segment_roles` | Catalogo aziendale. |
| `users` | UUID | 1:N ruoli, 1:N history come actor | Pronto per IAM, inutilizzato. |
| `user_segment_roles` | (`user_id`, `segment_id`) | collega utenti e segmenti | Ruolo stringa; ORM non impone enum. |
| `offers` | UUID | N:1 segmento; 1:N tabelle/storico | Anagrafica e lifecycle. |
| `dynamic_tables` | UUID | N:1 offerta | JSON per layout e JSON per note. |
| `offer_state_history` | UUID | N:1 offerta, N:1 user opzionale | URI output e audit. |
| `global_configs` | `config_key` | nessuna | Configurazioni comuni potenziali. |

L'ORM usa `Uuid(as_uuid=True)` e `uuid4` per le chiavi; è una scelta adatta anche all'obiettivo Spanner. Il DDL Spanner è però distinto dal modello SQLAlchemy e presenta un errore nella tabella `offer_state_history`: dopo `agcom_code_used VARCHAR(10),` compare `UUID,` senza nome colonna. Il DDL non deve essere applicato finché non viene corretto e provato contro Spanner.

### Offerta e validazione Pydantic

`OfferCreate` richiede `segment_id`, `commercial_name`, `technology_type`, `base_price` positivo e `date_start`. Il PO, se fornito alla creazione, deve rispettare `^PO\d+$`; la data fine non può precedere la data inizio. `OfferUpdate` è volutamente più permissivo: non riapplica i vincoli di prezzo, PO, metodo di pagamento o date, e il codice AGCOM impone solo una lunghezza da 10 a 50 caratteri, non esattamente 10 o 36 né un formato alfanumerico/UUID. Il servizio di transizione è più stretto sulla sola lunghezza.

Campi applicativi di `offers`:

| Gruppo | Campi |
| --- | --- |
| Identità | `id`, `segment_id`, `commercial_name`, `po_code` |
| Prodotto | `technology_type`, `base_price`, `payment_method` |
| Lifecycle | `status`, `current_agcom_code`, `date_start`, `date_end` |
| Naming | `custom_filename_sintesi`, `custom_filename_trasparenza` |
| Attivazione | `activation_price_gia_clienti`, `activation_price_nuovi_nativi`, `activation_price_nuovi_portabilita` |
| Audit | `created_at`, `updated_at` |

## Contratti REST effettivi

Tutti gli endpoint sono senza autenticazione. Il suffisso finale su `/offers/` è usato dalla dashboard; FastAPI può redirigere la variante senza slash. Le risposte offerta sono serializzate tramite `OfferResponse`.

### Lettura e CRUD

```http
GET /api/offers/
GET /api/offers/{uuid}
GET /api/offers/{uuid}/tables
```

La lettura delle tabelle restituisce una mappa, non una lista, per esempio:

```json
{
  "PREZZO": {
    "max_rows_limit": 15,
    "rows": [{"id": "p1", "type": "padre", "label": "Canone", "value": "29,99 euro", "children": []}],
    "note_links": {"html_content": "<b>IVA inclusa</b>"}
  }
}
```

`POST /api/offers/` crea il record e le quattro tabelle baseline. `PUT /api/offers/{uuid}` aggiorna solo i campi esplicitamente non nulli; un client non può quindi cancellare un valore opzionale impostandolo a `null`. Per `po_code`, il valore speciale `N/A` è trasformato in `None`. Se viene passato `status`, viene scritto senza history né generazione.

### Tabelle dinamiche

```http
PUT /api/offers/{uuid}/tables/PREZZO
Content-Type: application/json
```

```json
{
  "max_rows_limit": 15,
  "rows": [
    {
      "id": "p_canone",
      "type": "padre",
      "label": "Canone mensile",
      "value": "29,99 euro",
      "children": [
        {"id": "c_sconto", "type": "figlio", "label": "Sconto", "value": "-5 euro"}
      ]
    }
  ],
  "note_links": {"html_content": "Valido online."}
}
```

Il router esegue la validazione Pydantic standard con il limite di default 15, poi il servizio esegue nuovamente `model_validate` con il limite di segmento. Per un identificatore inesistente viene creata una nuova tabella. `note_links` viene escluso da `structural_content` e salvato nell'apposita colonna. Il valore di `max_rows_limit` resta nei dati ma non modifica il limite imposto dal servizio.

### Lifecycle, compilazione e CSV

```http
POST /api/offers/{uuid}/transition?target_status=APERTA&agcom_code=COD1234567
POST /api/offers/{uuid}/transition?target_status=CHIUSA&date_end=2026-12-31
POST /api/offers/{uuid}/compile
POST /api/offers/bulk-update
GET  /api/offers/{uuid}/mapping
```

La transizione riceve query parameter, non un oggetto JSON. Il compile endpoint richiede `BackgroundTasks` ed esegue il task dopo la risposta. Il bulk update richiede una lista UUID e `fields`, che è un `OfferUpdate`; fallisce con `404` quando anche una sola offerta non esiste e altrimenti applica gli stessi campi a tutte le righe in una sola commit.

```json
{
  "offer_ids": ["342ec6f4-ec8a-40a2-944d-57ff638b9bb8"],
  "fields": {"base_price": 24.99, "payment_method": "abbonamento"}
}
```

Il CSV mapping usa una costruzione testuale semplice. Nome commerciale e altri valori non sono quotati CSV: una virgola nel nome rompe la struttura della riga. Gli URL non provengono da `offer_state_history`, ma da un formato fisso `https://precontratti.windtre.it/.../{id}.pdf`.

## Architettura target e confini da costruire

Il target GCP previsto separa frontend statico, API, queue e renderer. Il passaggio corretto non è una migrazione meccanica di SQLite: occorre introdurre repository/session factory per Spanner, un comando di job idempotente contenente offer/version/output scope, worker che apre la propria sessione, storage privato con versioni e metadati, e endpoint che recuperano solo artefatti autorizzati. L'API deve diventare il punto di enforcement di OIDC e `user_segment_roles`; la dashboard non può restare responsabile dell'ownership.