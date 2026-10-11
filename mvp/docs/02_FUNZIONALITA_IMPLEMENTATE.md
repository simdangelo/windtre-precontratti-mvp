# 02 — Funzionalità implementate

Stato al 10 ottobre 2026. Tutto ciò che è descritto qui **esiste ed è coperto
da test** (78 test, tutti verdi) salvo dove diversamente indicato.

## 1. Bootstrap automatico del database

All'avvio (`lifespan` di FastAPI) l'app:

1. crea le directory `data/` e `data/generated/`;
2. crea lo schema (`Base.metadata.create_all`);
3. applica il **seed delle definizioni** (idempotente).

Il seed carica:

- **4 segmenti** Fisse: Fisso GA e Cross Selling Consumer, Fisso CB Consumer,
  Fisso GA e Cross Selling Microbusiness, Fisso CB Microbusiness;
- **3 tecnologie** con velocità e bollino: FWA Indoor (300/50 Mbps, bollino
  fibra-radio giallo), FTTC (200/20, fibra-rame giallo), FTTH (1000/100,
  fibra verde); le immagini stanno in `templates/bollini/`;
- il template **`SINTESI_FISSE`** (v1) che punta a
  `templates/word/sintesi_fisse_template.docx`;
- i **blocchi e i campi fissi** (vedi documento 03);
- il **dizionario delle voci** iniziale: Prezzo → Costo mensile, Per i già
  clienti, Costo SIM, Rata modem; Costi → Costo di attivazione, Modem, Costo di
  disattivazione.

`uv run python -m app.seed` esegue lo stesso bootstrap manualmente (non più
necessario). Il seed è il punto dove si aggiungono nuove definizioni al
catalogo.

## 2. Offerte: creazione e "Crea Sintesi"

- **Elenco offerte** (`/`): tabella con nome (**link all'editor**), **stato**
  (tag colorato), **codice AGCOM** (chip), categoria, **tecnologia** (solo il
  **bollino**, con tooltip del nome) e ultima modifica; per le offerte senza
  documento resta il tasto **"Crea Sintesi"**.
- **"Duplica"**: apre una **modale con il nuovo nome** (obbligatorio, non può
  coincidere con un'offerta esistente — nemmeno per maiuscole/spazi; controllo
  lato client e server con errore dentro la modale). La copia porta con sé
  anagrafica (categoria, segmento, tecnologia) e **tutta la Sintesi** (valori
  fissi e righe padre/figlio), mentre **nasce in stato `NUOVA`, senza codice
  AGCOM e senza file generati**.
- **"Elimina"** (rosso ghost): chiede conferma con una **modale dell'app** e
  poi **elimina definitivamente** offerta, documenti, valori, righe,
  registrazioni e file DOCX generati (il nome torna disponibile). Il nome
  dell'offerta è univoco (normalizzato: minuscole e spazi compattati).
- **Navigazione**: la voce "Offerte" è attiva solo in questa pagina (prima
  restava evidenziata anche nell'editor e nel form di nuova offerta); la top
  bar **non si sposta** tra le pagine (gutter della scrollbar stabile,
  `scrollbar-gutter: stable`). Il **marchio in alto** ("WIND3 Precontratti -
  MVP", con "Precontratti" in arancione) è **cliccabile** e riporta
  all'elenco offerte. Le pagine di dettaglio (**editor** e **nuova
  offerta**) hanno un **breadcrumb in alto** ("← Offerte / nome offerta") con
  il link di ritorno all'elenco, riconoscibile anche da chi non usa la top bar.
- **Aprire l'editor crea il documento se manca** (get-or-create): non esiste
  più il caso "offerta senza Sintesi" una volta aperto l'editor.

## 3. Nuova offerta a form completo (una sola azione)

`GET /offers/new` mostra **tutto in una pagina**:

- **anagrafica**: Nome offerta, Segmento, Tecnologia;
- **campi fissi** raggruppati per blocco (Intestazione, Servizio/i e
  apparecchiature, Velocità, Durata…);
- **tabelle dinamiche** (Prezzo, Costi) con le stesse funzioni dell'editor.

Comportamenti:

- **campi derivati live**: mentre digiti il nome, il campo "Nome Offerta"
  dell'Intestazione si aggiorna; selezionando la tecnologia si popolano le due
  caselle velocità (disabilitate), formattate come nella generazione
  (`300,00 Mbps in Download`); togliendo la tecnologia si svuotano.
- **"Crea offerta"** invia tutto a `POST /api/offers` in un'unica azione:
  vengono creati offerta (con **stato e codice AGCOM scelti nel form**),
  documento Sintesi e valori/righe. Al successo si apre l'**editor della nuova
  offerta** con un popup di conferma dal **titolo verde** ("Offerta creata") e
  **senza avvisi del browser** (le modifiche pendenti vengono marcate come
  salvate prima della navigazione).
- **validazione prima della creazione**: se il payload è incoerente (campo o
  voce inesistente) risponde errore e **non viene creato nulla** (nessuna
  offerta orfana).

## 4. Editor della Sintesi

`GET /offers/{id}` — pagina di compilazione organizzata in card:

- **Anagrafica**: **nome offerta modificabile** (validazione: vuoto o nome già
  esistente → rifiutato con 422), categoria, segmento e **tecnologia
  modificabile** (tendina) con il **bollino mostrato accanto** alla scelta (si
  aggiorna al cambio). Cambiando nome o tecnologia, i campi derivati
  (`nome_offerta`, velocità) si aggiornano subito; i valori si salvano con
  "Applica Modifiche". La card mostra in griglia, con etichetta, anche
  l'**ultima modifica** (aggiornata a schermo dopo il salvataggio). La legenda
  "I campi con * sono obbligatori" è **a destra nella riga del breadcrumb e in
  corsivo**; l'unico campo con asterisco è il Nome offerta, perché i campi del
  template **non vengono imposti**.
- **Stato e codice AGCOM**: tag colorato accanto al nome (**NUOVA** giallo,
  **APERTA** verde, **CHIUSA** rosso), chip 🏷️ con il codice **solo se
  presente**, tendina dello stato e campo del codice. **Nessun vincolo
  automatico**: l'utente imposta liberamente i due valori (all'offerta nuova
  restano `NUOVA` + codice vuoto, modificabili già in creazione); l'offerta
  resta modificabile in tutti e 3 gli stati.
- **Tabelle fisse**: una sezione per blocco (Intestazione, Servizio/i,
  Velocità, Durata…), con i campi in riga (**etichetta a sinistra, input a
  destra**) e un divider tra le sezioni; i campi derivati sono in sola
  lettura.
- **Tabelle dinamiche**: card speculare alla precedente; una sezione per
  tabella (Prezzo, Costi) con divider e titolo più grande, e le stesse funzioni:
  - **"Aggiungi padre"** e **"+ figlio"** (solo sui padri), **"×"** per
    rimuovere (rimuove anche i figli);
  - ogni riga ha una **voce scelta dal dizionario** (tendina) e un **valore
    libero** (facoltativo);
  - **"Nuova voce…"**: apre una **modale dell'applicazione** (mai un prompt del
    browser) in cui si scrive il nome; la registra nel dizionario per tutti e
    la seleziona; se il nome esiste già (anche con maiuscole diverse) l'errore
    appare **dentro la stessa modale**, che **resta aperta** per correggere il
    nome (invio con Enter per confermare); **la pagina non si ricarica** e i
    dati già digitati restano;
  - **rendering per layout**: nelle **2 colonne** la riga è affiancata
    (`Voce | Valore`, azioni a destra); nelle **1 colonna** la voce è sopra e
    **valore e azioni stanno sulla stessa riga** sotto (più compatto), a
    **larghezza piena**, con **divider unico sul gruppo padre**; in **entrambi
    i layout** l'**hover** evidenzia la riga in modo **simmetrico sopra/sotto**
    (i controlli sono inseriti nella riga) e per i **figli** la banda **parte
    dal bordo della barretta** (non copre la zona di raggruppamento: hover più
    corto, in altezza e larghezza, rispetto ai padri); i figli sono collegati
    al padre da una **barretta verticale** che **termina prima del divider**
    del gruppo successivo;
  - le spaziature sono **variabili CSS condivise** tra le due tabelle
    (`--table-row-pad-y`, `--table-child-pad-y`, `--table-row-gap`,
    `--table-child-row-gap`, `--table-group-sep` in `editor.css`): righe padre
    con padding simmetrico, **righe figlie più compatte** (padding, spazi
    interni e **controlli ridotti**, quindi **hover più corto**), **divider tra
    gruppi in una riga separatore dedicata** (`tr.group-separator`, linea
    centrata) e **barretta dei figli di colore contrastato** così resta
    visibile anche sotto l'hover;
  - **nessun header** `Voce/Valore/Azioni` in nessuna delle due tabelle (né in
    1 né in 2 colonne): le colonne sono allineate dal layout; una tabella
    vuota mostra solo il messaggio "Nessuna voce in questa tabella…";
  - il **layout** (`1_col`/`2_col`) è mostrato come informazione secondaria in
    piccolo accanto al titolo ("Tabella a 1 colonna" / "Tabella a 2 colonne").
- **Errori visibili**: le validazioni (es. nome mancante/duplicato)
  **evidenziano in rosso il campo** con il messaggio inline e vi scorrono sopra;
  il banner in cima resta solo per gli errori **senza un campo** associato (es.
  generazione fallita); digitando, l'errore si pulisce.
- **Barra azioni in fondo (sticky)**: "**Applica Modifiche**" e "**Ripristina**"
  **compaiono solo quando ci sono modifiche non salvate** (altrimenti la barra
  mostra solo "Genera Sintesi (.docx)", sempre visibile ma **disabilitato**
  finché ci sono modifiche pendenti, **con il motivo spiegato**: la barra
  indica "Modifiche non salvate: salva per generare la Sintesi" e il tasto ha
  il tooltip corrispondente); l'indicazione è **arancione, in grassetto e
  corsivo**. **"Applica Modifiche" chiede conferma** con una modale e, all'esito:
  popup **verde** ("Modifiche applicate") o **rosso** in caso di errore,
  **restando sulla pagina dell'offerta**; uscendo con modifiche pendenti compare
  la conferma dell'app (vedi sotto). La Sintesi si genera **solo da dati
  salvati** (vedi §5).
- **"Ripristina"**: riporta l'offerta ai valori salvati, previa conferma in-app
  ("Le modifiche non salvate andranno perse e l'offerta tornerà all'ultima
  versione salvata."). Anche **uscire dalla pagina** con modifiche pendenti
  (link in alto, "Annulla" nel form nuovo) apre una **modale
  dell'applicazione** con messaggi diversi se stai **creando** ("L'offerta non
  è stata ancora creata…") o **modificando** ("Ci sono modifiche non
  salvate…"). **Nessun popup nativo in tutta l'app**: le modifiche non salvate
  vengono anche copiate in una **bozza locale** (`localStorage`); se l'utente
  ricarica la pagina o riapre l'URL con la bozza presente, una modale propone
  **"Riprendi le modifiche" / "Scarta"**.
- **"Applica Modifiche"** (`PUT /api/offers/{id}/sintesi`):
  - i valori dei campi fissi vengono inseriti/aggiornati/cancellati (campo
    svuotato = valore rimosso);
  - le righe dinamiche vengono **sostituite integralmente** (delete + insert in
    un'unica transazione, ordinamento padre→figli);
  - tecnologia, stato e codice AGCOM vengono salvati **così come impostati**;
  - validazioni: campo/voce/tecnologia inesistente → 404; più di due livelli o
    riferimenti incoerenti → 422; blocco/campo di un altro template → rifiutato;
    nome offerta vuoto o già esistente → 422;
  - i timestamp di offerta e documento (`updated_at`) vengono aggiornati;
  - al successo la pagina torna all'**elenco offerte**.
- **"Genera Sintesi (.docx)"** (vedi §5) e **card "Sintesi generata"**: mostra
  la **versione corrente** (badge verde **"Aggiornata"** o arancione
  **"Superata"** se ci sono modifiche successive, con avviso "rigenera per
  aggiornarla") e le **versioni precedenti** in un pannello collassato con
  download. Quando la Sintesi è superata, la barra in fondo lo ricorda
  ("Sintesi superata: rigenera per aggiornarla").
- **Palette dei bottoni** (uniforme in tutta l'app, da best practice):
  - **arancione pieno** = azione **primaria/positiva** ("Nuova offerta", "Crea
    Sintesi", "Crea offerta", "Applica Modifiche", "Applica" massiva, "OK");
  - **grigio** = azioni **neutre/secondarie** ("Apri", "Annulla" nella
    creazione, "Genera Sintesi", "Aggiungi padre", "Nuova voce…", "+ figlio",
    "Anteprima", "Resta qui");
  - **rosso pieno** = **conferma di un'azione distruttiva** nelle modali
    ("Scarta modifiche", "Esci senza salvare/creare");
  - **rosso outline (ghost)** = azioni distruttive **discrete** ("×" di
    rimozione riga, "Ripristina/Scarta" della toolbar e del ripristino bozza).
- **Asset senza cache stantia**: `editor.js`/`editor.css` sono inclusi con
  `?v=<mtime del file>` (`asset_url` in `api/dependencies.py`), così il browser
  ricarica sempre la versione giusta dopo una modifica.

## 5. Generazione del DOCX

`POST /api/offers/{id}/generate`:

1. legge **i dati salvati** (il tasto è disabilitato finché ci sono modifiche
   pendenti);
2. **skip se già aggiornata**: se la Sintesi corrente è stata generata dopo
   l'ultima modifica dell'offerta, non crea un nuovo file e risponde `200`
   (`generated: false`); l'editor propone "Sintesi già aggiornata" con i tasti
   **[Non generare]** (default) e **[Genera comunque]** (`?force=true`) per i
   casi legittimi (es. template cambiato);
3. costruisce il contesto: campi fissi risolti (nome, tecnologia→velocità),
   **bollino della tecnologia** (immagine `InlineImage` di **0,53 × 0,53 cm**,
   dimensione fissa — la riga resta quella del template — iniettata **inline
   dopo il valore di "Servizi"**; tecnologia senza bollino → cella normale),
   tabelle dinamiche **appiattite** in righe fisiche (padri e figli nell'ordine
   di inserimento);
4. rende il template Word con `docxtpl`:
   - **padri in grassetto** (`RichText`), figli normali;
   - tabelle a 2 colonne = etichetta | valore; a 1 colonna = righe incolonnate;
5. salva il file in `data/generated/` con nome
   `<NomeOfferta>_sintesi_<timestamp>.docx` (**mai sovrascritto**) e risponde
   `201`;
6. registra il file in `generated_documents` (`is_current = true`; i
   precedenti diventano non correnti e finiscono nello storico).

Download: `GET /documents/{id}/download` (media type Word).

## 6. Modifica massiva sulla Sintesi (multi-campo)

`GET /bulk` — **form in stile editor**: si modificano **più campi insieme**.
La regola è "**compila solo ciò che vuoi cambiare**": i campi lasciati vuoti
non vengono toccati.

1. **Offerte**: selezione con checkbox (tutte predefinite);
2. **Cosa modificare**: un **unico box** con due gruppi separati da un
   **divider**, con titoli coerenti: **"Tabelle fisse"** (la **tecnologia**
   con "Non modificare", i **campi fissi** compilabili e i **derivati in sola
   lettura**: le **velocità si popolano scegliendo la tecnologia** nel gruppo
   Dati offerta, come nel form di creazione) e **"Tabelle dinamiche"** (tutte
   le **voci del dizionario** con un campo valore ciascuna; valgono solo per
   le offerte che le hanno — dove manca, l'offerta viene saltata senza creare
   righe);
3. **Anteprima** (barra in fondo stile editor, `POST /api/bulk/preview`):
   crea l'operazione in stato `ANTEPRIMA` e calcola per ogni offerta:
   - **esito**: `da_modificare` (almeno un valore cambia), `invariata` (tutto
     già uguale), `saltata_assente` (nessun valore applicabile: le voci
     coinvolte sono assenti);
   - **riepilogo** sintetico (es. "2 da modificare, 1 saltata (voce assente)")
     e conteggi complessivi (offerte modificate/inviariate/saltate, valori
     modificati, voci saltate).
   Se dopo l'anteprima si **modificano** valori o la selezione delle offerte,
   il pannello **si resetta** ("Modifiche cambiate: clicca di nuovo Anteprima.")
   e va rilanciata l'anteprima.
4. **Applica** (`POST /api/bulk/{id}/apply`): chiede **conferma** con una
   modale ("Applicare le modifiche?"); durante l'operazione, se è lenta,
   compare uno **spinner** a tutto schermo. Al termine una modale di esito
   ("Modifiche applicate") **senza riepilogo** (i conteggi sono già
   nell'anteprima) e si **resta sulla pagina**; l'anteprima viene resettata.
   In una transazione: aggiorna i valori dei campi fissi (**crea la riga del
   valore se il campo era vuoto**), la **tecnologia** delle offerte dove
   richiesto (le velocità derivate si aggiornano alla rigenerazione) e le
   righe esistenti delle voci con quel valore; le voci assenti vengono
   **saltate** (nessuna riga viene creata in questa versione); un'operazione
   già applicata viene rifiutata (422).

Note di scope: il **dettaglio per item** (etichetta, prima → dopo) è calcolato
e **disponibile nell'API** ma **non mostrato in UI** in questa versione (verrà
personalizzato più avanti). Il **"crea se manca"** e il **padre di contesto**
della versione a voce singola non esistono più; la **creazione di righe** in
massa è rimandata (vedi documento 04). Il confronto dei valori è per stringa
esatta.

## 7. Dizionario delle voci

- Le voci vivono in `voci`, legate a una **tabella dinamica** (blocco).
- `POST /api/voci` con `{block_id, label}`: crea la voce e risponde `201`. Il
  nome è **univoco per tabella senza distinzione di maiuscole/minuscole**
  ("MODEM" = "Modem" = "modem"): un duplicato risponde `422` con il messaggio
  "La voce … esiste già in questa tabella". Niente suffissi automatici.
- Le voci non si cancellano mai: c'è il campo `is_active` per la disattivazione
  (non esposto in UI nell'MVP).

## 8. Storico: rimosso per minimalità

Nell'MVP **non esiste alcuno storico**. Le tabelle `change_events`/`change_items`
e la colonna `row_version` sono state eliminate perché venivano scritte ma mai
lette da nessuna pagina o API. Lo scopo futuro (registro "chi ha fatto cosa",
timeline per offerta, controllo dei conflitti) e la procedura per
reintrodurle sono nel documento **04, §12**.

## 9. API esposte

| Metodo | Percorso | Scopo |
|---|---|---|
| GET | `/` | Elenco offerte (pagina) |
| GET | `/offers/new` | Form completo nuova offerta (pagina) |
| POST | `/offers` | Creazione legacy da form minimale (mantenuta per compatibilità) |
| POST | `/offers/{id}/sintesi` | "Crea Sintesi" da elenco (pagina, 303) |
| GET | `/offers/{id}` | Editor Sintesi (pagina) |
| POST | `/api/offers` | **Creazione offerta completa** (JSON, 201; accetta stato e codice AGCOM) |
| PUT | `/api/offers/{id}/sintesi` | Salvataggio Sintesi + tecnologia/stato/AGCOM (JSON) |
| POST | `/api/offers/{id}/generate` | Genera Sintesi .docx (201; 200 se già aggiornata; `?force=true` per forzare) |
| GET | `/documents/{id}/download` | Download del file generato |
| GET | `/technologies/{id}/badge` | Immagine del bollino della tecnologia (PNG) |
| POST | `/api/voci` | Crea voce del dizionario (201; duplicato, anche con maiuscole diverse → 422) |
| DELETE | `/api/offers/{id}` | Eliminazione definitiva dell'offerta e dei suoi dati (204) |
| POST | `/api/offers/{id}/duplicate` | Duplica l'offerta con un nuovo nome (201; nome duplicato → 422) |
| GET | `/bulk` | Pagina modifica massiva |
| POST | `/api/bulk/preview` | Anteprima massiva (persiste l'operazione) |
| POST | `/api/bulk/{id}/apply` | Applica la massiva |

Errori: eccezioni di dominio → `404` (non trovato), `422` (validazione),
`500` (generazione); il form legacy risponde `400` con messaggio in pagina sul
nome duplicato.

## 10. Test e qualità

- **78 test** in `tests/`: modelli, seed, schemi, offerte (creazione, elenco,
  Crea Sintesi, form completo, derivati, navigazione, breadcrumb, flag
  `?created=1`, **eliminazione** con cascata e liberazione del nome,
  **duplicazione** con copia della Sintesi, conflitto di nome case-insensitive,
  sorgente inesistente, sorgente senza documento), Sintesi (lettura,
  salvataggio, validazioni, separatori tra gruppi), stato e codice AGCOM
  (valori liberi in creazione e salvataggio, chip/tag in lista ed editor,
  etichette bottoni), tecnologia (modifica e tecnologia inesistente),
  **rinomina del nome** (modifica, duplicato, vuoto), **voci** (creazione,
  duplicato e varianti maiuscole/minuscole, duplicato sul seed, stesso nome
  ammesso in un'altra tabella), asset cache-busted (con marker JS di modale
  condiviso, prompt voce e bozza locale), generazione (contenuti e grassetto
  nel DOCX, download, **immagine del bollino presente/assente**, **skip se già
  aggiornata**, **forza nuova versione**, **nuova versione dopo modifica**,
  **stato Aggiornata/Superata e storico in editor**), bollino della tecnologia
  (**endpoint immagine** 200/404, **colonna in lista**, **badge accanto alla
  select** nell'editor), massiva **multi-campo**
  (anteprima con riepilogo per offerta, applicazione su campi fissi, voci e
  **tecnologia**, **voci assenti saltate**, **campo fisso vuoto riempito**,
  **tecnologia uguale → invariata**, tecnologia inesistente → 404,
  validazioni, doppia applicazione rifiutata, **pagina massiva con conferma,
  spinner, reset dell'anteprima, gruppi fisse/dinamiche e velocità derivate**,
  **marchio cliccabile verso l'elenco**, target rimossi alla
  cancellazione dell'offerta), bootstrap.
- I test girano su SQLite temporaneo e passano dall'HTTP layer
  (`TestClient` + `dependency_overrides`), come da best-practice.
- `ruff` e `mypy --strict` puliti.

## 11. Verifiche non coperte da test automatici

- Il comportamento JS dell'editor (live update, layout, "Nuova voce…") è
  verificato con uno smoke su DOM simulato, non in un browser reale: un giro
  manuale in browser resta consigliato.
- Anche il **blocco di "Genera Sintesi (.docx)" con modifiche non salvate** è
  lato client (il server non conosce lo stato dell'editor): da verificare a
  mano in browser.
- Il **ripristino della bozza locale** dopo reload (modale "Riprendi le
  modifiche"/"Scarta") è lato client: da verificare a mano in browser.
- Non esiste ancora un test end-to-end in browser (Playwright o simili).

## 12. Limiti noti interni (non funzionali)

- Alcune query di sola lettura vivono nelle route delle pagine
  (`pages.py`) per comodità: accettato per l'MVP, da spostare nei servizi in
  fase di rifinitura.
- Il confronto dei valori nelle massive è per stringa esatta (`10 euro` ≠
  `10 €`): è una scelta documentata, non un bug.
