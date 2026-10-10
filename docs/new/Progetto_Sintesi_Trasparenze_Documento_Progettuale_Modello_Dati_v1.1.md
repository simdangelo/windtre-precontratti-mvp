# Sintesi & Trasparenze — Documento di inquadramento per la progettazione del modello dati

**Versione:** 1.1 · **Data:** 5 ottobre 2026 · **Derivato da:** Documento descrittivo v0.2 e Documento di inquadramento v1.0, corretto con le precisazioni dello sviluppatore
**Destinatario:** un LLM (o un progettista) che deve aiutare a definire il **modello di business e il modello dati** dell'applicazione.

---

## 0. Scopo, focus e come usare il documento

Questo documento contiene **solo ciò che serve a progettare il modello dati**. Il **focus primario** è uno solo:

> Creare un documento markdown in cui viene definito un database model, con le relazioni tra tabelle, che permetta di gestire correttamente **(1) le tabelle dinamiche**, **(2) le modifiche massive** e **(3) la storicizzazione**. In questo documento deve essere presente una descrizione del modello che mi faccia capire quali esigenze sono state risolte e quali ancora da risolvere e perche non sono state risolte. Si faccia inoltre presente se qualche esigenza non puo essere soddisfatta e se requisiti piu rigidi possono invece risolvere questa esigenza (noi parleremo con l'area dedicata e chiederemo se potremmo portare avanti le richieste che tu eventualmente chiederai).

Quando il modello sarà chiaro e si saprà come gestire questi tre aspetti, si affronteranno i punti aperti secondari (significato esatto di "chiusa", permessi trasversali tra segmenti, date separate, migrazione, ecc.). Questi punti sono elencati alla sezione 12 e **non vanno risolti ora**: il modello deve solo non impedirne la gestione futura.

Il documento **non propone soluzioni al modello dati**. Descrive il dominio, i principi già decisi (sezione 3), i dati reali, i vincoli, i problemi (sezione 10) e i casi d'uso contro cui il modello deve reggere (sezione 11). Il compito di chi legge è proporre un modello dati e di business, dichiarando le ipotesi dove restano decisioni aperte.

**Etichette di affidabilità**

| Etichetta | Significato |
|---|---|
| **[CERTO]** | Requisito o decisione confermata dallo sviluppatore/cliente, o osservato in modo coerente |
| **[DECISO]** | Scelta di perimetro o di progetto presa per semplificare: si assume vera ora |
| **[PROBABILE]** | Emerge da una sola fonte o è l'aspettativa di un referente |
| **[APERTO]** | Nessuna risposta o risposte divergenti |
| **[INFERENZA]** | Lettura dell'autore, da verificare |
| **[CAMPIONE]** | Osservato in un campione di 32 file reali del cliente (20 Sintesi, 12 Trasparenze): sono solo esempi, non rappresentativi, e riflettono il processo manuale as-is |

---

## 1. Il progetto in una pagina

Un operatore telefonico (WINDTRE, più il marchio Very Mobile) deve produrre, per ogni offerta commerciale, due documenti regolamentari:

- la **Sintesi Contrattuale** (documento per il cliente, Word e poi PDF), organizzata in sezioni e **tabelle padre/figlio**;
- la **Trasparenza Tariffaria** (scheda **Excel con struttura rigida imposta da AGCOM**, più un PDF).

Oggi questi documenti sono file sparsi sui PC delle persone del marketing, compilati a mano. Ogni modifica comune a molte offerte va rifatta file per file, e la compilazione manuale produce **disallineamenti** tra Sintesi e Trasparenza e tra documenti diversi.

Si vuole una **web app** in cui il marketing inserisce **una sola volta** i dati di un'offerta in un database centrale, che diventa l'**unica fonte di verità**: da lì si generano sia la Sintesi sia la Trasparenza, e per costruzione non possono più divergere. Il requisito più enfatizzato è la **modifica massiva**: cambiare un valore una volta e propagarlo alle offerte interessate.

**Il nodo centrale.** Le Sintesi contengono tabelle la cui struttura varia da offerta a offerta e che l'MVP salva come JSON senza schema. Le modifiche massive e la storicizzazione richiedono invece dati **comparabili tra offerte e nel tempo**. Libertà di struttura e capacità di operare in massa sono in tensione: il modello deve risolverla.

Esiste già un **MVP** (Cloud Spanner, dialetto PostgreSQL); i suoi limiti sono alla sezione 9.

---

## 2. Utenti e perimetro

Gli utenti sono circa venti persone del **marketing**, non tecniche, divise in **nove segmenti** [CERTO]: Mobile GA Consumer, Mobile CB Consumer, Mobile GA Microbusiness, Fisso GA e Cross Selling Consumer, Fisso CB Consumer, Fisso GA e Cross Selling Microbusiness, Fisso CB Microbusiness, Etnico Consumer GA/CB, Very Mobile (struttura simile ma non identica a WINDTRE). Mobile CB Microbusiness non è impattato. Sigle (non confermate): GA = acquisizione, CB = base clienti, CNS/MB = Consumer/Microbusiness, CS = Cross Selling.

Ogni utente **modifica** solo offerte del proprio segmento [CERTO]. Le questioni di visibilità trasversale e di campi comuni a più segmenti sono **rimandate** [DECISO].

Le modifiche commerciali sono pianificate (*canvas*, 3-4 volte l'anno) e toccano molte offerte insieme; quelle regolamentari sono imprevedibili [CERTO].

---

## 3. Principi di modello già decisi

Questi principi sono **vincoli di partenza** per il modello.

1. **Offerta = Sintesi = Trasparenza** [CERTO]. Nel modello di business esiste una sola entità, l'**offerta**, e a ciascuna corrispondono **una e una sola Sintesi e una e una sola Trasparenza**. L'offerta è identificata dal suo **nome**. Se all'interno contiene più punti prezzo (es. prezzo per nuovi clienti, prezzo convergente, seconda linea), sono **contenuto dell'offerta**: la Sintesi è comunque una sola.
2. **Il nome dell'offerta è unico** [DECISO]. Nei file di esempio lo stesso nome commerciale compare con prezzi diversi, ma per semplificare si impone l'unicità come requisito.
3. **Fonte unica di verità** [CERTO]. L'offerta nel database è l'unica fonte: popola **sia** la Sintesi **sia** la Trasparenza. I disallineamenti osservati nei file di esempio (stesso prodotto con prezzi, velocità o nomi diversi tra i due documenti; Sintesi senza Trasparenza e viceversa) sono **effetti del processo di compilazione manuale as-is**, non requisiti da replicare: l'applicazione deve eliminarli. Il campione va usato per capire i **contenuti**, non per ricostruire le incoerenze.
4. **La tecnologia determina bollino, velocità e attributi collegati** [CERTO]. È un requisito. I file di esempio che lo contraddicono (es. alcune offerte Very con velocità diverse a parità di tecnologia, offerte Mobile "shaped") non modificano il modello: sono trattati come eccezioni/errori as-is non rilevanti ora.
5. **Generazione dei documenti da template** [CERTO come idea di soluzione, non come requisito del cliente]. Il piano è avere un **template Word con campi di unione (merge fields)** riempito da una libreria Python (es. `docxtpl`) con i dati dell'offerta presenti nel database. L'alternativa, meno considerata, è generare l'intero Word con `python-docx` senza template. La Trasparenza usa il template Excel con griglia fissa. Implicazione per il modello: i dati dell'offerta devono poter essere **forniti al template** in una forma che le tabelle (con numero variabile di righe) possano ciclare.
6. **Nomi uniformi delle tabelle** [DECISO]. Le tabelle che rappresentano gli stessi contenuti avranno **gli stessi nomi in tutti i segmenti** (es. un solo titolo per "servizi a pagamento"), così da ridurre la variabilità (sezione 6.3).
7. **Il modello non deve blindare la struttura**: righe, padri e figli aggiuntivi devono poter essere aggiunti in futuro e il database deve poter accogliere nuovi campi non previsti oggi [CERTO].

---

## 4. I due documenti

### 4.1 Sintesi Contrattuale

Documento a sezioni; ogni sezione contiene **tabelle** e spesso **testo libero** (note, condizioni, anche molto lunghe) [CERTO]. Alcune parti sono comuni a tutte le offerte, altre variano. Secondo il requisito, "i soli elementi fissi sono etichette e titoli; tutti gli altri campi sono variabili, con frequenze diverse" [CERTO].

Dal campione: la Sintesi ha una data di disponibilità (inizio) e la frase fissa "valida fino alla chiusura in sottoscrivibilità", non una data di fine; non riporta né stato né codice AGCOM [CAMPIONE]. La **tecnologia** compare nella Sintesi e determina un'immagine (bollino) associata automaticamente; i dettagli grafici sono fuori scopo, conta che la tecnologia sia un attributo dell'offerta da cui discendono contenuti e che debba essere modificabile in massa.

### 4.2 Trasparenza Tariffaria

Scheda Excel con **griglia fissa di circa 45 righe con etichette identiche** per tutte le offerte, più una zona di note libere [CAMPIONE]. Il formato è imposto da AGCOM e non è negoziabile [CERTO]. La griglia contiene: operatore, stato (o codice AGCOM), date di inizio e fine sottoscrivibilità, territorio, nome commerciale, tipologia (piano base o opzione/bundle), piani compatibili, pagina web, mercato, modalità di pagamento, target clientela, tecnologia, velocità download/upload, prezzi di attivazione per target (già clienti, nuovi nativi, nuovi in portabilità) in due colonne ("a listino" / "in promozione"), durata promozione, costo di disattivazione, durata minima, costo di recesso, prezzi ricorrenti e a consumo (a regime / in promozione), servizi inclusi.

Caratteristiche rilevanti per il modello: alcuni valori sono **composti con "/"** a significato posizionale (es. scatto alla risposta con 4 valori); le convenzioni di assenza ("-", "ND", vuoto) non sono uniformi; molti vocabolari sono liberi; la parte finale delle note è ricorrente e quella iniziale specifica dell'offerta; il regime IVA dipende dal segmento (Consumer inclusa, Microbusiness esclusa) [CAMPIONE].

Il **codice AGCOM** è un UUID di 36 caratteri assegnato da AGCOM dopo il caricamento (entro ~10 giorni) e scritto nella cella "Stato dell'offerta" al posto di "Nuova" [CERTO nel campione].

### 4.3 Il rapporto tra i due documenti

Poiché l'offerta è la fonte unica (principio 3), Sintesi e Trasparenza sono **due viste generate dagli stessi dati**. Restano due cose da modellare:

- i dati comuni (prezzo, costo di attivazione, durata, velocità, tecnologia, nome) vivono **una sola volta** nell'offerta e alimentano entrambi;
- esistono dati propri di un solo documento (testi della Sintesi, note e campi specifici della griglia della Trasparenza) e i due documenti hanno **cicli di vita non allineati**: molti aggiornamenti toccano solo la Sintesi [CERTO]. Il sistema deve poterli generare separatamente.

Come ogni dato dell'offerta si proietta nei campi della griglia della Trasparenza (mappatura) non è documentato: fa parte del progetto [APERTO].

---

## 5. Entità di dominio emerse

Non è un modello dati, ma l'elenco dei concetti che il modello deve esprimere.

| Concetto | Descrizione | Stato |
|---|---|---|
| **Segmento** | Uno dei nove gruppi; porta permessi e regime IVA | [CERTO] |
| **Offerta** | Unità unica: identificata dal nome (univoco), una Sintesi, una Trasparenza, un segmento | [CERTO] |
| **Tecnologia** | Attributo dell'offerta; determina bollino, velocità e attributi collegati | [CERTO] |
| **Campo scalare** | Valore singolo dell'offerta (nome, prezzo base, costo di attivazione, date, …) | [CERTO] |
| **Tabella** (padri e figli) | Struttura dati della Sintesi, con titolo standardizzato; presenza e contenuto variabili per offerta | [CERTO] |
| **Voce** (padre/figlio) | Riga logica di una tabella, con etichetta, valore e note | [CERTO] |
| **Testo libero / blocco comune** | Note e paragrafi, spesso ripetuti uguali o quasi in molti documenti | [CAMPIONE] |
| **Opzione collegata** | Servizio aggiuntivo (es. Reload Forever, Più Sicuri Mobile) con proprie descrizioni/prezzi | [CAMPIONE] |
| **Cluster di modifica** | Raggruppamento di offerte per cui è mappata una modifica massiva (sezione 8.3) | [PROBABILE] |
| **Codice AGCOM e stato** | UUID e stato (Nuova/Aperta/Chiusa) dell'offerta/Trasparenza | [CERTO] |
| **Documento generato** | File prodotti (Sintesi Word/PDF, Trasparenza Excel/PDF), con versioni | [CERTO] |
| **Registro di audit / storico** | Traccia di ogni operazione e dello stato dei dati nel tempo | [CERTO] come esigenza |
| **Configurazione globale** | Parametri comuni (es. coefficiente RDA) | [CERTO] |

---

## 6. Le tabelle dinamiche (cuore del problema)

### 6.1 Struttura logica [CERTO]

Una tabella ha un **titolo** e un insieme di **padri** (voci principali, es. "Costo mensile", "Costo di attivazione"), ciascuno con **figli** (sotto-voci, es. "Già clienti", "Nuovi clienti in portabilità"). Un padre può avere un valore proprio, essere solo un'intestazione, avere figli con valore, ecc. (quattro combinazioni documentate nell'MVP). Sotto la tabella possono esistere **note** riferite a padri o figli, con link. I numeri di padri e figli osservati sono solo massimi: **non vanno blindati**.

Regole di valore: "ND" → in output "Non applicabile"; valore vuoto → la riga non compare [CERTO come accordo]. (Quando un valore è ND e quando è vuoto è un dettaglio rimandato.)

### 6.2 Tabelle fisse e tabelle dinamiche

Nell'MVP alcune tabelle sono **predefinite** nel template (struttura e voci note, valori da riempire), altre sono **create dall'utente** da frontend con titolo, padri e figli. Nel Fisso alcune tabelle sono identiche in tutti i segmenti ("Servizio/i e apparecchiature", "Velocità", "Durata, rinnovo e risoluzione"), altre variano ("Prezzo", "Costi"); nel Mobile quasi tutte differiscono leggermente tra segmenti [PROBABILE]. Le tre categorie esplicitamente dinamiche nell'MVP sono Prezzo, Costi, Servizi.

Nota sulla forma fisica: nei documenti Word esistono tabelle con una, due o tre colonne a seconda del segmento e perfino nello stesso segmento. È una questione di **presentazione nel template** e non incide sullo schema logico padre→figli→valore: **non è rilevante per il modello**.

### 6.3 Variabilità e uniformità

- **Presenza variabile.** La presenza stessa di una tabella cambia da offerta a offerta: tabella "Daily Pass" solo in alcune offerte Mobile Microbusiness; tabella "Costi" ripetuta due o tre volte nel Fisso; coppie di tabelle "Descrizione/Prezzi" ripetute per ogni **opzione collegata** nel Mobile CB (una Sintesi ha dieci tabelle, un'altra nove) [CAMPIONE].
- **Stessa informazione, forme diverse.** I servizi aggiuntivi (Reload Forever, Più Sicuri Mobile) sono una tabella nel Mobile CB, un blocco titolo+testo nel Mobile GA e nell'Etnico, una voce di costo nel Fisso [CAMPIONE].
- **Titoli non uniformi** per gli stessi contenuti ("Servizi a pagamento", "Servizi non inclusi", assorbiti in "Costi"; "Prezzo"/"Prezzi"; "Servizio/i e apparecchiature"/"Descrizione Offerta") [CAMPIONE].
- **Decisione:** le tabelle che rappresentano gli stessi contenuti avranno gli stessi nomi [DECISO]. Questo riduce la variabilità tra segmenti, ma **non elimina** la presenza variabile né la possibilità di aggiungere tabelle e voci nuove.

### 6.4 Le etichette delle voci (non il template)

Questo paragrafo non riguarda il template Word. Riguarda i **nomi delle voci** (padri e figli) **memorizzati nel database** e il fatto che le modifiche massive devono poter individuare "la stessa voce" in offerte diverse.

L'MVP identifica le voci per **posizione** nei template (`parent_0_label`, `child_0_1_value`): la posizione non esprime il significato. Il rischio ipotizzato è che operatori diversi chiamino la stessa voce in modo diverso ("velocità massima download" / "velocità massima scaricamento"), e che la modifica massiva debba agire su entrambe. Nel campione:

- per la sola voce "velocità massima" esistono cinque formulazioni (maschile/femminile, "stimata", numero di nota variabile da 1 a 4, indicazione del cluster nell'etichetta, minuscolo senza spazio);
- altri esempi: "Costo disattivazione servizio" / "…anticipata del servizio" / "Costo disattivazione"; "Eventuali sconti e loro durata" / "Eventuali scontistiche e loro durata";
- **dentro lo stesso segmento le etichette sono stabili** (otto Sintesi Fisso Microbusiness identiche), la divergenza segue per lo più il confine di segmento; il campione è piccolo [CAMPIONE];
- alcune etichette contengono un **numero di nota** variabile o una parte commerciale (cluster), quindi non sono puri nomi.

Poiché le tabelle avranno nomi uniformi (principio 6) e le Sintesi saranno generate da un template unico, il fenomeno dovrebbe ridursi. **Resta aperto se la stessa standardizzazione si applica anche alle voci (padri e figli)**, cioè se esiste un elenco condiviso di voci o se l'utente le scrive liberamente. Da questa decisione dipende molto come le modifiche massive riconoscono una voce [APERTO, decisione ad alto impatto].

---

## 7. Dove vivono i valori: ridondanza e relazioni

Lo stesso valore compare spesso in più punti. Con una fonte unica il problema non è più "allineare più file" ma **"come rappresentare nel modello che un dato compare in molti posti, perché cambiandolo una volta si aggiorni ovunque"**.

**Tre posizioni di un valore nell'offerta**

1. **Scalare dell'offerta** (nome, tecnologia, prezzo base, costo di attivazione, date, codice).
2. **Cella di una tabella dinamica** (costo SIM, SMS extra soglia, penali, durate).
3. **Dentro testo libero** (frasi che citano prezzi, rate, durate, riferimenti normativi).

**Ripetizione dello stesso valore** [CAMPIONE]. Sintesi Fisso "Professional": il prezzo 31,99 compare in tre blocchi (cella Prezzo e due paragrafi), la rata del modem 5,99 in tre, il costo di attivazione 1,99 in due. Etnico "Unlimited Full": costo di attivazione 49,99 e rata 2,08 in tre blocchi ciascuno. Inoltre lo stesso valore compare nel nome file e nella Trasparenza (cella e nota).

**Relazioni aritmetiche tra campi.** Il prezzo totale è dichiarato nel testo come somma di componenti: "31,99 euro è composto, per i primi 48 mesi, da: 21 euro di canone, 5 euro di chiamate illimitate e 5,99 euro di rata del modem". Le somme tornano in tutti i casi controllati (21+5+5,99=31,99; 15+5+5,99=25,99; 19+9,99+3=31,99; 24+5,99=29,99; 30+5+5,99=40,99) [CAMPIONE]. Oggi la coerenza è mantenuta a mano; cambiare un componente impone di ricalcolare totale e frasi. Se l'utente inserisce il totale, i componenti o entrambi è [APERTO].

**Rateizzazione.** L'attivazione compare come importo totale e come rate ("49,99 euro" e "24 rate mensili di 2,08 euro") in tabella e in nota [CAMPIONE].

**Testi comuni con varianti.** Molti blocchi sono ripetuti in decine di documenti: frase introduttiva e di validità identiche in 18 Sintesi WINDTRE su 20; blocchi identici in 8-10 documenti Fisso. Ma la sezione "Modifiche" esiste in 8 varianti su 18 documenti, "Agevolazione Economica Utenti Disabili" in 4 varianti su 10, il testo sul recesso del Fisso in 3 varianti su 10. Non è noto se le varianti siano volute o residui della propagazione manuale. Valori e riferimenti ricorrenti, candidati a gestione centralizzata: costo SIM 10 € (6 Sintesi su 20), SMS extra soglia 0,29 € (6), GIGA giornaliero 0,99 € (4), disattivazione 10 € (4); delibere AGCOM citate nei testi (290/21/CONS in 12 Sintesi, 156/23/CONS in 10, 9/23/CONS in 8) [CAMPIONE]. Il modello deve decidere il rapporto tra testo "di catalogo" condiviso e personalizzazione per offerta.

**Valore dipendente (nota secondaria).** Il coefficiente RDA (giga usabili in UE) è aggiornato annualmente e il valore dipende dal canone (7,5 GB a 4,99; 14,9 GB a 9,99; 29,8 GB a 19,99, circa 1,5 GB per euro [INFERENZA]). Nell'MVP è un valore per chiave globale. Per ora è un esempio di valore derivato, non un caso prioritario.

**Fuori scopo ora [DECISO]:** le dipendenze tra segmenti (es. canone convergente citato in una Sintesi Mobile e in una Fisso con valori diversi 24,99 e 25,99) non vanno considerate.

---

## 8. Le modifiche massive

### 8.1 Il requisito [CERTO]

È il requisito **più enfatizzato**: applicare una modifica una volta sola e propagarla a tutte le offerte oppure a un sottoinsieme selezionato, per Sintesi, Trasparenze o entrambe. Prima di applicarla il sistema avvisa del numero di offerte coinvolte e chiede conferma (già nell'MVP) [PROBABILE]. È richiesta anche la **duplicazione** di offerte, singola o massiva.

### 8.2 Che cosa si vuole modificare

In linea di principio vorrei modificare qualasiasi cosa relativa ad una offerta, senza limiti: valori "fissi" (i.e. nome commerciale, tecnologia), valori di tabelle dinamiche. Si potrebbe pensare di voler modificare anche i nomi dei padri/figli, ma questo dipende da che tipo di soluzione implementeremo. Possiamo anche decidere di non poter modificare le etichette dei padri-figli (i.e. non e' possibile modificare l'etichetta "Prezzi gia clienti") ma soltanto i valori associati. Su questo possiamo fare delle proposte in modo da semplificarci il lavoro

### 8.3 Mappatura per cluster (nota di complessità, non gestita ora)

Le modifiche massive sono state finora **mappate per cluster di offerte** dagli utenti: ad esempio *il campo 3 della tabella Costi può essere modificato massivamente solo per le offerte del cluster "Netflix" e del cluster "Amazon"*. Se questa è la regola, il flusso utente naturale sarebbe:

1. l'utente **seleziona il cluster**;
2. il sistema mostra **tutti i valori modificabili su quel cluster**;
3. l'utente sceglie il valore da modificare e **seleziona le offerte** del cluster (tutte o solo alcune) su cui applicarlo;
4. il sistema applica la modifica.

**Nota:** sappiamo che questa complessità esiste (cluster come insieme di offerte, e per ogni cluster un insieme di campi modificabili), ma **per ora non verrà gestita**. Il modello non deve impedirla in futuro. Non vanno confusi questi cluster di modifica con i "cluster Giga" del Mobile (finiti/shaped/illimitati), anch'essi non trattati ora.

### 8.4 Altri aspetti, rimandati

Come si seleziona il gruppo di offerte in assenza di cluster, anteprima e annullamento, effetti sui documenti già generati (documenti "superati"), chi può eseguire modifiche su più segmenti: sono casi d'uso importanti ma **rimandati** (sezione 12).

---

## 9. Stato dell'MVP e scarti dal modello

L'MVP (documento "Database design", con 2 versioni in sequenza — l'MVP base e' la prima tabella; la v2 e' una alternativa piu completa) prevede: segmenti, utenti, ruoli per segmento (viewer/editor/admin), tecnologie (con bollino e velocità massime), modalità di pagamento, offerte, costi di attivazione per tipo di cliente (tre target), **tabelle dinamiche** (identificatore tra Prezzo/Costi/Servizi, titolo, contenuto JSON, note), **storico dei cambi di stato**, **snapshot delle tabelle congelati a ogni cambio di stato**, documenti (tipo, versione, flag corrente), configurazioni globali. Funzioni: creare offerte con campi fissi e tabelle dinamiche, generare Sintesi/Trasparenze da template con segnaposto posizionali, sostituire i bollini per tecnologia, modifica massiva su un **sottoinsieme di campi** con conteggio.

IMPORTANTE: questi MVP sono stati creati velocemente prima della raccolta di requisiti, quindi potrebbero essere completamente sbagliati e portarci fuori strada. Se credi siano dannosi o poco utili, non considerarli.

**Vincoli tecnici già presenti** (scelte di progetto, non requisiti del cliente): Cloud Spanner (dialetto PostgreSQL), FastAPI/SQLAlchemy, chiavi UUIDv4 generate dall'applicazione, file su Cloud Storage, identità tramite OIDC aziendale, SQLite per i test. L'MVP stesso riconosce che le tabelle dinamiche "non consentono modifiche massive, perché sono personalizzate sulla singola offerta".

**Dove il modello attuale non copre quanto richiesto:**

| Scarto | Dettaglio |
|---|---|
| Tabelle dinamiche | JSON senza schema: non interrogabile né modificabile in massa per voce |
| Storico | solo transizioni di stato; nessun log di tutte le modifiche, né delle massive, né delle cancellazioni (solo eliminazione logica) |
| Prezzo | un solo prezzo base; esistono più punti prezzo dentro l'offerta e il prezzo è somma di componenti |
| Campi liberi | nessuna collocazione se non il campo note; blocchi di testo comuni non modellati |
| Raggruppamenti | nessun concetto di cluster/etichetta di offerte per le modifiche massive |
| Copertura Trasparenza | senza corrispondenza nel DB: colonne "in promozione", durata promozione, costo di recesso, tipologia (piano base/opzione), piani compatibili, territorio, blocco servizi inclusi [INFERENZA sulle sole tabelle descritte] |
| Documenti | tipo `TEMPLATE_DOCX/XLSX` ambiguo (template o file compilato?); mancano tipi per Sintesi/Trasparenza generate |
| Date | un solo intervallo di validità per offerta (rimandato) |
| RDA | un valore per chiave globale; il valore dipende dal canone (secondario) |

---

## 10. I problemi da risolvere

Ordinati per priorità sul focus (tabelle dinamiche, modifiche massive, storicizzazione). Nessuna soluzione indicata.

**P1 — Rappresentare le tabelle dinamiche in modo comparabile.** Le tabelle non hanno schema fisso, ma devono poter essere interrogate e modificate in massa e riprodotte in un template. Occorre decidere l'**identità di una voce** (padre/figlio) indipendentemente da posizione, etichetta visibile, numero di nota e segmento. Vincoli: non blindare righe e voci; nuove tabelle e voci senza sviluppo; presenza variabile di tabelle per offerta; tabelle ripetute per opzione collegata; i nomi delle tabelle saranno uniformi (principio 6); se anche le voci siano standardizzate è aperto (6.4).

**P2 — Modifiche massive su dati a struttura variabile.** Individuare "la stessa voce" in offerte diverse (che può non esistere in alcune), applicare valore/etichetta/presenza/testo su un insieme selezionato di offerte, con conteggio e conferma, tracciando l'operazione come evento unico e coerente con lo storico. Include i campi scalari (tecnologia con bollino, prezzo base, costo attivazione) e i valori dentro le tabelle. La mappatura per cluster (8.3) è nota ma non gestita ora.

**P3 — Storicizzazione adeguata.** Stabilire cosa conservare e con quale granularità per poter ricostruire "com'era l'offerta (e quindi Sintesi e Trasparenza) in un dato momento": solo snapshot a ogni cambio di stato (come l'MVP), ogni singola modifica, ogni modifica massiva come evento a sé. Va conservata anche la **struttura** (quali tabelle e voci esistevano, rinominate o eliminate), oltre ai valori. Servono: confronto tra versioni, legame tra versione dei dati e file generati (i file precedenti non vanno sovrascritti), audit di tutte le operazioni degli utenti. Il cliente chiede una proposta con pro e contro per ciascuna opzione e non ha preferenze.

**P4 — Valori ridondanti e derivati.** Lo stesso valore vive in più posizioni (scalare, cella, frase, nota, Trasparenza), alcuni valori sono somme di altri. Il modello deve stabilire come un dato comune venga **riferito** (non copiato) nei punti in cui compare, se i totali sono calcolati dai componenti, e come gestire i valori incorporati nel testo libero in modo che una modifica massiva li aggiorni tutti.

**P5 — Testi comuni con varianti.** Rapporto tra testo di catalogo condiviso e personalizzazione per offerta/segmento; come si modifica in massa un testo che non è identico ovunque.

**P6 — Vincolo del formato AGCOM.** La Trasparenza ha griglia fissa con valori composti e vocabolari quasi liberi, mentre la Sintesi ha tabelle variabili. I dati necessari alla griglia devono essere **strutturati e validabili** (UUID del codice, date, numeri, unità), pur lasciando libertà nelle tabelle della Sintesi. La mappatura offerta → griglia è da costruire.

**P7 — Alimentazione del template.** I dati dell'offerta devono potersi trasformare nel contesto che il template Word (con campi di unione) riempie, comprese tabelle a numero variabile di righe, note sotto tabella, testi liberi e bollino per tecnologia.

---

## 11. Casi d'uso contro cui validare il modello

Alcuni sono descritti esplicitamente nei materiali, altri ricavati (ˆ).

| # | Caso d'uso | Mette alla prova |
|---|---|---|
| UC1 | Creare un'offerta (nome univoco) con campi scalari e tabelle (fisse e dinamiche) e generare Sintesi e Trasparenza dalla stessa fonte | P1, P6, P7 |
| UC2 | Registrare il codice AGCOM (UUID) sull'offerta e cambiare stato, conservando i file precedenti | P3 |
| UC3 | Modificare un'offerta già avanzata di stato (prezzo, tecnologia, testo) e poter ritrovare la versione precedente dei dati e dei file | P3 |
| UC4 | Duplicare un'offerta, singolarmente o in blocco | P1, P3 |
| UC5 | Modifica massiva di un **campo scalare** (tecnologia con bollino, prezzo base, costo di attivazione) su offerte selezionate, con conteggio e conferma | P2, P4 |
| UC6 | Modifica massiva del **valore di una voce dentro una tabella dinamica** (es. costo SIM 10 € in 6 Sintesi) quando la voce può non esistere in alcune offerte | P1, P2 |
| UC7 | Modifica massiva che **aggiunge, rinomina o elimina una voce o tabella** in molte offerte ˆ | P1, P2, P3 |
| UC8 | Aggiornare un **testo libero comune** (es. sezione "Modifiche", riferimento a una delibera) che esiste in più varianti | P5 |
| UC9 | Cambiare il **prezzo di un componente** e ottenere totale e frasi coerenti (21+5+5,99=31,99) ˆ | P4 |
| UC10 | Offerta con **opzioni collegate** che portano tabelle/prezzi (Mobile CB) o paragrafi (altri segmenti) | P1 |
| UC11 | Aggiornamento annuale del **coefficiente RDA** con valore dipendente dal canone ˆ (secondario) | P4 |
| UC12 | **Audit**: chi ha creato, modificato, inserito il codice, chiuso, eliminato, eseguito una massiva; ricostruire lo stato di un'offerta a una certa data | P3 |
| UC13 | **Aggiungere un nuovo campo o una nuova tabella** non prevista senza sviluppo | P1 |
| UC14 | **Modifica massiva per cluster** (selezione cluster → valori modificabili → selezione offerte): non gestita ora, ma non impedita dal modello | P2 |

---

## 12. Decisioni e punti aperti

### 12.1 Decisioni che influenzano il modello (da prendere o ipotizzare)

1. **Granularità della storicizzazione** (solo cambi di stato, ogni modifica, ogni massiva) e chi accede allo storico.
2. **Modifica sul posto o nuova versione** di un'offerta già avanzata, e su quali campi. Fino a decisione, il modello deve esplicitare l'ipotesi adottata.
3. **Standardizzazione delle voci** (padri e figli) oltre ai nomi delle tabelle: elenco condiviso oppure libere.
4. **Elenco puntuale dei campi modificabili in massa** per segmento/cluster e relativa frequenza (file non disponibili).
5. **Tipo di modifica massiva:** valore, etichetta, presenza di riga, testo libero.
6. **Prezzo totale e componenti:** cosa inserisce l'utente, il totale è calcolato?
7. **Testi comuni:** le varianti sono volute o accidentali; come gestire gli override.
8. **Mappatura Sintesi/offerta → griglia Trasparenza** (richiede lo "Schema Vademecum.xlsx" e la scheda vuota, non forniti).

### 12.2 Punti aperti rimandati [DECISO: dopo il modello]

Sono corretti e importanti, ma si affronteranno dopo aver definito come gestire tabelle dinamiche, modifiche massive e storicizzazione.

- Significato esatto di **CHIUSA** (non più sottoscrivibile o non più modificabile), riapertura, ruolo delle chiuse negli aggiornamenti regolamentari; stati realmente usati da ciascun segmento; "quattro file" per Sintesi e Trasparenza.
- **Date** separate di validità per Sintesi e Trasparenza.
- **Permessi:** visibilità trasversale, chi esegue modifiche che attraversano più segmenti, cancellazione di un'offerta.
- **Dipendenze tra segmenti** (convergenza, riferimenti incrociati).
- Regole speciali del **Mobile CB** sulla granularità delle trasparenze e sul punto prezzo più alto (con il principio 1 si assume 1 Sintesi = 1 Trasparenza).
- **Cluster Giga** (finiti/shaped/illimitati) e velocità dipendenti da altro che la tecnologia.
- Regola su **"ND" / vuoto / "-"**.
- **Volumi** e **migrazione** iniziale dai file esistenti (formati disomogenei, segnaposto residui "XX", "XXX", `$Nome POPZ$`).
- Significato di sigle (CVM, CDA, CR/CS).

### 12.3 Argomenti esclusi da questo documento (fase di implementazione)

Regole grafiche e accessibilità dei **bollini** e del PDF (PDF/UA, testo alternativo, titolo del documento); **naming dei file** e vincoli **Adobe** (PDF ≤ 2 MB, nome ≤ 160 caratteri, caratteri ammessi, nomi unici), file CSV di mappatura Adobe; **righe massime** per sezione; titoli al singolare/plurale; layout dei template e sintassi dei segnaposto; **consegna** dei file (email, cartelle, durata); dettagli di stack e infrastruttura oltre alla sezione 9.

---

## Appendice A. Esempi reali sintetici

**A.1 Etichette diverse per la stessa voce (velocità massima)**

```
Fisso Microbusiness : "Velocità massimo di connessione Internet"
Fisso CB Consumer   : "Velocità massima di connessione Internet"
Mobile/Etnico       : "Velocità di connessione Internet massima stimata (1..4)"
Etnico (cluster)    : "…massima stimata (4) 200 Giga Full Speed" / "… (3) Giga illimitati"
Very                : "Velocità di connessione internet massima stimata(2)"
```

**A.2 Un valore, molte posizioni (Sintesi Fisso "Professional")**

```
Prezzo 31,99 -> cella tabella Prezzo + paragrafo "composto da..." + paragrafo condizioni
Totale 31,99 = canone 21 + chiamate 5 + rata modem 5,99   (la rata 5,99 compare in 3 blocchi)
```

**A.3 Mappatura per cluster (esempio fornito dallo sviluppatore)**

```
Cluster "Netflix"  -> campo 3 della tabella Costi modificabile in massa
Cluster "Amazon"   -> campo 3 della tabella Costi modificabile in massa
Flusso: seleziona cluster -> vede i valori modificabili -> sceglie le offerte (tutte o alcune) -> applica
```

## Appendice B. Glossario minimo

- **AGCOM:** Autorità per le Garanzie nelle Comunicazioni. **Vademecum:** regole di compilazione dell'Excel della Trasparenza (delibera 252/16/CONS).
- **Sintesi Contrattuale / Trasparenza Tariffaria:** i due documenti (sezione 4); nel modello, due viste della stessa offerta.
- **Codice AGCOM:** UUID RFC 4122 di 36 caratteri assegnato dopo il caricamento.
- **Padre / Figlio / Voce:** voce principale e sotto-voci di una tabella. **Tabella dinamica:** tabella con padri e figli senza schema predefinito (JSON nell'MVP).
- **Punto prezzo:** variante di prezzo interna a un'offerta (nuovi clienti, convergente, seconda linea); non è un'entità separata.
- **Cluster di modifica:** insieme di offerte (es. "Netflix", "Amazon") per cui sono mappati i campi modificabili in massa. **Cluster Giga (Mobile):** finiti / shaped / illimitati (non trattato ora).
- **RDA:** coefficiente annuale di giga utilizzabili in UE. **PO:** codice tecnico dell'offerta Very Mobile. **Canvas:** cicli di revisione commerciale, 3-4 l'anno.
- **Convergenza:** offerta abbinata a SIM mobile o a luce&gas, con condizioni di prezzo dedicate.
- **docxtpl:** libreria Python che riempie un template Word con campi di unione usando i dati forniti. **python-docx:** libreria Python per generare un Word da zero.
