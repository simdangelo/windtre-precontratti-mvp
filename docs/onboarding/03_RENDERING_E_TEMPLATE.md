# Rendering, template e output documentali

## Contratto del motore di generazione

`DocumentService.execute_asynchronous_document_compilation` legge un'offerta e le sue tabelle, prepara un dizionario `synthesis_payload`, sceglie i nomi, richiama il generatore DOCX e XLSX, converte entrambi in PDF e inserisce lo storico. Non invia file a GCS: costruisce URL che sembrano puntare al bucket `w3-precontratti-outputs`, ma gli artefatti effettivi risiedono in `/tmp/compilation_workspace`.

Il payload contiene `technology_code`, `placeholders` e `tables`. I placeholder calcolati includono operatore, stato/codice, date formattate, territorio, mercato, metodo di pagamento, clientela, prezzo, PO, data documento e velocità. `Very Mobile` cambia operatore e URL di trasparenza; i segmenti con `MOB` e Very Mobile sono classificati come mercato mobile, tutti gli altri come fisso.

La clientela è derivata dai tre prezzi di attivazione non nulli. In assenza di prezzi specifici, il servizio inserisce tutti e tre i target. I placeholder dei prezzi di attivazione preferiscono i campi strutturati dell'offerta; altrimenti eseguono una ricerca lessicale nelle label padre e figlio contenenti “attivazione”, “già/gia”, “nativo” o “portabilità/portabilita/mnp”. Questa euristica va sostituita da un modello esplicito se i template reali dipendono dal risultato.

## Placeholder globali

Il renderer cerca token `{{chiave}}` in paragrafi e celle delle tabelle Word, e in qualunque cella Excel. Le chiavi costruite dal servizio sono:

| Placeholder | Fonte |
| --- | --- |
| `operatore`, `pagina_web`, `mercato_riferimento` | Segmento |
| `stato_offerta`, `agcom_code`, `po_code` | Lifecycle e PO |
| `data_inizio`, `data_fine`, `data_documento` | Date dell'offerta e tempo di generazione |
| `nome_offerta`, `tecnologia`, `prezzo` | Metadati offerta |
| `tecnologia_rete`, `velocita_download`, `velocita_upload` | Mappa `TECHNOLOGY_SPEEDS` |
| `modalita_pagamento`, `target_clientela` | Campi offerta e prezzi attivazione |
| `<IDENTIFICATORE>_notes` | `note_links.html_content` |
| `<IDENTIFICATORE>_notes_plain`, `note_regolatorie_plain` | Nota convertita in testo semplice Unicode |

L'elenco `TECHNOLOGY_SPEEDS` comprende 5G (2000/200 Mbps), 4G (300/50), FTTH (2500/1000), FTTC (200/20) e FWA (300/50). La mappa è dato applicativo fisso: non esiste configurazione per segmenti, offerte full speed o data di validità.

## Ruolo dei template rispetto alle tabelle dinamiche

La domanda operativa più frequente è: «Se dall'app posso creare un numero qualsiasi di tabelle padre-figlio, a cosa serve un template Word con placeholder fissi?». I due elementi non si sostituiscono: il template fornisce la **forma e i contenuti statici** del documento, mentre i dati dell'app forniscono i **contenuti variabili strutturati**. Il renderer combina i due.

### Cosa mette il template

Il master Word contiene l'identità visiva del documento: intestazioni, piè di pagina, loghi, titoli fissi, testi legali, note corporate, margini, font e tabelle statiche. Al suo interno ci sono due tipi di placeholder:

1. **Placeholder globali** per i metadati dell'offerta, come `{{nome_offerta}}`, `{{prezzo}}`, `{{agcom_code}}`, `{{data_inizio}}`. Questi vengono sostituiti con i valori del record `offers`.
2. **Placeholder di tabella** per i dati dinamici, come `{{SERVIZI_parent_0_label}}` e `{{SERVIZI_parent_0_value}}`. Questi segnano dove il motore deve inserire righe e valori provenienti dalle `dynamic_tables`.

Senza template, il documento sarebbe un assemblaggio generico di tabelle. Il template garantisce che l'output abbia l'aspetto, l'ordine e i testi fissi approvati per la comunicazione aziendale.

### Cosa mettono i dati dell'app

Dall'app non si creano "tabelle Word", ma **record JSON** collegati a un'offerta. Ogni record ha:

- un identificatore, per esempio `PREZZO`, `COSTI`, `SERVIZI`, `DURATA`;
- un array di righe padre, ciascuna con `label`, `value` e figli;
- note e link.

Questi record sono indipendenti dal template: possono essere aggiornati, duplicati, convalidati e riusati. Quando parte la generazione, il motore mappa i dati JSON sui placeholder del template.

### Come avviene la mappatura

Il renderer apre il template, scorre le tabelle Word e cerca celle che contengono marker come:

```text
{{SERVIZI_parent_0_label}}
{{SERVIZI_parent_0_value}}
{{SERVIZI_child_0_0_label}}
{{SERVIZI_child_0_0_value}}
```

L'indice numerico nel marker corrisponde alla posizione della riga nell'array JSON, non al suo `id`. Per esempio, il primo padre della tabella `SERVIZI` nel JSON va nel marker `parent_0`, il secondo in `parent_1`, e così via. I figli seguono la notazione `child_<padre>_<figlio>`.

Questo significa che il template non deve contenere una tabella vuota da riempire magicamente, ma deve contenere **tante righe predefinite quante sono le righe massime** che si vogliono supportare. Se il JSON ha meno righe, il motore elimina le righe in eccesso; se ne ha di più, le righe eccedenti non trovano marker e non vengono renderizzate.

### Esempio pratico

Ipotizza una tabella `PREZZO` che può contenere fino a 5 padri e ogni padre fino a 2 figli. Il template Word deve contenere marker fino a:

```text
{{PREZZO_parent_0_label}} ... {{PREZZO_parent_0_value}}
{{PREZZO_child_0_0_label}} ... {{PREZZO_child_0_0_value}}
{{PREZZO_child_0_1_label}} ... {{PREZZO_child_0_1_value}}
{{PREZZO_parent_1_label}} ... {{PREZZO_parent_1_value}}
...
{{PREZZO_parent_4_label}} ... {{PREZZO_parent_4_value}}
{{PREZZO_child_4_0_label}} ... {{PREZZO_child_4_0_value}}
{{PREZZO_child_4_1_label}} ... {{PREZZO_child_4_1_value}}
```

Se l'editor inserisce 3 padri e il primo ha 1 figlio, il motore:

- popola i marker di `parent_0`, `child_0_0`, `parent_1`, `parent_2`;
- rimuove le righe con `parent_3`, `parent_4` e i figli rimanenti.

Il documento finale ha quindi la stessa struttura approvata, ma solo le righe effettivamente compilate.

### Layout affiancato e verticale

Nel **layout affiancato** si mette solo il marker della label nella cella sinistra e la cella destra rimane vuota: il motore scrive il valore nella cella adiacente. È adatto a tabelle classiche a due colonne.

Nel **layout verticale** si mettono entrambi i marker, `..._label` e `..._value`, in celle o righe distinte. È adatto a elenchi compatti a colonna singola.

La scelta del layout è decisione del template author, non dell'editor che inserisce i dati.

### Limite importante

La flessibilità dell'app è nella **varietà dei contenuti**, non nella **capacità infinita del template**. Se un editor aggiunge nel JSON più righe di quante il template preveda, le righe in più non appariranno nel documento. Per questo occorre progettare il template con il numero massimo di righe richiesto dal segmento, come indicato nel requisito per ciascun mercato.

### Analogia con il foglio Excel

Lo stesso principio vale per la Trasparenza: il template Excel contiene il layout AGCOM, le celle di intestazione e il marker `[INIZIO_TABELLA_PREZZI]`. I dati dell'app vengono inseriti sotto quel marker. Qui il problema è ancora più delicato perché inserire righe in Excel può spostare formule e intervalli: il template deve essere preparato tenendo conto di queste espansioni.

## Rich text e hyperlink

I valori delle celle Word passano da `_write_formatted_cell_text`; i paragrafi che sostituiscono placeholder passano dalla formattazione delle run. Il parser supporta:

| Sintassi | Risultato |
| --- | --- |
| `**testo**`, `<b>testo</b>` | grassetto |
| `<i>testo</i>` | corsivo |
| `^1^`, `<sup>1</sup>` | apice |
| `<sub>2</sub>` | pedice |
| `https://dominio` | hyperlink Word blu e sottolineato |
| `[Etichetta](https://dominio)` | hyperlink con label |
| `[Etichetta](https://dominio "Tooltip")` | hyperlink con ScreenTip |

Per Excel `clean_markup` rimuove tag HTML elementari e simboli Markdown; `html_to_unicode_sub_super` converte apici/pedici limitati in caratteri Unicode e `<br>` in newline. Il rendering non sanitizza URL contro protocolli non HTTP in modo strutturato: nel contesto business va introdotta un'allowlist e va definito chi può introdurre link esterni.

## Bollini e accessibilità

Sono configurati asset e descrizioni alternative per FTTH, FTTC, FWA e 5G. Il risolutore prima cerca `templates/assets/` con i nomi della mappa, quindi usa nomi locali in `templates/bollini/`; ciò consente compatibilità con asset esistenti ma crea due convenzioni. Quando trova un file, aggiunge un'immagine larga 14 pt e prova a impostare `descr` nel `docPr` OpenXML. Se l'API interna di `python-docx` cambia, l'eccezione viene ignorata.

Il bollino può essere invocato dal token `$Bollino$`, con qualunque combinazione di maiuscole/minuscole, oppure aggiunto per label che contengono “tecnologia”. Perciò la posizione precisa dipende dal contenuto del template e non è dimostrata automaticamente. La conformità richiede un test finale con tecnologia assistiva e un validatore PDF/UA: un ALT nel DOCX non garantisce che il convertitore lo mantenga nel PDF.

## Trasparenza XLSX

Il renderer apre il workbook attivo, sostituisce placeholder, cerca label specifiche per scrivere tecnologia e velocità e quindi cerca una cella contenente `[INIZIO_TABELLA_PREZZI]`. Se il marker esiste, lo svuota e inserisce righe successive, scrivendo label in colonna B e valore in C. Le righe padre e figlio sono appiattite; il figlio riceve il prefisso testuale `  - `.

`openpyxl.insert_rows` sposta le celle ma non aggiorna automaticamente le formule, riferimenti, grafici, nomi o layout complessi. Il codice non implementa l'aggiornamento di formule dichiarato nel LLD. Per un template AGCOM reale, ogni modifica alla zona dinamica deve quindi essere verificata da test che aprono il file in Excel/LibreOffice e confrontano formule, aree di stampa e rendering PDF.

La funzione di print setup imposta A4 verticale, margini da 0.25 e fit-to-page in larghezza e altezza. È una scelta globale e può comprimere documenti lunghi; non è una prova di conformità con il vademecum AGCOM.

## Conversione PDF e Microsoft Graph

Il client `Graph` usa client credentials OAuth2 verso Azure AD, memorizza token e scadenza in memoria, carica il file in una cartella OneDrive che include un `run_id`, richiede il contenuto con `?format=pdf`, gestisce manualmente il redirect Azure Blob senza header Authorization e infine tenta la cancellazione. Riprova per status 400, 429, 500, 502, 503 e 504, con `Retry-After` o backoff esponenziale fino a cinque retry. Il codice tratta 400 come transitorio, scelta che potrebbe moltiplicare errori di input persistenti.

Per la Sintesi Graph è obbligatorio: credenziali assenti o conversione fallita sollevano `RuntimeError`. Per la Trasparenza Graph è preferito; fallendo prova Spire.XLS e, se fallisce anche questo, `libreoffice --headless --convert-to pdf:calc_pdf_Export`. Il tentativo di rimuovere watermark/pagine di valutazione Spire tramite `pypdf` è un workaround non idoneo come garanzia di licensing o accessibilità.

## Naming e artefatti

Per WINDTRE il nome base predefinito della Sintesi è `<nome>_<tecnologia>_<prezzo>`, quello della Trasparenza è `trasparenza_<nome>`; vengono aggiunti suffix `NUOVA`, `COD_<codice>` o stato. Per Very Mobile, se fornito, il nome custom viene usato togliendo una eventuale estensione docx/xlsx/pdf e rimettendo l'estensione corretta. Il normalizzatore converte spazi in underscore, rimuove tutto ciò che non appartiene a `[A-Za-z0-9._-]` dalla base e tronca a 160 caratteri contando l'estensione.

La sanificazione non normalizza l'estensione, non verifica che il risultato non sia vuoto, non risolve collisioni dopo troncamento e non assicura PO nel nome Very Mobile. Il controllo 2 MB è un warning post-conversione. Un job production deve fallire in modo esplicito oppure generare un artefatto corretto quando una policy Adobe non è soddisfatta.