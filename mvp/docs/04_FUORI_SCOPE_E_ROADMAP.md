# 04 — Fuori scope e roadmap

Tutto ciò che **non è stato implementato nell'MVP** per tenere il primo rilascio
semplice, con il motivo e l'impatto previsto. L'MVP è progettato perché queste
estensioni non richiedano di rifare il modello (vedi documento 03, §8).

## 1. La Trasparenza Tariffaria (Excel AGCOM)

**Manca**: form di compilazione della Trasparenza e generazione dell'`.xlsx`
dalla griglia fissa AGCOM. Oggi esiste solo il documento `SINTESI`.

**Perché fuori**: l'MVP era focalizzato sulla Sintesi; la Trasparenza è più
semplice (griglia fissa) ma richiede la mappatura campo → cella e il Vademecum.

**Cosa serve**: template Excel definitivo + definizioni delle celle
(`template_fields` con `excel_cell`), form dedicato, servizio di generazione
`openpyxl`. Nessun cambio di schema: è lo stesso modello con
`doc_type = trasparenza`. Il form sarà **separato** da quello della Sintesi (i
due ground truth sono indipendenti, per decisione di progetto).

## 2. Collegamento Sintesi ↔ Trasparenza

**Manca**: qualunque mappatura o controllo incrociato tra i due ground truth.
Oggi, per decisione, possono divergere liberamente.

**Cosa serve**: una tabella di mappatura tra chiavi dei campi/voce della
Sintesi e celle della Trasparenza (più eventuali trasformazioni), da costruire
con l'area regolamentare. L'identità stabile delle voci e delle chiavi è già
predisposta per questo.

## 3. Note delle Sintesi

**Manca**: note statiche/dinamiche sotto le tabelle, con chip verso i valori
(`{{ voce.<code> }}`) e propagazione automatica alla generazione. Il template
di test è stato volutamente creato **senza note**.

**Perché fuori**: prima si è consolidato il nucleo (tabelle dinamiche,
massive); le note sono il secondo problema per complessità.

**Cosa serve**: tabella `template_note` (blocco, testo, chip), editor per
inserire i chip, risoluzione nel render context, policy per i chip irrisolti
(blocco della generazione o nota condizionata). Le note per singola offerta
sono un'estensione ulteriore.

## 4. PDF e accessibilità

**Manca**: conversione DOCX → PDF e PDF/UA (accessibile), requisiti Adobe.

**Cosa serve**: pipeline di conversione (LibreOffice/Graph), controlli di
dimensione (≤ 2 MB), naming file secondo le regole Adobe (caratteri, 160
caratteri, unicità), titolo del documento e ordine di lettura. Non incide sul
modello dati.

**Bollini e accessibilità**: i bollini delle tecnologie sono già iniettati come
immagini (M23), ma **senza testo alternativo** (`docxtpl`/`InlineImage` non lo
espongono): il testo alternativo per il PDF/UA va gestito in fase di
accessibilità (es. post-elaborazione del DOCX o libreria di conversione).

## 5. Ciclo di vita AGCOM

**C'è** (decisione M15): stati commerciali **`NUOVA`/`APERTA`/`CHIUSA`** e
**codice AGCOM** sull'offerta, impostabili **liberamente** in creazione e in
editor (default `NUOVA`, nessun vincolo automatico); tag colorati e chip AGCOM
in elenco ed editor.

**Manca**: le regole di coerenza stato↔codice (quando richieste), la regola dei
**"quattro file"** (versioni prima/dopo il codice, mai sovrascritte), PDF per
canale, **blocco delle modifiche** negli stati avanzati (oggi l'offerta resta
modificabile in tutti e 3 gli stati), storico delle transizioni, naming dei file
legato allo stato.

**Cosa serve**: definire le regole con l'area regolamentare, poi eventualmente
un blocco lato server; quando arriverà la Trasparenza, decidere se serva anche
uno stato per documento (`offer_documents.status` oggi resta inutilizzato).
Vedi documento 03 §5.6.

## 6. Utenti, autenticazione e permessi

**Manca**: login (OIDC aziendale), ruoli per segmento (viewer/editor/admin),
segregazione "modifico solo il mio segmento".

**Perché fuori**: singolo utente/demo.

**Cosa serve**: middleware/dependency di autenticazione, tabelle
`users`/`user_segment_roles`, controlli nei servizi. Il campo `segment_id` sulle
offerta c'è già.

## 7. Categorie Mobile, Very ed Etnico

**Manca**: template e definizioni per le altre categorie.

**Cosa serve**: un nuovo `document_template` + blocchi/campi/voci per ciascuna
categoria, riusando lo stesso codice. Da valutare, per il Mobile, se serviranno
sottocategorie di template.

## 8. Funzioni massive avanzate

**Mancano**:

- modifica massiva **delle etichette** (le etichette sono del dizionario: un
  "rinomina" è per definizione globale, non selettiva);
- **rimozione** di una voce in massa (oggi si aggiornano solo le voci già
  presenti; nessuna riga viene creata o rimossa);
- **creazione righe in massiva** (il vecchio "crea se manca" con padre di
  contesto è stato rimosso in M26: da reintrodurre se servirà);
- massiva su **testi** (note/paragrafi);
- **annullamento** di un'operazione: oggi la massiva **non conserva i valori
  precedenti**; con lo storico (vedi §12) si può costruire un ripristino come
  nuova operazione;
- gestione fine dei **conflitti**: `row_version` è stata rimossa insieme allo
  storico (§12); va reintrodotta insieme alla UI che segnali "offerta
  modificata nel frattempo";
- massiva per **cluster** (vedi §9).

## 9. Cluster e caratteristiche trasversali

**Manca**: raggruppamenti di offerte (Netflix, Amazon, assicurazione) come
criterio di selezione per le massive e come contenuto.

**Cosa serve**: tabelle cluster + appartenenza + elenco dati abilitati;
nessuna modifica alle operazioni massive esistenti.

## 10. Parametri globali (es. coefficiente RDA)

**Manca**: valori comuni con validità temporale (RDA dipende dal canone).

**Cosa serve**: tabella `global_parameter` (chiave, validità, valore) e uso nei
testi/segnaposto.

## 11. Dizionario delle voci: evoluzioni

**Mancano**:

- **alias** tra voci sinonime ("Rata Modem" ≈ "Rata del Modem") con unione
  guidata;
- **valori ricorrenti** (elenchi di valori suggeriti, con possibilità di
  stringa libera);
- **disattivazione** delle voci da UI (il campo `is_active` c'è ma non è
  esposto);
- **label_override** per singola offerta (con la voce che resta identica).

## 12. Storico minimo e revisioni (rimandato)

### 12.1 Cosa manca e a cosa servirebbe

Nell'MVP **non esiste alcuno storico**: le tabelle `change_events` /
`change_items` e la colonna `row_version` su `offers`/`offer_documents` sono
state **eliminate** perché venivano scritte a ogni salvataggio/massiva/
generazione ma **mai lette** da pagine o API: costo di scrittura e complessità
di modello senza alcun beneficio per l'utente.

Uno **storico minimo** servirebbe a:

1. rispondere a "**chi ha cambiato questo valore, quando e da cosa a cosa**"
   (registro append-only, evento + dettaglio per campo/voce);
2. mostrare una **timeline per offerta** nella pagina del documento;
3. dare la base per l'**annullamento** di una massiva e per il **controllo dei
   conflitti** tra anteprima e applicazione (§8);
4. predisporre la **ricostruzione "com'era a una data"** e le **revisioni
   congelate** dei documenti emessi (snapshot con `render_context`), che
   restano comunque un passo ulteriore (design nei documenti `riferimenti/`).

### 12.2 Come reintrodurlo

La strada è tracciata: gli hook erano già nei servizi e vanno rimessi negli
stessi punti (`app/services/sintesi.py:save_sintesi`, `app/services/bulk.py:
apply_bulk`, `app/services/generation.py:render_sintesi`).

1. **Ricreare i modelli** seguendo lo schema rimosso:

   ```
   change_events
     id               UUID  PK
     kind             VARCHAR(32)  -- create | manual_edit | bulk | generate
     committed_at     DATETIME(tz)
     bulk_operation_id UUID FK -> bulk_operations.id, nullable

   change_items
     id                 UUID  PK
     event_id           UUID  FK -> change_events.id, indicizzato
     offer_document_id  UUID  FK -> offer_documents.id
     template_field_id  UUID  FK -> template_fields.id, nullable
     voce_id            UUID  FK -> voci.id, nullable
     old_value          VARCHAR(500), nullable
     new_value          VARCHAR(500), nullable
   ```

   Più l'enum `EventKind` (`create`, `manual_edit`, `bulk`, `generate`) in
   `app/models/types.py`; l'evento `CREATE` può essere finalmente emesso alla
   creazione dell'offerta.
2. **Ricreare il servizio** `app/services/history.py` con
   `record_event(db, kind, items, bulk_operation_id=None)`, che aggiunge
   l'evento e i suoi item nella **stessa transazione** della modifica.
3. **Riagganciare i tre punti di scrittura**:
   - salvataggio Sintesi → `MANUAL_EDIT`, un item per campo/riga scritta
     (con `old_value`/`new_value`);
   - applicazione massiva → **un solo** `BULK` per operazione (con
     `bulk_operation_id`), un item per offerta toccata;
   - generazione → `GENERATE`, un item con il percorso del file.
4. **Migrazione**: in produzione aggiungere la migrazione Alembic; in
   sviluppo basta ricreare il database (il bootstrap ricrea lo schema).
5. **UI**: pagina "Storico" per documento (elenco eventi + item con
   prima/dopo), filtrabile per tipo.

**Controllo dei conflitti** (alternativa o aggiunta allo storico): rimettere
`row_version` su `offers` e `offer_documents`, esporla in lettura all'editor e
pretenderla in scrittura (`If-Match`); a divergenza il server risponde `409` e
le massive marcano l'offerta come `fallita` (l'esito e il motivo esistono già
in `bulk_operation_targets`).

### 12.3 Cosa resta fuori anche dopo

Ricostruzione "com'era a una data", diff tra versioni, revisioni congelate,
conservazione a norma: sono il livello successivo, da costruire sopra lo
storico minimo.

## 13. Infrastruttura di produzione

**Mancano**: migrazioni Alembic, passaggio a Postgres (o Cloud Spanner),
storage su GCS, code asincrone, CI/CD, ambienti staging/produzione, secret
management, observability.

**Nota**: il codice è già scritto per essere portabile (UUID generati
dall'app, enum non-native, nessuna dipendenza SQLite-specifica), ma il DB di
sviluppo/test è SQLite per scelta.

## 14. API JSON: estensioni fuori scope

**C'è** (decisione M27): una **API JSON** sotto `/api` (elenco/
dettaglio offerte, template, tecnologie, segmenti, bollino, download) più
`POST /api/offers/{id}/sintesi`; usa gli stessi services delle pagine e l'HTML
**coesiste** (nessuna dismissione).

**Mancano**:

- **CORS** (per servire un frontend su un'origine diversa);
- **paginazione, filtri e versioning** (`/api/v1`);
- **autenticazione** dell'API (vedi §6);
- **CRUD dei dati master** (modifica/cancellazione di voci, segmenti,
  tecnologie).

**Cosa serve**: middleware/parametri FastAPI per CORS e versionamento,
dipendenze di autenticazione (§6) ed endpoint di scrittura sui dati master con
le relative validazioni.

## 15. Naming dei file e consegna

**Manca**: regole di naming (nome offerta + tecnologia + prezzo + elemento
diversificante, vincoli Adobe), PDF per il sito, coesistenza delle versioni.

Oggi il file si chiama `<NomeOfferta>_sintesi_<timestamp>.docx`.

## 16. Migrazione dei documenti esistenti

**Manca**: import delle Sintesi storiche (file Word sparsi), in formati
disomogenei, con segnaposto residui.

**Cosa serve**: parser/censimento e definizione del perimetro (quali offerte
migrare). È anche l'occasione per popolare il dizionario con le voci reali.

## 17. Debiti tecnici minori (da pulire)

- query di sola lettura nelle route delle pagine (`pages.py`) invece che nei
  servizi;
- nessun test end-to-end in browser (solo smoke su DOM simulato);
- il confronto stringhe nelle massive non normalizza formati (`10 euro` vs
  `10 €`);
- nessun messaggio "flash" di conferma/errore sulle pagine (solo lo stato in
  pagina "Salvato.").

## 18. Ordine suggerito per la fase 2

1. **Trasparenza**: form + generazione Excel (percorso completo più semplice,
   sblocca il ciclo reale di lavoro).
2. **Note con chip**: completa le Sintesi e rende robusti i testi.
3. **Ciclo AGCOM + PDF/naming**: consegna reale dei documenti.
4. **Utenti e permessi**: prima di aprire a tutti i segmenti.
5. **Dizionario evoluto** (alias, valori ricorrenti) e **massive avanzate**
   (rimozione, annullamento con storico, controllo conflitti — §12).
6. **Infrastruttura di produzione** (DB gestito, storage, CI/CD).
