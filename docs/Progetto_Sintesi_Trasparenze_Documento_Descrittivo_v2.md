# Automazione di Sintesi Contrattuali e Trasparenze Tariffarie
## Documento descrittivo del progetto — stato della conoscenza al 2 ottobre 2026

**Versione:** 0.2 (bozza per revisione) · **Natura del documento:** descrittivo. Non propone soluzioni: fotografa ciò che si sa, ciò che è certo, ciò che è contraddittorio e ciò che manca.

**Novità della v0.2:** integrate le evidenze estratte da **32 file reali** messi a disposizione dal cliente (20 Sintesi Word e 12 Trasparenze Excel, cartella "DOC OFFERTE AS IS SOTTOSCRIVIBILI"). Le nuove evidenze sono raccolte soprattutto nelle sezioni 4.8, 5.4, 5.5, 6.5 e 7.7, e hanno aggiornato anche le sezioni 3.3, 4.4, 4.7, 11, 12, 13 e 14. Dove un'evidenza reale smentisce o precisa ciò che dicevano i requisiti, lo segnalo nel punto in cui il tema compare.

---

## 0. Come leggere questo documento

Questo documento è scritto per chi non ha mai visto il progetto. Racconta il contesto, gli utenti, i documenti da produrre, i dati coinvolti, i processi e i problemi aperti. Non contiene una soluzione tecnica: serve a mettere ordine prima di progettarla. Le domande per smarcare i dubbi sono raccolte alla fine (sezione 13), mentre lungo il testo i dubbi sono segnalati dove nascono.

### Convenzione di affidabilità

Ogni affermazione importante porta una di queste etichette, perché non tutto ciò che si legge nei materiali ha lo stesso peso.

- **[CERTO]**: stabilito nel requisito formale o confermato in modo esplicito e coerente da più fonti.
- **[PROBABILE]**: emerge da una sola fonte, oppure è l'aspettativa o l'opinione di un singolo referente, non una decisione formale.
- **[APERTO]**: nessuna risposta, risposta non pertinente o risposte divergenti.
- **[CONTRASTO]**: due o più fonti dicono cose incompatibili (raccolte nella sezione 12).
- **[INFERENZA]**: lettura mia, non scritta in nessun documento; va verificata.

### Fonti usate e sigle

| Sigla | Documento | Natura |
|---|---|---|
| **REQ** | "Requisito – Automazione creazione file precontratti" | Requisito del cliente, con commenti a margine di vari utenti |
| **MAN** | "Manuale di progettazione dei template – Sintesi & Trasparenze" | Manuale d'uso dei template Word, descrive il comportamento del prototipo |
| **DB** | "Database design" | Progettazione logica e fisica del modello dati dell'MVP, con tre varianti evolutive (NEW, NEW 2, NEW 3) |
| **MAIL1** | Email "a che punto siamo" (richiesta del 15/09/2026) | Richiesta di chiarimenti su campi emersi, azioni massive, cluster mobile |
| **MAIL2** | Email con i deliverable completati e le 9 domande sulla soluzione | Contiene risposte inline alle domande |
| **BRIEF** | Descrizione fornita a voce dallo sviluppatore | Contesto, obiettivo, problemi principali |
| **CAMP** | Campione di 32 file reali (cartella "DOC OFFERTE AS IS SOTTOSCRIVIBILI – REDUCED") | 20 Sintesi `.docx` e 12 Trasparenze `.xlsx` di offerte reali, organizzate per segmento |

### Il campione di file reali (CAMP)

Il cliente ha messo a disposizione un campione ridotto di documenti "as is" di offerte sottoscrivibili. Non è rappresentativo in senso statistico (due o tre documenti per segmento), ma è l'unica fotografia di come i documenti sono davvero oggi.

| Segmento | Sintesi (docx) | Trasparenze (xlsx) | Note |
|---|---|---|---|
| Mobile GA Consumer | 2 | 0 | Nessuna Trasparenza fornita |
| Mobile CB Consumer | 2 | 2 | Una delle due Trasparenze è **protetta da password** e non è leggibile |
| Mobile GA Microbusiness | 2 | 2 | |
| Fisso CB (e "CR") Consumer | 2 | 0 | La cartella delle Trasparenze è vuota |
| Fisso GA (e "CR") Microbusiness | 6 | 2 | Sintesi di tre famiglie di offerta, in varianti FTTC e FTTC Extra |
| Fisso CB Microbusiness | 2 | 2 | |
| Etnico Consumer GA/CB | 2 | 2 | |
| Very Mobile | 2 | 2 | |

Non c'è alcun campione dedicato a **Fisso GA e Cross Selling Consumer**, e il segmento Mobile CB Microbusiness (non impattato) è correttamente assente. Le cartelle del campione portano i nomi dei referenti: per minimizzare i dati personali non li riporto.

Le coppie Sintesi–Trasparenza **non si corrispondono** nel campione: spesso c'è una Sintesi senza la Trasparenza dello stesso nome e viceversa (dettagli nelle sezioni 4.8 e 5.5). Non si può quindi usare il campione per verificare in modo diretto la coerenza tra i due documenti della stessa offerta.

### Limiti del materiale

Prima di tutto è bene sapere cosa non ho potuto vedere, perché influisce sull'affidabilità di molte sezioni.

- Il REQ è un estratto testuale di un documento che conteneva molte **immagini** (le tabelle "come da immagine", i bollini, lo screenshot del Vademecum). Delle tabelle descritte nel REQ conosco quasi solo la numerosità di padri e figli. Il campione CAMP mi ha permesso di verificarne il contenuto reale per diversi segmenti, ma non per tutti.
- Dei file del campione ho letto **testo, tabelle, immagini incorporate e testo alternativo**, ma non l'aspetto grafico finale (impaginazione, colori, dimensioni reali dei bollini). Non ho potuto aprire la Trasparenza Mobile CB protetta da password.
- Sono citati ma **non forniti**: il Vademecum AGCOM (PDF), lo "Schema Vademecum.xlsx", la "scheda trasparenza tariffaria vuota.xlsx" con la mappatura dei campi, i file "azioni massive PRECONTRATTI FISSO all.xlsx" e "Confronti tabelle mkt FISSO.xlsx", le macro Excel dei gruppi Fisso e Mobile, il template Word proposto per le Sintesi del Fisso e la proposta di File System. Senza questi non conosco la **lista puntuale dei campi per cui gli utenti vogliono la modifica massiva**, che è il dato più importante per il progetto.
- L'attribuzione delle risposte inline in MAIL2 non è esplicita. Le tratto come espressione di un referente, non come decisione validata da tutti i segmenti.

---

## 1. Il progetto in breve

Un operatore telefonico (WINDTRE, con il marchio Very Mobile) deve produrre, per ogni offerta commerciale, due documenti regolamentari: la **Sintesi Contrattuale** (un documento per il cliente, oggi in Word e poi PDF) e la **Trasparenza Tariffaria** (una scheda in formato Excel con struttura imposta da AGCOM, più un PDF per il sito). Oggi questi documenti vivono come file sparsi sui PC delle persone del marketing dei vari mercati, e ogni modifica comune a molte offerte va rifatta a mano su ciascun file.

Si vuole una **web app** in cui gli operatori del marketing, ciascuno per il proprio mercato e segmento, inseriscono una sola volta i dati dell'offerta in un database centrale e generano da lì Sintesi e Trasparenze a norma. La funzione che gli utenti chiedono con più forza è la **modifica massiva**: cambiare un valore una sola volta e vederlo propagato a tutte le offerte interessate.

Il nodo progettuale è che le offerte sono molte, eterogenee, con tabelle proprie e campi propri, mentre la modifica massiva presuppone che i dati siano comparabili tra offerte diverse. Inoltre il **ciclo di vita dell'offerta** (Nuova, Aperta, Chiusa) e le regole su cosa sia modificabile e quando non sono ancora chiari.

Un **MVP esiste già** (prototipo dimostrativo con un modello dati su Cloud Spanner). Il lavoro in corso è capire i casi d'uso reali per far evolvere il database.

---

## 2. Contesto e dominio

### 2.1 Cliente e utenti

Gli utenti sono persone del **marketing** dei vari mercati, dipendenti di un operatore telefonico. Sono circa una ventina, divise in nove gruppi di lavoro (sezione 3). Non sono sviluppatori né esperti di dati: lavorano oggi con Word, Excel, PDF e macro.

### 2.2 I due documenti e perché esistono

La **Sintesi Contrattuale** riassume le condizioni economiche e contrattuali dell'offerta in una struttura a sezioni e tabelle. Viene pubblicata in PDF sull'e-commerce, nei punti vendita (tramite il sistema Adobe) e sulle pagine di trasparenza dei siti windtre.it e verymobile.it. Contiene anche i **bollini** grafici che identificano la tecnologia di rete, richiesti dalle delibere AGCOM.

La **Trasparenza Tariffaria** è una scheda in **Excel con struttura fissa e rigida**, dettata dal Vademecum AGCOM (delibera 252/16/CONS, allegato 1). Viene caricata sul portale AGCOM "Confronta offerte"; in caso di non conformità il caricamento viene rifiutato. Una versione PDF viene pubblicata anche sui siti. Il formato è **non negoziabile** [CERTO].

Le due cose sono documenti **distinti**, con contenuti e finalità diverse: una modifica all'uno non impatta necessariamente l'altro, e il sistema deve poterli trattare separatamente [CERTO].

### 2.3 Come si lavora oggi (AS-IS)

Si parte da un documento esistente salvato sul PC di una persona, si modificano a mano solo i punti necessari (o si crea da zero) e si ripete lo stesso intervento su ogni documento coinvolto. Poi i file vengono caricati a mano sui vari canali. Le persone usano anche **macro Excel** (per Fisso e per Mobile) con cui compilano i campi variabili e rigenerano le sintesi (MAIL2); queste macro non mi sono state fornite.

Le modifiche **commerciali** sono pianificate e avvengono in occasione dei *canvas* (3-4 volte l'anno). Quelle **regolamentari** dipendono da delibere esterne e sono imprevedibili. Ogni modifica commerciale comporta la produzione contestuale di più Sintesi e Trasparenze, per più mercati [CERTO].

### 2.4 Cosa resta fuori dal sistema

La distribuzione dei file sui canali (siti, Adobe, portale AGCOM) **resta in carico agli utenti** [CERTO]. Il sistema produce i file, non li pubblica.

---

## 3. Gli utenti: mercati, segmenti, ownership

### 3.1 I nove gruppi

Il REQ elenca i gruppi con le persone abilitate (omesse qui). Nove sono impattati, uno no.

| # | Gruppo | Note |
|---|---|---|
| 1 | Mobile GA Consumer | |
| 2 | Mobile CB Consumer | |
| 3 | Mobile GA Microbusiness | |
| 4 | Fisso GA e Cross Selling Consumer | |
| 5 | Fisso CB Consumer | |
| 6 | Fisso GA e Cross Selling Microbusiness | |
| 7 | Fisso CB Microbusiness | |
| 8 | Etnico Consumer GA/CB | |
| 9 | Very Mobile | Struttura simile ma non identica a WINDTRE |
| — | Mobile CB Microbusiness | **Non impattato** dal progetto |

Ogni gruppo ha da una a quattro persone. Il numero di nove segmenti coincide con quello del DB [CERTO].

### 3.2 Segregazione e ownership

Ogni utente può **modificare solo** i documenti del proprio mercato e segmento [CERTO]. Su cosa possa **vedere** c'è un'evoluzione: nel REQ si parla di "gestire solo mercato e segmento di sua competenza", mentre in MAIL2 viene riportata la richiesta degli utenti di **vedere anche le offerte degli altri gruppi**, modificando soltanto le proprie [PROBABILE]. Le due formulazioni non coincidono (sezione 12).

Il DB prevede un modello di ruoli per segmento (viewer, editor, admin) e un'autenticazione tramite identità aziendale (OIDC). L'autenticazione non è citata nel REQ: è una scelta già presente nell'MVP [INFERENZA].

### 3.3 Sigle del dominio da confermare

I documenti usano sigle mai definite. Le interpretazioni qui sotto sono mie e vanno confermate.

- **GA** e **CB**: probabilmente acquisizione di nuova clientela e base clienti esistente (Gross Add / Customer Base) [INFERENZA].
- **CNS** e **MB**: Consumer e Microbusiness.
- **CVM**: compare in "FISSO CNS CVM / Cross Selling" senza spiegazione [APERTO].
- **CDA**: compare in una tabella Etnico, probabilmente il costo di attivazione [INFERENZA]. Nelle Sintesi Etnico reali la tabella corrispondente si intitola "Costo di attivazione", il che rafforza l'ipotesi.
- **CS** e **CR**: il REQ parla di "Cross Selling (CS)", mentre i nomi delle cartelle del campione usano "CR" (es. "FISSO CB e CR", "FISSO GA e CR"). È verosimile che indichino lo stesso concetto, ma non è detto [APERTO].
- **Punto prezzo**: usato per descrivere la granularità delle trasparenze, mai definito (sezione 5.4) [APERTO].
- **RDA**: coefficiente annuale che determina i giga utilizzabili in Unione Europea [CERTO nella funzione, sigla non sciolta].
- **PO**: codice tecnico dell'offerta in Very Mobile [CERTO].

---

## 4. La Sintesi Contrattuale

### 4.1 Struttura

La Sintesi è composta da **sezioni**, ciascuna su un argomento (recesso, costi, servizi inclusi, durata, velocità, ecc.). Alcune sezioni contengono informazioni comuni a tutti i documenti WINDTRE, altre variano con l'offerta. Per Very Mobile la struttura è simile ma non identica [CERTO].

Il contenuto è organizzato in **tabelle** con una struttura a **padre e figlio**: il padre è la voce principale (es. "Costo mensile", "Costo di attivazione"), i figli sono le sotto-voci (es. "nuovi clienti", "portabilità"). Questa struttura deve essere mantenuta per consentire l'automazione [CERTO]. Dopo le tabelle seguono spesso **campi liberi** di testo (note, condizioni, sezioni strutturate), che per il Fisso CNS possono superare una pagina: il desiderata è **nessun limite di caratteri** [CERTO come desiderata, vedi anche REQ commento al numero 629 parole].

### 4.2 Fissi e variabili: tre significati diversi di "fisso"

La parola "fisso" viene usata con tre accezioni che è importante tenere separate, perché confonderle porta fuori strada.

1. **Frequenza di modifica** (REQ 1.1): campi *fissi* (cambiano mai o al massimo una volta l'anno) e campi *variabili* (cambiano ai canvas o per delibere).
2. **Concordato nel REQ** (sezione To-Be): "i soli elementi fissi nei documenti sono le etichette e i titoli; tutti gli altri campi sono variabili, seppur con frequenze diverse" [CERTO].
3. **Architettura dell'MVP** (BRIEF, DB, MAN): tabelle *fisse* (struttura e voci predefinite nel template, con valori da riempire) contro tabelle *dinamiche* (create dall'utente da frontend con nome, padri e figli) [PROBABILE: è il disegno attuale, non un requisito].

Il BRIEF afferma che nel Fisso "alcune tabelle sono fisse, uguali per tutti i mercati, e altre dinamiche", mentre nel Mobile "anche le tabelle fisse sono leggermente diverse". Confrontando le mappature del REQ l'affermazione è **in gran parte confermata ma con sfumature**: nel Fisso le tabelle "Servizio/i e apparecchiature" (4 padri, 4 figli), "Velocità" (1 padre, 2 figli) e "Durata, rinnovo e risoluzione" (4 padri, 5 figli) hanno la stessa struttura in tutti i segmenti, mentre "Prezzo" e "Costi" variano da segmento a segmento. Nel Mobile le differenze si estendono a quasi tutte le tabelle.

### 4.3 Tabelle per segmento (numerosità massime)

Tutti i numeri sono **massimi osservati oggi** su sintesi di esempio, non limiti da imporre. Il REQ chiede esplicitamente di **non blindare** la possibilità di aggiungere righe o voci in futuro [CERTO]. Il contenuto reale delle tabelle sta in immagini che non ho.

| Segmento | Tabelle mappate nel REQ (titolo: padri/figli) |
|---|---|
| Mobile GA e CB Consumer | 1 senza titolo: 3/3 · Descrizione Offerta: 5/5 · Velocità del servizio Internet e mezzi di ricorso: 2/4 · Prezzo: 5/6 · senza titolo: 1/5 · Servizi: 3/8 · Durata, rinnovo e risoluzione: 3/3 · Servizi Aggiuntivi: 10 padri con 2 figli ciascuno |
| Mobile GA Microbusiness | 1 senza titolo: 3/3 · Servizio/i e apparecchiature: 5/5 · Daily Pass: 1/1 · Velocità: 1/2 · Prezzo: 4/7 · Costo di attivazione servizio: 1/4 · senza titolo: 2/5 · Durata, rinnovo e risoluzione: 3/3 |
| Etnico Consumer | Prezzo: 5 padri + 6 righe · CDA: 1 padre + 4 righe · Servizi: 2 padri + 5 righe · Durata, rinnovo e risoluzione: 3 padri + riga a lato (elenco apparentemente incompleto) |
| Very Mobile | 1 senza titolo: 3/2 · Servizi e Apparecchiature: 6/6 · Velocità: 1/2 · Prezzo: 7/10 · Rinnovo e risoluzione: 3/3 |
| Fisso CB Consumer | 1 senza titolo: 3/3 · Servizio/i e apparecchiature: 4/4 · Velocità: 1/2 · Prezzo: 1/1 · Costi: 5/8 (con proposta di scorporare "Servizi a pagamento") · Durata: 4/5 · Funzioni per utenti con disabilità (campo libero) · Modifiche (campo libero) |
| Fisso CB Microbusiness (dichiarato valido anche per Fisso GA CNS) | 1 senza titolo: 3/3 · Servizio/i e apparecchiature: 4/4 · Velocità: 1/2 · Prezzo: 1/2 · Costi: 5/9 (in 3 tabelle) · Durata: 4/5 · Modifiche (campo libero) |
| Fisso GA/Cross Selling Microbusiness | 1 senza titolo: 3/3 + bollino · Servizio/i e apparecchiature: 4/4 · Velocità: 1/2 · Prezzo: 1/3 · Costi (accorpato con servizi inclusi): 4/10 · Servizi non inclusi: 1/4 · Durata: 4/5 |
| Fisso CNS CVM/Cross Selling | 1 senza titolo: 3/3 + bollino · Servizio/i e apparecchiature: 4/4 · Velocità: 1/2 · Prezzo: 1/1 · Costi (accorpato): 4/6 · Servizi non inclusi: 1/5 · Durata: 4/5 |

Altre osservazioni su queste tabelle:

- Il numero di padri e figli "è sempre da intendersi come massimo": non tutte le offerte li usano tutti [CERTO].
- Le note devono comparire **sotto la tabella a cui si riferiscono**, non in mezzo e non a piè di pagina [CERTO]. Sotto le tabelle devono poter esistere **note riferite a padri o figli e link** [CERTO].
- Se un padre o un figlio ha valore "ND" si scrive "Non applicabile"; se è vuoto, la riga **non deve comparire** nell'output [CERTO]. Non è ammesso lasciare righe vuote per motivi di accessibilità.
- Alcune tabelle possono avere i figli **affiancati** oppure **sotto**: entrambe le disposizioni devono essere possibili [CERTO].
- Si è proposto di dare un **titolo a tutte le tabelle** (alcune oggi non lo hanno) per facilitare automazione e riferimenti, ma l'ultima parola spetta all'area regolamentare [APERTO]. Sul titolo al singolare o plurale ("Prezzo" resta singolare, "Costi" plurale) c'è stata discussione e una scelta caso per caso.
- I titoli per gli stessi contenuti **non sono uniformi tra segmenti**: i servizi a pagamento sono "Servizi a pagamento" nel Fisso CB Consumer e "Servizi non inclusi" nel Fisso GA/CS; il Fisso CB Consumer scorpora i servizi dal "Costi", mentre il Fisso GA/CS li accorpa. Questo ha effetti diretti sulla modifica massiva (sezione 7).

### 4.4 Righe massime per sezione

Il REQ riporta un massimo di righe per sezione e per segmento (es. Mobile GA Consumer: Prezzo 12, Costi 5, Servizi 5; Mobile CB Consumer: Bundle 6, Prezzo 4, Costi 6, Servizi 15; Fisso: Prezzo 5, Costi 8 o 12, Servizi 14; Etnico: Prezzo 4, Costi 7, Servizi 10; Very Mobile: 3). Il dato è ambiguo: per alcuni segmenti compare un "totale" che non è la somma delle sezioni, e il Very Mobile ha un solo numero senza ripartizione. Inoltre le righe del paragrafo 1.2.1 e i padri/figli della mappatura (sezione 4.3) sono **metriche diverse che non si riconciliano** (es. Mobile GA Consumer: "Prezzo 12 righe" contro "Prezzo: 5 padri e 6 figli") [CONTRASTO/APERTO].

**Cosa dice il campione.** Il confronto con le Sintesi reali permette di sciogliere in parte il dubbio. Il "totale" del REQ sembra coincidere con il **numero di righe fisiche della tabella Prezzo**: nel Mobile GA Consumer la tabella Prezzo ha esattamente 12 righe (il REQ dice 12) e nel Mobile GA Microbusiness ne ha 11 (il REQ dice 11) [INFERENZA]. Per l'Etnico invece la tabella Prezzo reale ha 11 righe mentre il REQ riporta 4 per Prezzo e 10 di totale, quindi la lettura non regge per tutti i segmenti. Nel Fisso GA/CS Microbusiness la tabella Prezzo reale ha da 3 a 4 righe, coerente con il massimo di 5 del REQ. Contare le righe fisiche include le righe dei padri (che nelle tabelle Mobile compaiono come righe-intestazione senza valore), per cui "righe" e "padri più figli" non sono la stessa unità [APERTO].

### 4.5 I bollini

I bollini identificano la tecnologia di rete (fibra, mista, FWA, ecc.) e riguardano **solo la Sintesi, non la Trasparenza** [CERTO]. Regole:

- sono obbligatori, in alta risoluzione, e devono stare **accanto alla parola chiave della tecnologia**, non a fine frase;
- stessa dimensione dentro lo stesso documento e tra documenti diversi;
- colori secondo la delibera 106/25/CONS: **verde** (Pantone 361), **giallo** (Pantone 137), **rosso** (Pantone 192);
- testo alternativo obbligatorio per i lettori di schermo;
- l'associazione tecnologia → bollino può essere automatica (flag o dizionario);
- nel Fisso si elimina il **secondo** bollino della Fibra (quello nel testo libero), restano il **primo e il terzo**, posizionati nelle griglie;
- sono state sollevate perplessità sull'accessibilità di celle unificate con immagini: serve test con browser e lettori di schermo [APERTO].

La modifica della tecnologia di un'offerta comporta un cambio di bollino, e questo è uno dei casi in cui la modifica massiva è già stata esemplificata (sezione 7).

### 4.6 Accessibilità e vincoli del PDF

Il PDF della Sintesi deve essere **accessibile** (testo ricercabile, ordine di lettura, testo alternativo per le immagini). Oggi richiede un **controllo manuale a ogni modifica** [CERTO come stato attuale]. Il PDF destinato ad Adobe ha vincoli aggiuntivi:

- solo formato PDF, con alcuni caratteri non riconosciuti (altrimenti il file va in KO);
- dimensione massima **2 MB**;
- nome file massimo **160 caratteri** inclusa l'estensione;
- caratteri ammessi nel nome: punto, underscore, trattino; **vietati** `\ / : * ? " < > |` e gli spazi;
- Adobe **non accetta due file con lo stesso nome** [CERTO].

Non so se il sistema deve garantire o solo agevolare il rispetto di questi vincoli (validazione bloccante?) [APERTO].

### 4.7 Naming dei file

Il nome del file deve includere sempre il **nome dell'offerta, la tecnologia e il prezzo**, secondo quanto richiesto dalle vendite, più una parte **editabile dall'utente**, nel rispetto dei vincoli di lunghezza e caratteri [CERTO].

- **WINDTRE Fisso (GA, CNS, MB):** nome commerciale + tecnologia + prezzo + un **elemento diversificante** (data oppure canale: pdv, tls, online, web), necessario perché Adobe rifiuta nomi uguali.
- **Very Mobile:** struttura desiderata `data creazione + prezzo + GIGA + costo attivazione + nome PO`, separati da underscore (`yyyymmdd_x.xx_xxGB_x.xx_POXXXXXX`); il **PO deve essere nel nome** perché è l'unico identificativo tecnico. Si accetta anche che l'utente digiti il nome in autonomia, ma l'aggiunta automatica di un suffisso data-ora-minuti è considerata ridondante [CERTO].
- Sia per Sintesi che per Trasparenza serve un **campo in interfaccia** per determinare il nome file [CERTO].
- Il naming deve essere **coerente tra versione chiusa e versione nuova** di una stessa offerta [CERTO].

Il MAN descrive un naming diverso (suffisso `_NUOVA`, codice AGCOM nel nome della Sintesi): vedi sezione 12.

**Cosa dice il campione.** I nomi file reali non seguono né le regole del REQ né quelle di Adobe. Esempi (abbreviati): `Internet100-Professional-FTTC31,99conv25,99-011026.docx`, `Internet100-FTTCExtra-CambioTecnologia-attivazione-1,99€x24mesi-032026.docx`, `AbsoluteInternetProfessional5G-FWA28,99-pdv220626.docx`, `UDG_Sintesi_Contrattuale-GO_220_XXS_5G_Easy_Pay.docx`, `20240708_5,99_5G_150GB_4,99_PO_Very_RicAut_Mand_010425_GA.docx`, `241125_5G_13,99_GS1000_0_GA_PO_Very_171124_DO_A_GA.docx`. Si osserva quanto segue.

- **Caratteri fuori elenco:** molti nomi contengono la **virgola** (nei prezzi) e uno contiene il simbolo **€**. Né la virgola né € sono tra i caratteri ammessi da Adobe (solo punto, underscore e trattino). Non so se questi nomi Word siano poi rinominati prima del caricamento del PDF [APERTO].
- **Formati di data diversi:** `011026` (giorno-mese-anno a due cifre), `072026` e `032026` (mese-anno), `20240708` (anno-mese-giorno), `241125` (anno-mese-giorno a due cifre), `pdv220626` (canale più data). Il canale (`pdv`) compare in un solo caso.
- **Prezzo nel nome:** nel Fisso compare il prezzo di riferimento e, quando c'è una convergenza, entrambi i prezzi (`31,99conv25,99`). In Very compare il prezzo ma l'ordine degli elementi cambia da un file all'altro (`5,99_5G_150GB_4,99` contro `5G_13,99_GS1000_0`).
- **Il "PO" in Very:** il REQ vuole il codice PO come ultimo elemento (`POXXXXXX`), ma nei file reali "PO" compare come testo (`PO_Very_RicAut_Mand_010425_GA`) seguito da altre sigle: non è chiaro quale parte sia il codice identificativo e quale sia testo libero [APERTO].
- **Data nel nome contro data nel contenuto:** il file Very `20240708_…` riporta nel documento "disponibile dall'08/07/25" e la sua Trasparenza ha data di inizio 2025-07-08, quindi l'anno nel nome (2024) non coincide con quello nei contenuti (2025). Anche il file Fisso CB `20260724_INTERNET 100 Professional_CB` ha inizio sottoscrivibilità 2023-10-19: la data nel nome sembra la data di produzione del file, non quella di inizio [INFERENZA]. Alcuni nomi contengono inoltre **spazi** (es. `20260724_INTERNET 100 Professional_CB.xlsx`), anch'essi vietati da Adobe.

### 4.8 Cosa mostrano le Sintesi reali

Le venti Sintesi del campione permettono di verificare sul campo molte delle affermazioni dei requisiti. In sintesi: la struttura generale è riconoscibile e coerente con il REQ, ma i documenti reali sono **meno uniformi** di quanto i requisiti lascino intendere, e **molte informazioni che oggi dovrebbero essere "campi" vivono in realtà dentro testo narrativo**. Questo secondo punto pesa molto sulle modifiche massive (sezione 7.7).

#### Tre forme fisiche dello stesso schema padre-figlio

Lo schema padre-figlio descritto nel REQ compare nei documenti reali in tre forme diverse, a seconda del segmento.

- **Fisso** (GA/CS Microbusiness, CB Microbusiness, CB Consumer): tabelle a **una colonna** in cui etichetta e valore sono righe alternate (es. riga "Traffico internet", riga seguente "Illimitato"). Otto tabelle per documento.
- **Mobile** (GA e CB Consumer, GA Microbusiness, Etnico): tabelle a **due colonne** (etichetta e valore), con righe-intestazione dei padri senza valore (es. "Costo mensile (salvo eventuali promozioni)" seguita da "Già clienti | …"). Da sette a dieci tabelle per documento.
- **Very Mobile**: tabelle a **tre colonne** (padre, figlio, valore) in cui l'etichetta del padre è **ripetuta in ogni riga** (es. "Costo ricorsivo (al lordo di eventuali promozioni) | Già clienti | ND"). Sette tabelle per documento.

Le prime due forme corrispondono ai due layout descritti nel MAN (due colonne affiancate; una colonna incolonnata). La forma a tre colonne di Very **non è descritta nel MAN** [APERTO].

#### Il numero e il tipo di tabelle variano anche dentro lo stesso segmento

Nel Mobile CB Consumer la Sintesi "MIA 100 Easy Pay" ha dieci tabelle: una descrizione dell'offerta, **tre tabelle "Descrizione Opzione …"** (Reload Forever, Più Sicuri Mobile PRO, Più Sicuri Mobile) e **tre tabelle "Prezzi"**, una per l'offerta e una per ciascuna opzione di sicurezza. La Sintesi "MiaCycUnlimited100" ne ha nove, perché non ha la descrizione di Reload Forever (opzione legata a Easy Pay). Si tratta quindi di tabelle che si **ripetono per ogni opzione collegata all'offerta**, in numero variabile. Nel Fisso la tabella "Costi" compare **due o tre volte** con contenuti diversi. Nel Mobile GA Consumer e nell'Etnico gli stessi servizi aggiuntivi (Reload Forever, Più Sicuri Mobile) sono invece blocchi di titolo e testo libero, non tabelle. Il REQ mappa per Mobile GA e CB Consumer una tabella "Servizi Aggiuntivi" da 10 padri con 2 figli ciascuno: nei campioni **la stessa informazione ha forme diverse** (tabella, blocco di testo, assente). La tabella "Daily Pass" prevista dal REQ per il Mobile GA Microbusiness non compare nei due campioni di quel segmento: è presente solo in alcune offerte.

#### I titoli reali non coincidono sempre con il REQ

- Il REQ tratta insieme "Mobile GA e CB Consumer" con una seconda tabella intitolata "Descrizione Offerta". Nei campioni la Sintesi GA ha la tabella intitolata **"Servizio/i e apparecchiature"**, mentre la Sintesi CB (MIA) ha **"Descrizione Offerta"**. I due segmenti, accorpati nel REQ, hanno quindi titoli e struttura diversi: questo conferma l'osservazione iniziale per cui nel Mobile "anche le tabelle fisse sono leggermente diverse".
- La tabella dei prezzi è "Prezzo" al singolare in quasi tutti i documenti, ma **"Prezzi"** al plurale (ripetuta più volte) nel Mobile CB.
- Il REQ propone di dare il titolo "Servizi non inclusi" (Fisso GA/CS) o "Servizi a pagamento" (Fisso CB Consumer) alla tabella dei servizi a pagamento. Nelle Sintesi Fisso del campione, **modificate a fine settembre 2026**, le tre tabelle di costo restano tutte intitolate "Costi" e nessuna ha il nuovo titolo: la proposta sembra non ancora applicata [INFERENZA].
- La policy di roaming ("Politica di utilizzo corretto in roaming EEA") compare nel Fisso CB Consumer dentro la sezione Costi, e non compare nelle Sintesi Fisso Microbusiness.

#### "ND", righe vuote e segnaposto dimenticati

Il REQ stabilisce che "ND" diventa "Non applicabile" e che i campi vuoti non producano righe. Le Sintesi reali oggi si comportano diversamente:

- Il **Mobile** e **Very** mostrano "ND" letterale: Very ne ha **18 celle** per documento (ad esempio "Apparecchiature | ND", "Durata minima del contratto | ND | ND"), il Mobile GA/Etnico ne ha da 3 a 5. Il Fisso invece scrive "Non applicabile" (es. "Condizioni di sblocco dell'apparato: Non applicabile"). L'applicazione della regola del REQ cambierebbe quindi il testo visibile all'utente finale in Mobile e Very.
- Compare anche il trattino "-" come valore assente (es. "Già clienti | -").
- Resta da stabilire **quando un valore è "ND" e quando è "vuoto"**: nei documenti oggi sono scelte manuali dell'autore, e le due condizioni producono output opposti (testo "Non applicabile" contro riga omessa) [APERTO].
- **Sei Sintesi su venti contengono segnaposto non sostituiti**: "XX" e "XXX" (es. "Costo mensile promozionale per XX mesi | XXX euro al mese"), una variabile visibile come testo (`$Nome POPZ$`), e testi come "link al sito Roaming Europa" al posto del vero collegamento. Questo mostra che il processo manuale attuale produce residui e che il controllo è affidato alla persona.

#### Testi ripetuti e "deriva" tra documenti

Molti blocchi di testo sono ripetuti in decine di documenti. Nel campione di 20 Sintesi:

- la frase introduttiva ("La presente sintesi contrattuale fornisce gli elementi principali…") e la frase sulla validità ("La sintesi contrattuale fornita è valida fino alla chiusura in sottoscrivibilità…") sono identiche in **18 documenti**, tutti i WINDTRE (Very ha un testo proprio);
- nel Fisso Microbusiness e Consumer ci sono blocchi identici in **8 o 10 documenti** (ad esempio i testi su recesso, rinnovo, servizi inclusi, "Tutti i prezzi sono da intendersi IVA esclusa…");
- la sezione **"Modifiche"** (variazioni unilaterali) esiste in **8 varianti diverse su 18 documenti**; il testo "Agevolazione Economica Utenti Disabili" in 4 varianti su 10 documenti; il testo su Professional Cloud in 3 varianti su 10; il testo sul recesso del Fisso in 3 varianti su 10. Anche le Sintesi "gemelle" (versioni FTTC e FTTC Extra della stessa offerta) differiscono in alcuni casi per qualche riga di testo comune, ad esempio nella sezione "Modifiche".

Questi numeri mostrano due cose insieme: ci sono moltissimi **candidati a gestione centralizzata** (testi comuni) e, allo stesso tempo, i testi "comuni" **non sono davvero identici** tra loro. Non so se le varianti siano volute (differenze di segmento o di mercato) o siano il frutto della propagazione manuale, quindi non è possibile dire quali debbano convergere [APERTO]. Un esempio che il campione rende evidente è l'**IVA**: le Sintesi Fisso Consumer dicono "Tutti i prezzi sono da intendersi IVA inclusa", le Fisso Microbusiness "IVA esclusa", e le Trasparenze Mobile Microbusiness riportano "Prezzi IVA esclusa". Il regime IVA dipende quindi dal segmento (Consumer incluso, Microbusiness escluso), il che chiarisce l'apparente contrasto segnalato nella v0.1 (vedi sezione 12).

#### Valori incorporati nel testo e relazioni aritmetiche

Questo è il punto che incide di più sul problema delle azioni massive. Le Sintesi reali mostrano che **lo stesso valore compare in più punti dello stesso documento, spesso dentro frasi**.

- Nella Sintesi Fisso GA/CS Microbusiness "Professional" il prezzo 31,99 compare in tre blocchi (una cella della tabella Prezzo e due paragrafi narrativi), la rata del modem 5,99 in tre blocchi, il costo di attivazione 1,99 in due. Nella Sintesi Etnico "Unlimited Full" il costo di attivazione 49,99 e la rata 2,08 compaiono in tre blocchi ciascuno. A questi si aggiungono il **nome del file** e, nella Trasparenza, sia la cella strutturata sia la nota testuale.
- Il prezzo totale è spesso **scomposto in componenti nel testo**: "31,99 euro è composto, per i primi 48 mesi, da: 21 euro di canone del servizio, 5 euro di chiamate illimitate e 5,99 euro di rata del modem". Le somme tornano in tutti i casi che ho controllato (21 + 5 + 5,99 = 31,99; 15 + 5 + 5,99 = 25,99; 19 + 9,99 + 3 = 31,99; 24 + 5,99 = 29,99; 30 + 5 + 5,99 = 40,99). Esiste dunque una **relazione aritmetica tra campi diversi** che oggi è mantenuta a mano: cambiare un componente impone di cambiare il totale e le frasi che li citano.
- **RDA:** il coefficiente compare come numero dentro la cella "Politica di utilizzo corretto in roaming EEA" ("Roaming Data Allowance 7,5 Gigabyte da utilizzare in UE…"), non come campo a sé. I valori osservati nel Mobile Consumer sono 7,5 GB (canone 4,99), 14,9 GB (canone 9,99) e 29,8 GB (canone 19,99), cioè circa **1,5 GB per ogni euro di canone** [INFERENZA]; per il Mobile Microbusiness "Professional Country" il valore è 25 GB, con un rapporto diverso rispetto al canone (12,99 euro IVA esclusa). Nel Fisso e in Very la stessa informazione è soltanto un collegamento ("clicca qui"). Lo stesso concetto ha quindi **due rappresentazioni** nei documenti: numero dentro un testo (Mobile WINDTRE) e semplice collegamento (Fisso e Very).
- **Convergenza mobile–fisso e luce&gas:** compare in forme diverse. In Mobile come paragrafo nella sezione Prezzo ("Si ricorda che, se la SIM mobile è abbinata all'Offerta fissa…"), in Etnico come blocco finale "CONVERGENZA MOBILE – LUCE&GAS" (in due varianti di impaginazione), nel Fisso come riga di prezzo ("Per clienti con utenza mobile WINDTRE Professional abbinata | 25,99 euro"). C'è anche un **riferimento incrociato tra segmenti**: la Sintesi Mobile Microbusiness "Professional Country" cita un canone fisso convergente di **24,99 euro**, mentre la Sintesi Fisso Microbusiness "Professional" riporta **25,99 euro** per i clienti con quel mobile abbinato. Le due Sintesi hanno date di ultima modifica diverse (giugno e settembre 2026), per cui è plausibile una deriva da aggiornamento non propagato [PROBABILE].

#### Un documento può contenere più prezzi; lo stesso nome può indicare offerte diverse

- Le Sintesi Fisso GA/CS Microbusiness contengono **più punti prezzo nello stesso documento** ("Per nuovi clienti 31,99", "Per clienti con utenza mobile abbinata 25,99", "Seconda linea +10 euro") e il nome file riporta entrambi i prezzi (`31,99conv25,99`). Nell'offerta FWA compare anche una nota con un terzo prezzo condizionato (22,99 euro per i primi 12 mesi in caso di più profili tecnologici attivabili). Una Sintesi corrisponde quindi a una **famiglia di punti prezzo**, mentre nel REQ la Trasparenza è per punto prezzo.
- Le due Sintesi Fisso CB Consumer del campione sono **identiche tranne per il costo di attivazione** (1,99 euro per 24 mesi contro 2,00 euro per 12 mesi): il nome file porta questa differenza come elemento diversificante.
- Le Sintesi "FTTC" e "FTTC Extra" dello stesso prodotto sono, nei campioni, **identiche o quasi nel testo (differenze di poche righe) e usano la stessa immagine di bollino** (l'impronta del file immagine è identica in ogni coppia): la differenza esiste nel nome file e nella Trasparenza (la versione "NGA"), ma non nel contenuto del documento [APERTO].
- Il **nome commerciale non identifica un'offerta**: "INTERNET 100 Professional" compare nella Sintesi Fisso CB Microbusiness con un canone di 29,99 euro e nella Trasparenza Fisso CB Microbusiness con 40,99 euro (34,99 per i primi 48 mesi nella variante senza modem), con date di inizio diverse. Allo stesso modo la Sintesi "INTERNET 100 Full Professional" (40,99) e la Trasparenza "ABSOLUTE 100 Full Professional" (35,99) hanno nomi e prezzi diversi. Non è chiaro se si tratti di offerte distinte o della stessa offerta documentata in modo non allineato [APERTO].

#### Intestazione e date

L'intestazione cambia tra mercati: Mobile e Etnico usano "Nome Offerta / Data / Validità", il Fisso usa "Nome Offerta / Disponibilità offerta / Offerta valida fino al", Very usa il logo con il nome e la frase "Sintesi contrattuale disponibile dal gg/mm/aa". In tutte le Sintesi WINDTRE del campione il campo "Validità" (o "Offerta valida fino al") contiene **la frase fissa** "valida fino alla chiusura in sottoscrivibilità" e **non una data di fine**. Nella Sintesi, quindi, la data di fine validità non compare: al contrario la Trasparenza la contiene. Questo è coerente con quanto emerso dalle call (la validità della Sintesi non coincide con quella della Trasparenza) e suggerisce che il concetto di "data di fine" sia oggi proprio solo della Trasparenza [PROBABILE]. I formati di data sono inconsistenti (`6-10-2025`, `1-01-2025`, `19/01/2026`, `01-10-2026`). In un caso (MIA 100) la data è vuota e in un altro la data condivide la cella con un'immagine.

#### Bollini, testo alternativo e metadati

- Il **testo alternativo** è presente e sensato soltanto nelle sei Sintesi Fisso GA/CS Microbusiness (es. "Bollino Fibra FTTC misto Rame", "Bollino Fibra FTTC: misto Fibra Radio"). Sette documenti (Mobile e Etnico) hanno il testo alternativo **generato automaticamente da Word** ("Immagine che contiene testo, Carattere, Elementi grafici, simbolo – Il contenuto generato dall'IA potrebbe non essere corretto"), che non è un testo alternativo valido. Gli altri sette (Fisso CB Consumer e Microbusiness, Very, Mobile Microbusiness Data) **non hanno alcun testo alternativo**. Il requisito di accessibilità è quindi oggi rispettato solo in parte.
- Il testo alternativo del bollino FWA riporta la dicitura "FTTC" ("Bollino Fibra FTTC: misto Fibra Radio") pur riferendosi a una tecnologia FWA: probabile residuo di copia [INFERENZA].
- Le immagini dei bollini sono file molto piccoli (da circa 1 a 5 KB), il che non fa pensare a una "alta risoluzione" [INFERENZA].
- **Nessun documento Word del campione ha il titolo del documento** nelle proprietà, mentre il MAN dichiara un output PDF/UA, che lo richiede.
- Nel campione i bollini (immagini) compaiono inoltre fuori dalla Tabella 1, ad esempio dentro la cella "Bundle" del Mobile (verosimilmente il logo 5G) e in paragrafi di testo libero, e non solo accanto al nome della tecnologia come nel MAN [INFERENZA: non ho visto le immagini renderizzate].

#### Very Mobile: un formato a parte

Le Sintesi Very hanno sette tabelle a tre colonne, nessun blocco "ConciliaWeb", sezioni proprie (VoLTE, Very Protetti, Protezione minori, "Funzioni per gli utenti finali con disabilità visive e uditive") e un'intestazione con logo e piè di pagina differenti. Non contengono il codice PO nel testo (è solo nel nome file). Il formato è effettivamente "simile ma non identico" a WINDTRE, come dichiarato dal REQ, ma la differenza è più strutturale di quanto il REQ suggerisca (tre colonne con padre ripetuto, 18 celle ND).

---

## 5. La Trasparenza Tariffaria e il codice AGCOM

### 5.1 Cos'è e come si pubblica

È un Excel con campi e valori ammissibili imposti dal Vademecum. Viene prodotto in Excel per AGCOM e in PDF per i siti (dove il PDF segue anche le regole di Adobe) [CERTO]. In MAIL2 si dice che è stata fatta una mappatura dei campi collegati e dei valori ammissibili sul file della Trasparenza, con i dubbi evidenziati in giallo, **in attesa di risposta degli utenti** [APERTO].

### 5.2 Il codice AGCOM

Per ogni trasparenza AGCOM assegna un **codice univoco**, **entro 10 giorni dal caricamento** [CERTO]. Fino all'arrivo del codice il campo vale "Nuova". Sul formato ci sono tre versioni diverse (sezione 12): "codice alfanumerico" (REQ), controllo di lunghezza 10 o 36 caratteri (DB), **UUID secondo RFC 4122** (dal Vademecum, citato in MAIL2, con esempio di 36 caratteri). Il MAN usa esempi come `COD1234567` che non sono UUID.

### 5.3 Una trasparenza per offerta? No: regole diverse per segmento

- **Mobile GA Consumer, Fisso GA/CB Consumer, Fisso Microbusiness, Very Mobile, Etnico:** una trasparenza distinta, con il proprio codice, per **ogni combinazione offerta–punto prezzo** [CERTO].
- **Mobile CB Consumer:** produce poche trasparenze raggruppando le offerte per tipologia e riportando **solo il punto prezzo più alto**, con un unico codice. Una modifica sul punto prezzo più alto chiude la trasparenza precedente e ne apre una nuova; modifiche su punti inferiori non richiedono aggiornamenti (REQ 1.2.2 e MAIL2) [PROBABILE].
- Più avanti nel REQ si legge che il Mobile CB Consumer "si allinea al processo degli altri": si producono tutti gli output per ogni punto prezzo e poi si sceglie il documento col punto prezzo più alto. È incompatibile col punto precedente, oppure descrive una scelta lato utente su un output comunque generato per tutti [CONTRASTO].

Conseguenza descrittiva: l'unità "offerta" non coincide con l'unità "trasparenza", e nemmeno con l'unità "Sintesi" (che ha nome, tecnologia e prezzo propri). Il documento non definisce mai con precisione quale sia l'entità minima da gestire (sezione 13, domanda 1).

### 5.4 Cosa conferma il campione sul codice e sulla granularità

Il campione dà una risposta concreta ad almeno due dubbi del REQ.

- **Formato del codice:** nelle tre Trasparenze del campione che hanno un codice, il valore è un **UUID di 36 caratteri** in minuscolo (es. `eab9995b-2cd6-4519-9355-1040f725774c`). Non compare nessun codice da 10 caratteri e nessun valore tipo `COD1234567`. Il formato UUID è quindi confermato dai dati reali [CERTO nel campione]; gli esempi del MAN non corrispondono a un codice AGCOM reale.
- **Dove sta il codice:** nella Trasparenza il codice è scritto **nella stessa cella "Stato dell'offerta"**, al posto del valore "Nuova". Questo conferma la lettura del REQ (e non quella del BRIEF, secondo cui il codice sarebbe un campo separato del form) e chiarisce che "APERTA" non è un valore che compare nel file AGCOM [CERTO nel campione].
- **Granularità Mobile CB:** la Trasparenza Mobile CB del campione si chiama "MIA 250 Easy Pay" e riporta nelle note che "la composizione sopra indicata è quella massima per prezzo e per GIGA", mentre la Sintesi del campione è "MIA 100 Easy Pay". Una Trasparenza copre quindi più Sintesi e rappresenta la composizione massima: coerente con la regola "solo punto prezzo più alto" del REQ 1.2.2 [PROBABILE].
- **Granularità Etnico:** le due Trasparenze Etnico del campione ("Call Your Country Flash+ 200 EP" e "CYC Flash+ 200 No Grace Period") sono **due documenti distinti con due codici diversi**, che differiscono per target (solo portabilità, oppure nativi e portabilità), costo di attivazione e prezzo mensile. Coerente con la regola "una per offerta–punto prezzo" [PROBABILE].

### 5.5 La scheda Excel reale: struttura, convenzioni e qualità dei dati

#### Una griglia fissa, più una zona di note libere

Le undici Trasparenze leggibili del campione hanno la stessa struttura: una griglia di circa **45 righe con etichette fisse**, poi da una a una decina di righe di **note libere** (il foglio arriva a 47–57 righe, a seconda delle note). La griglia contiene, in ordine: operatore, stato, data di inizio e di fine sottoscrivibilità, territorio, nome commerciale, tipologia (piano base oppure opzione/bundle), piani base compatibili, pagina web di pubblicazione, mercato, modalità di pagamento, target clientela, tecnologia di rete, velocità (download e upload), prezzo di attivazione per target (già clienti, nuovi nativi, nuovi in portabilità) in due colonne ("a listino" e "in promozione"), durata promozione, costo di disattivazione, durata minima, costo di recesso, prezzo (addebito flat, poi addebito a consumo con scatto alla risposta, SMS, internet) in due colonne ("a regime" e "in promozione"), e infine i servizi inclusi (fonia da fisso, fonia da mobile on-net e off-net, SMS, internet a volume e a tempo).

Alcune corrispondenze con il modello dati dell'MVP sono dirette: il prezzo di attivazione per tre tipi di target del foglio coincide con la tabella dei costi di attivazione per tipo di cliente del DB, e il nome commerciale, la tecnologia, le date, lo stato e il codice sono campi dell'offerta. Altre parti della griglia non hanno corrispondenza nel DB: le **colonne "in promozione"** (prezzi e attivazione promozionali), la **durata della promozione**, il **costo di recesso**, il **tipo di offerta** (piano base o opzione), i **piani compatibili**, il **territorio**, e l'intero blocco **servizi inclusi** (minuti, SMS, GB) [INFERENZA sulla copertura del DB, basata sulle sole tabelle descritte nel documento].

#### Stesso modello, ma non esattamente la stessa griglia

Le Trasparenze Very hanno la **stessa griglia spostata di una colonna** (le etichette sono nelle colonne B-C-D invece di A-B-C) e il foglio ha un nome diverso ("TRASPARENZA" contro "TLC" per quelle WINDTRE recenti; "MIA EasyPay" e "Table 1" in due file Mobile). Un generatore dovrebbe quindi rispettare due posizioni diverse, oppure è la regola AGCOM a tollerarle [APERTO].

#### Gli stati, nella pratica

Su undici Trasparenze leggibili, **otto hanno stato "Nuova"** e **tre hanno un codice**. **Nessuna ha "Chiusa"**. Tre elementi rendono il quadro più sfumato:

- Alcune Trasparenze con stato "Nuova" sono **molto vecchie**: Professional Data 10 GIGA (inizio 2021), Professional Country (2022), INTERNET 100 Professional Fisso CB Microbusiness (2023). Per questi segmenti "Nuova" è quindi uno **stato che dura anni e non viene mai sostituito dal codice**, il che conferma i commenti di Mobile e Fisso Microbusiness nel REQ ("l'unico stato usato è Nuova") [CERTO nel campione].
- Le due Trasparenze Etnico "Flash+ 200" hanno una **data di fine sottoscrivibilità nel passato** (1 febbraio 2026), ma lo stato resta il codice, non "Chiusa", e il campione è etichettato come "sottoscrivibili". O la chiusura non è stata registrata nel file, oppure la data di fine e lo stato "Chiusa" si muovono in modo indipendente [APERTO].
- Il nome file riporta una data (es. `20260724_…`) che non coincide con la data di inizio sottoscrivibilità nel foglio (es. 2023-10-19): non è un dato dell'offerta ma probabilmente della produzione del file.

#### Convenzioni e disomogeneità dei valori

Le celle non contengono sempre un solo valore tipizzato:

- Valori composti con **separatore "/"** e significato posizionale spiegato nelle note: quattro valori in "Scatto alla risposta" (fisso-fisso, fisso-mobile, mobile-mobile, mobile-fisso), due valori in velocità e attivazione per le offerte convergenti (primo fisso, secondo mobile), e forme come "0,0/30,00" per il costo di recesso o "-/-" per la disattivazione.
- Il "-" indica assenza di valore, diverso da "ND" e dal vuoto.
- Formati numerici misti: "39,99", "39.99", "8.99", "2000" (in Mbps) per la stessa tipologia di campo. Le **unità non coincidono tra documenti**: la velocità è "2000" Mbps nella Trasparenza e "2,0 Gbps" nella Sintesi dello stesso mercato.
- Date a volte come vere date, a volte come testo ("20/09/2021").
- Vocabolari non controllati: tecnologia ("LTE", "5G", "4.5 G", "FTTC", " FTTC" con spazio, "3G,4G,5G,LTE,LTE ADVANCE"), tipo di offerta ("Piano base" e "Piano Base"), piani compatibili ("Nessuno", "Nessuna", "Tutti", "-"), target clientela (liste libere, con differenze di maiuscole come "Già Clienti Fisso" e "Già clienti fisso" in due file gemelli), mercato (con spazi e ritorni a capo finali), indirizzo di pubblicazione (http o https, con o senza barra finale, percorsi diversi). Maiuscole e minuscole variano anche nei valori ("illimitato", "Illimitato", "illimitati").

Non conosco i "valori ammissibili" mappati nello "Schema Vademecum.xlsx", quindi non posso dire se queste variazioni siano ammesse da AGCOM o errori che il sistema dovrebbe impedire [APERTO].

#### Le note: una parte fissa e una variabile, davvero

Le righe di nota contengono, in tutte le Trasparenze WINDTRE, un **blocco finale ricorrente** (numeri di emergenza e localizzazione del chiamante, ConciliaWeb, Trasparenza Tecnica, assistenza post-vendita, recapiti dell'impresa, a volte informazioni per utenti con disabilità e prescrizione) con piccole differenze di forma tra file, e un **blocco iniziale specifico dell'offerta** (rateizzazione dell'attivazione, fatturazione, condizioni di utilizzo, elenco paesi). Nelle Trasparenze Very le note sono brevi e specifiche (es. elenco degli operatori di provenienza per la portabilità, rimando all'Allegato 5 del Codice delle comunicazioni elettroniche). Questo conferma nei fatti che il campo note ha una parte stabile e una variabile, come richiesto dagli utenti del marketing Fisso, anche se la decisione registrata nel REQ è di avere una sola nota nel DB [CONTRASTO con il REQ già segnalato, sezione 12].

#### Informazioni duplicate tra Sintesi e Trasparenza, e incongruenze

Gli stessi dati (prezzo, costo di attivazione, durata, velocità, tecnologia) compaiono sia nella Sintesi sia nella Trasparenza, spesso in forma diversa (cella strutturata contro frase). In un caso la **Trasparenza Very** "Very 5,99 per nuovi numeri" riporta come target "Nuovi clienti in portabilità", ma i prezzi di attivazione sono compilati sulla riga dei "nuovi clienti nativi", e la Sintesi corrispondente parla di nativi: verosimile errore di compilazione manuale [PROBABILE]. Nella Trasparenza Etnico "Flash+ 200 EP" il prezzo di attivazione è "49.99" nella cella e "49,99" nella nota. La Trasparenza Mobile CB "MIA 250 Easy Pay" (inizio 2023) dichiara una velocità di 1600 Mbps in download, mentre la Sintesi MIA del campione (modificata nel 2026) dichiara 2,0 Gbps: il documento "con codice" può quindi restare in linea per anni con valori diversi da quelli della Sintesi attuale, in linea con l'idea che i due documenti abbiano cicli di vita non allineati [PROBABILE].

---

## 6. Il ciclo di vita dell'offerta

### 6.1 Cosa dice il requisito

Il REQ definisce tre stati, descritti sul file Excel della Trasparenza e **dichiarati confermati**:

- **NUOVA:** all'arrivo di una nuova offerta, l'utente scrive "Nuova" nel campo "Stato dell'offerta" e la data di inizio nel campo "Data di inizio sottoscrivibilità dell'offerta".
- **APERTA:** quando arriva il codice AGCOM, l'utente lo inserisce **nel campo "Stato dell'offerta"** (quindi nell'Excel il valore del campo diventa il codice). Viene prodotto un Excel e il suo PDF.
- **CHIUSA:** quando l'offerta non è più **sottoscrivibile**, l'utente scrive "Chiusa" e la data di fine. Si producono un nuovo Excel e un nuovo PDF che **non sovrascrivono** quelli di APERTA.

Nel BRIEF la dinamica è raccontata in modo leggermente diverso: la creazione dà lo stato NUOVA, il codice AGCOM viene inserito nel form dell'offerta e questo causa il passaggio **automatico** ad APERTA; CHIUSA arriva "quando l'offerta non sarà più sovrascrivibile". Le differenze sono due e contano (sezione 12): dove sta il codice (campo di stato nell'Excel o campo dedicato nel form) e che cosa significa CHIUSA (non più sottoscrivibile o non più modificabile).

### 6.2 I commenti degli utenti: lo stato APERTA non è vissuto allo stesso modo

I commenti a margine del REQ mostrano che i segmenti **usano gli stati in modo diverso**:

- Mobile GA Consumer: non si riconosce nella descrizione di APERTA, perché AGCOM pubblica il file già col codice dentro l'Excel e non c'è altra operatività lato WINDTRE.
- Mobile CB Consumer: descrive tre fasi (Nuova al lancio, codice alfanumerico quando l'offerta è in corso, Chiusa con data di chiusura) e interpreta "aperta" come la fase intermedia.
- Very Mobile: valgono **solo Nuova e Chiusa**.
- Fisso CB Microbusiness e Mobile GA Microbusiness: l'**unico stato usato finora è Nuova**.
- Fisso (altro commento): confermato.
- Dopo un confronto fuori documento si precisa che APERTA serve per tracciare le **modifiche su trasparenze già in linea**, scenario comune nel CB.

Il REQ chiude dicendo che "gli stati sono stati confermati". Ma la pratica descritta dagli utenti suggerisce che gli stati **non valgono ugualmente per tutti**, e non è chiaro se per alcuni segmenti si passi direttamente da Nuova a Chiusa [APERTO]. Va anche tenuto presente che "APERTA" non compare mai nell'Excel di AGCOM: lì il campo di stato contiene "Nuova", un codice, o "Chiusa". APERTA sembra quindi uno stato **interno al nostro sistema** [INFERENZA].

### 6.3 Quando si può modificare un'offerta

Qui la conoscenza è la più fragile. Le risposte raccolte in MAIL2 sono le seguenti.

| Domanda | Risposta ricevuta | Affidabilità |
|---|---|---|
| La modifica massiva riguarda anche le offerte NUOVE e APERTE? E le CHIUSE? | "Mi aspetto tutte le offerte **non chiuse**; una volta chiusa non deve essere più editabile." | [PROBABILE] — "mi aspetto" non è una decisione |
| Una offerta NUOVA è modificabile in attesa del codice? | "Non porre troppi vincoli in questa fase; se abbiamo dubbi smarchiamoli con gli utenti." | [APERTO] — non è una risposta |
| Dopo l'inserimento del codice l'offerta resta modificabile? E il codice stesso? | "Direi di sì", perché Sintesi e Trasparenza hanno cicli di vita non allineati: molti aggiornamenti restano interni e toccano solo la Sintesi. | [PROBABILE] |
| Il codice può contenere refusi? Serve validazione? | Il Vademecum dice che è un UUID (RFC 4122), quindi serve un controllo sintattico. | [PROBABILE] — contraddice altri documenti sul formato |
| Si possono generare Sintesi e Trasparenze per ogni stato? | "Una volta che un'offerta viene chiusa, mi aspetto che non sia più modificabile." | [APERTO] — non risponde alla domanda posta |

### 6.4 Tensioni interne al modello di stati

Mettendo insieme le fonti emergono diversi punti che non si incastrano.

1. **Modifica in-place o nuova versione?** Il REQ dice che quando un'offerta si chiude "per la nuova offerta si genera un nuovo record con stato 'nuova'", e che il naming deve essere coerente tra "versione chiusa e nuova". Nel Mobile CB, la modifica del punto prezzo più alto chiude la trasparenza e ne apre un'altra. Inoltre è richiesta la **duplicazione** (massiva o su selezione) dei documenti destinati a essere modificati. Tutto questo fa pensare a un modello in cui modificare vuol dire **creare una nuova offerta che sostituisce la precedente** [INFERENZA]. Le risposte in MAIL2 vanno invece verso la **modifica sul posto anche dopo il codice**. I due modelli non sono equivalenti e il materiale non sceglie.
2. **Cosa vuol dire CHIUSA.** Nel REQ "chiusa" significa non più **sottoscrivibile** (è un fatto commerciale), mentre in MAIL2 e nel BRIEF diventa non più **modificabile** (è un blocco del sistema). Sono due concetti diversi. Un'offerta non più sottoscrivibile può avere clienti ancora attivi, e le modifiche regolamentari (RDA, convergenza, bollini) potrebbero doverla comunque raggiungere [APERTO].
3. **Come si arriva a CHIUSA.** Chiudere significa inserire stato e data di fine e produrre nuovi file. Se la chiusa non è modificabile, la chiusura è l'ultima modifica consentita. Cosa accade a una chiusura sbagliata (riapertura)? Nessun documento ne parla [APERTO].
4. **I "quattro file".** Gli utenti vogliono entrambi i file (Excel e PDF) sia prima che dopo il codice AGCOM, senza sovrascrivere: "quattro file" [CERTO come richiesta]. Ma con la chiusura se ne aggiungono altri due, quindi per una trasparenza vissuta fino alla chiusura i file diventano **sei** (e di più se le modifiche generano ulteriori versioni). Non è detto se la regola dei quattro file valga anche per la Sintesi.

### 6.5 Cosa aggiunge il campione sul ciclo di vita

Il campione non risolve le domande aperte sugli stati, ma restringe il campo (i dettagli sono nelle sezioni 5.4 e 5.5).

- Le **Sintesi non portano né uno stato né il codice AGCOM**: in nessuna delle venti Sintesi compare un UUID, e "AGCOM" appare soltanto come riferimento a una delibera (Protezione minori). Il segnaposto `{{agcom_code}}` del MAN e l'idea di un codice nel nome della Sintesi non hanno riscontro nei documenti reali. Lo stato e il codice sono quindi attributi **della Trasparenza**, non della Sintesi [CERTO nel campione].
- Nelle Trasparenze, "Nuova" può durare **anni** (offerte del 2021, 2022, 2023 ancora "Nuova") nei segmenti Microbusiness: per loro APERTA non è mai stata raggiunta.
- Una Trasparenza con **data di fine nel passato** (1 febbraio 2026) mantiene lo stato con il codice invece di "Chiusa". Non è visibile nel campione come e quando "Chiusa" venga effettivamente registrata.
- Le coppie Sintesi–Trasparenza dello stesso nome non esistono per tutte le offerte nel campione, in linea con l'idea che i due cicli di vita non siano allineati.
- Le Sintesi hanno "Disponibilità offerta" (data di inizio) e non una data di fine; le Trasparenze hanno data di inizio e fine sottoscrivibilità. Sono i **due insiemi di date** a cui si riferisce MAIL1.

---

## 7. Le azioni massive: cosa si vuole e perché è difficile

### 7.1 Il requisito

È il requisito **più enfatizzato** [CERTO]: applicare una modifica una sola volta e propagarla a tutti i documenti, oppure a un sottoinsieme selezionato, per Sintesi e/o Trasparenze. Le modifiche massive devono poter avvenire su più mercati. È richiesto anche il **flag** per generare solo sintesi, solo trasparenze o entrambe, e la **duplicazione** massiva o a selezione. Quando l'utente avvia una modifica massiva, il sistema deve avvisarlo del numero di offerte coinvolte e chiedere conferma (già presente nell'MVP) [PROBABILE].

### 7.2 Quali campi sono oggetto di modifica massiva

Qui c'è un **buco informativo grave**. L'elenco puntuale dei campi doveva arrivare dai file di censimento (che non ho). I casi **concretamente citati** nei materiali sono:

- **tecnologia** dell'offerta, con relativo bollino (esempio che l'MVP già gestisce tramite un "segnaposto bollino" ripetibile in note e valori delle tabelle dinamiche);
- **prezzo base** e **costo di attivazione** (citati in MAIL1 come possibili candidati al trattamento analogo al bollino);
- **coefficiente RDA**: aggiornamento annuale, presente in tutti i segmenti e aggiornato in simultanea; il campo è comune ma il **valore dipende dal canone del servizio**, quindi non è un unico numero;
- **naming e condizioni della convergenza** mobile–luce–gas: modifica almeno annuale, comune a tutti i segmenti;
- **caratteristiche trasversali** di gruppi di offerte: ad esempio tutte quelle del mondo assicurazione, che includono Netflix o Amazon, o con un certo tipo di copertura (dalla call con gli utenti del Fisso);
- parti dei campi liberi di uso comune (es. il testo "Modifiche" presente in diversi segmenti), anche se nessun documento le cita esplicitamente come candidate [INFERENZA].

Non sappiamo **quali tra le circa trenta o quaranta tabelle delle varie sintesi** contengano campi da modificare in massa, né con che frequenza.

### 7.3 Il nodo delle tabelle dinamiche

Nell'MVP le tabelle di tipo Prezzo, Costi, Servizi sono memorizzate **per offerta**, come strutture padre-figlio in formato JSON (**schema-on-read**, cioè senza uno schema rigido in database). Questo permette di aggiungere tabelle, padri e figli senza sviluppare nulla, ed era la risposta alla varietà delle offerte. Lo stesso MAIL1 riconosce la conseguenza: **questa libertà non consente modifiche massive**, "in quanto le tabelle dinamiche sono personalizzate sulla singola offerta".

Il BRIEF formula il problema così: gli utenti vogliono modifiche massive anche su campi che stanno dentro le tabelle dinamiche; ma una tabella dinamica non ha schema, può esistere o non esistere in una data offerta, e le voci possono chiamarsi in modi diversi. L'esempio dello sviluppatore è chiaro: un operatore crea la voce "velocità massima download", un altro "velocità massima scaricamento", e la modifica massiva dovrebbe agire su entrambe.

Alcune osservazioni descrittive su questo nodo, senza proporre soluzioni:

- Nel REQ i **padri sembrano avere etichette ricorrenti** ("Costo mensile", "Durata minima del contratto del servizio", "Velocità massima di connessione Internet", ecc.): le mappature le trattano come voci tipiche. Nella v0.1 segnalavo che nei materiali non c'era prova che l'esempio dei sinonimi si verificasse davvero. **I file reali lo confermano in parte** (sezione 7.7): per il solo padre della velocità massima esistono cinque formulazioni, ma la divergenza segue per lo più i confini tra segmenti, mentre dentro un segmento le etichette sono stabili. Il censimento delle occorrenze dei campi delle tabelle della Sintesi del Fisso (citato in MAIL2) servirebbe a quantificare il fenomeno su un campione più ampio [APERTO].
- Nel campione, inoltre, il numero e il tipo delle tabelle cambiano da offerta a offerta anche nello stesso segmento (tabelle ripetute per ogni opzione collegata, tabella "Daily Pass" presente solo in alcune offerte, tabella "Costi" ripetuta due o tre volte), quindi la **presenza stessa** di una tabella è un'informazione variabile (sezione 4.8).
- Nei template dell'MVP (MAN) i segnaposto sono **posizionali**: `parent_0_label`, `child_0_1_value`. La posizione nella tabella non esprime il significato della voce.
- Le tabelle dinamiche coprono due cose diverse: l'**insieme di righe** (quali padri e figli esistono in una data offerta) e il **testo delle etichette**. Una modifica massiva sul valore e una sul nome della voce sono richieste di natura diversa.
- Il nodo si riduce quando il campo coinvolto è comune a tutte le offerte (tecnologia, prezzo base, costo attivazione), e si aggrava per campi presenti solo in alcune tabelle o in alcuni segmenti.

### 7.4 Caratteristiche trasversali tra offerte

La richiesta emersa dalla call con il Fisso è di poter modificare massivamente tutte le offerte "che condividono una caratteristica" (assicurazione, Netflix, Amazon, un tipo di copertura). I materiali non dicono come queste caratteristiche vadano rappresentate né chi le dichiara. Oggi non esiste nel modello dati un concetto di "caratteristica" o "etichetta" attribuibile a più offerte [APERTO].

### 7.5 I cluster del Mobile

Dal Mobile è emersa una classificazione delle offerte in tre cluster:

- **Giga finiti**;
- **Giga shaped:** esiste una soglia di GB entro cui si naviga alla massima velocità; oltre si naviga a una velocità ridotta;
- **Giga illimitati**.

Nell'MVP la velocità in upload e download dipende **solo dalla tecnologia** (massimi di Mbps salvati sulla tecnologia). I cluster introducono velocità che dipendono da altro e non sono modellate [APERTO]. Non è detto se il cluster sia solo un'informazione descrittiva o un attributo su cui fare modifiche massive.

**Cosa dice il campione.** I cluster sono visibili nelle Sintesi Etnico. L'offerta "Call Your Country Unlimited Full 5G Easy Pay" ha "GIGA illimitati … alla massima velocità disponibile su rete 5G" e la velocità riportata nella Sintesi è "2.00 Gbps in Download, 200 Mbps in Upload" con l'etichetta "(4) 200 Giga Full Speed". L'offerta "Unlimited Plus EP" ha "Gigabyte in 5G illimitati, di cui 200 in 5G Full Speed, poi con Cap a 10 Mbps" e una **riga di velocità aggiuntiva** (10 Mbps in download e in upload) con l'etichetta "(3) Giga illimitati": la tabella Velocità ha quindi sei righe invece di tre. Anche il Mobile CB riporta "meccanismo di QoS: 10 Mbps in download e upload superati i GIGA alla massima velocità" e il Mobile Microbusiness "Professional Country" indica per i dati oltre soglia "Shaping 128Kbps". In pratica, le offerte "shaped" hanno più coppie di velocità (a seconda del volume) e il cluster non è un attributo dichiarato ma emerge dal testo. Nella Trasparenza Etnico "Flash+ 200" la velocità è un solo valore (2000/200 Mbps) e il "5G Full Speed" compare solo nelle note [PROBABILE]. Anche in Very la velocità non dipende dalla sola tecnologia: l'offerta "Very 5,99 per nuovi numeri" dichiara come tecnologia "3G, 4G, 5G, LTE, LTE Advanced" ma una velocità di **30/30 Mbps**, mentre l'offerta "1000 Giga SPECIAL" dichiara **2000/200 Mbps**. Questo contraddice l'assunzione del modello dati attuale, in cui le velocità massime sono attributi della tecnologia [CERTO nel campione].

### 7.6 Su quali offerte, in quali stati, chi può farla

- Stati: aspettativa di un referente è "tutte le non chiuse" (sezione 6.3) [PROBABILE].
- Perimetro: tutti i documenti, oppure un sottoinsieme selezionato [CERTO]; come si seleziona (per segmento, per tecnologia, per caratteristica, a mano) non è specificato.
- Permessi: un utente modifica solo il proprio segmento (sezione 3.2). Ma campi come **RDA** e **convergenza** sono per definizione comuni a **tutti i segmenti**: chi ha diritto di modificarli in blocco, se ognuno è titolare solo del proprio? [CONTRASTO/APERTO]
- Effetti sui documenti già generati: se una modifica massiva rende superati i file già prodotti, cosa succede? MAIL2 ricorda che nel flusso attuale gli utenti rigenerano le sintesi dalla macro; una modifica massiva senza rigenerazione produce **documenti incoerenti** con ciò che altri vedono sulla scheda. Non c'è risposta su flag "OUTDATED" né sulla conservazione delle versioni [APERTO].

### 7.7 Cosa dicono i file reali sulle azioni massive

I file del campione consentono di verificare dove, nei documenti, vivono davvero i valori che gli utenti vorrebbero cambiare in massa. Il risultato complica il problema formulato nel BRIEF, ma gli dà anche contorni più precisi.

#### Un "campo" è spesso sparso in più punti

Un cambio di prezzo non tocca una cella: tocca la tabella Prezzo, le frasi che scompongono il prezzo (con una relazione aritmetica tra totale e componenti), le note di una o più tabelle, il nome del file e, nella Trasparenza, la cella strutturata e la nota. Lo stesso vale per la durata di una promozione, per il costo di attivazione e la sua rateizzazione (ad esempio "49,99 euro" e "24 rate mensili di 2,08 euro" compaiono sia in tabella sia nella nota a piè di tabella) e per il nome dell'offerta (intestazione, nome file, Trasparenza). Le Sintesi Fisso Microbusiness mostrano inoltre che il prezzo totale è la somma di componenti dichiarate nel testo, per cui una modifica massiva su un componente richiede di ricalcolare totale e frasi.

#### Valori e testi comuni a molte offerte

Nel campione ci sono numerosi valori e blocchi ricorrenti, candidati naturali alle modifiche massive:

- costo SIM di 10 euro (6 Sintesi su 20), tariffa di 0,29 euro per SMS extra soglia (6 su 20), 0,99 euro per il GIGA giornaliero (4 su 20), costo di disattivazione di 10 euro "pari al costo realmente sostenuto" (4 su 20);
- riferimenti a delibere AGCOM: 290/21/CONS in 12 Sintesi, 156/23/CONS in 10, 9/23/CONS in 8 (una modifica normativa colpisce tutti i documenti che le citano);
- collegamenti alle pagine del sito sul roaming (10 Sintesi su 20), con testi di link in parte segnaposto (es. "link al sito Roaming Europa");
- i blocchi di testo comune descritti nella sezione 4.8, che però esistono in più varianti.

#### Le etichette divergono davvero, ma soprattutto tra segmenti

L'esempio dei sinonimi ("velocità massima download" contro "velocità massima scaricamento") indicato nel BRIEF non compare nei file, ma lo **stesso fenomeno esiste nelle etichette dei padri**. Per il solo padre della velocità massima ci sono cinque formulazioni:

| Formulazione dell'etichetta | Dove |
|---|---|
| "Velocità massimo di connessione Internet" (con "massimo" al maschile) | Fisso Microbusiness (8 Sintesi su 8) |
| "Velocità massima di connessione Internet" | Fisso CB Consumer |
| "Velocità di connessione Internet massima stimata (n)" con un numero di nota variabile da (1) a (4) | Mobile e Etnico |
| "Velocità di connessione Internet massima stimata (4) 200 Giga Full Speed" / "… (3) Giga illimitati" | Etnico (due varianti nello stesso segmento, con un'indicazione di cluster nell'etichetta) |
| "Velocità di connessione internet massima stimata(2)" (minuscolo, senza spazio) | Very |

Altri esempi: "Costo disattivazione servizio" (5 Sintesi), "Costo disattivazione anticipata del servizio" (2), "Costo disattivazione" (Very, 2); "Eventuali sconti e loro durata" (6) e "Eventuali scontistiche e loro durata" (8); "Condizioni di rinnovo o risoluzione al termine della durata minima" nel Fisso, con l'aggiunta ", se prevista" negli altri; "Costo mensile (salvo eventuali promozioni)", "Costo mensile", "Costo ricorsivo (al lordo di eventuali promozioni)", "Costo canone del servizio, salvo sconto canone dedicato" per il prezzo ricorrente. Due osservazioni.

- **Dentro lo stesso segmento le etichette sono molto stabili** (es. otto Sintesi Fisso Microbusiness con la stessa formulazione), mentre la divergenza segue per lo più il **confine di segmento o di mercato**. Il campione è piccolo e non basta per dire che accada sempre così [INFERENZA], ma ridimensiona l'ipotesi che ogni operatore scriva etichette diverse per lo stesso concetto.
- Alcune etichette **contengono un numero di nota variabile** ("(1)", "(2)", "(3)", "(4)") o parti che indicano il cluster dell'offerta ("200 Giga Full Speed", "Giga illimitati"). L'etichetta non è quindi solo un nome: incorpora riferimenti ad altri elementi del documento e informazioni di tipo commerciale.

Il vero problema non è dunque solo "come far corrispondere due nomi diversi", ma che l'etichetta, il valore, il numero di nota e le frasi correlate sono parti di uno stesso insieme che oggi viene mantenuto a mano.

#### Alcune dipendenze tra segmenti e tra documenti

Oltre al riferimento incrociato Mobile–Fisso già citato (24,99 contro 25,99), la convergenza luce&gas, la politica di roaming e i servizi aggiuntivi compaiono con forme diverse in segmenti diversi. Le opzioni collegate all'offerta (Reload Forever, Più Sicuri Mobile) portano con sé **proprie tabelle di descrizione e di prezzo** (Mobile CB), proprie voci di costo (Fisso) o semplici paragrafi (Mobile GA, Etnico): una modifica massiva su "tutte le offerte con Reload Forever" dovrebbe quindi agire in due forme diverse (tabella nel Mobile CB, paragrafo nel Mobile GA e nell'Etnico).

---

## 8. Cosa deve produrre il sistema

### 8.1 Gli output

Quattro file per offerta [CERTO]:

1. Sintesi contrattuale in **Word**;
2. Sintesi contrattuale in **PDF** (accessibile);
3. Trasparenza tariffaria in **Excel** (formato AGCOM);
4. Trasparenza tariffaria in **PDF**.

L'utente seleziona le offerte e **quali output** gli servono (solo Sintesi, solo Trasparenza, entrambi). Il BRIEF descrive invece un bottone per singola offerta con "crea sintesi" e "crea trasparenza": i due modi d'uso (singolo e batch) non sono in contraddizione, ma il REQ parla di produzione in blocco.

### 8.2 Consegna

Il REQ prevede la consegna **via email in formato compresso**, con possibile organizzazione in sottocartelle distinte per Sintesi e Trasparenze (valutato, non deciso). Il modello dati dell'MVP prevede invece l'archiviazione dei file su storage cloud con versioni. I due approcci non sono alternativi, ma il materiale non chiarisce quale sia il canale principale e per quanto tempo i file restano disponibili [APERTO].

### 8.3 File aggiuntivo per Adobe

Poiché Adobe esporta in CSV, gli utenti chiedono di poter **scaricare dallo strumento un file di mappatura delle sintesi nello stesso formato di Adobe** [CERTO come richiesta]. Il formato non è descritto e non ne abbiamo un esempio.

### 8.4 Cosa storicizzare

L'ultima domanda strutturale è che cosa conservare nel tempo: stato delle offerte, contenuto delle tabelle a ogni transizione, file generati, versioni. MAIL2 chiede di fare una **proposta con pro e contro** per ciascuna opzione; il cliente non ha una preferenza espressa e collega la scelta alla visibilità che gli utenti devono avere su ciò che hanno prodotto (cartelle di output). Anche la struttura dei nomi dello storage è rimandata a questa decisione [APERTO].

---

## 9. Tracciabilità, sicurezza, requisiti non funzionali

- **Audit completo:** "sicuramente è necessario tracciare tutte le operazioni degli utenti": chi crea, modifica, inserisce il codice, chiude, elimina, esegue una modifica massiva [CERTO]. Il REQ non cita la cancellazione delle offerte: è un'operazione prevista? [APERTO]
- **Segregazione per segmento** con editor autorizzati [CERTO]; visibilità trasversale richiesta dagli utenti [PROBABILE].
- **Flessibilità del modello dati:** il database deve poter accogliere nuovi campi non previsti oggi [CERTO]. Il REQ stesso nota che la fattibilità di un unico database va verificata dopo la mappatura dei campi [PROBABILE: nota a margine].
- **Accessibilità** dei PDF e conformità agli standard AGCOM [CERTO].
- **Volumi:** non c'è alcun numero su quante offerte attive, quanti documenti l'anno, quanti utenti simultanei [APERTO].
- **Migrazione iniziale:** le offerte attuali vivono in file sparsi; il REQ cita una cartella con offerte di esempio da usare per costruire la base dati, ma non dice se tutte le offerte esistenti vadano importate né come [APERTO].

---

## 10. Lo stato attuale dell'MVP e del modello dati

Questa sezione descrive ciò che esiste, non propone cambiamenti.

### 10.1 Cosa fa il prototipo

Dalle email e dai manuali risulta che l'MVP già permette di: creare offerte con campi fissi e tabelle dinamiche; generare Sintesi da template Word con segnaposto e Trasparenze da un template Excel; sostituire bollini in base alla tecnologia; eseguire una modifica massiva su un **sottoinsieme di campi**; mostrare il numero di offerte selezionate prima di confermare. Aggiungere tabelle non richiede sviluppo [PROBABILE: è quanto affermato in MAIL1].

Il comportamento dei template è descritto nel MAN: segnaposto globali per nome offerta, tecnologia, prezzo, codice AGCOM, codice PO; tabelle dinamiche con righe padre e figlio in due layout (a due colonne affiancate o a una colonna); quattro combinazioni di padre e figli (padre semplice, intestazione senza valore, padre con valore e figli, figli senza valore); traduzione "ND" in "Non applicabile"; eliminazione automatica delle righe senza valore; note ancorate sotto la tabella; grassetto e link in markdown o HTML.

### 10.2 Stack e scelte già presenti nel DB

Il DB descrive un'architettura su **Google Cloud Spanner (dialetto PostgreSQL)**, applicazione in Python/FastAPI con SQLAlchemy, chiavi UUID generate dall'applicazione, file su Google Cloud Storage, identità tramite OIDC aziendale, SQLite come motore locale di test. Sono scelte di progetto, non requisiti del cliente.

### 10.3 Le entità

Nel modello attuale (variante più recente, "NEW 3") ci sono: **segmenti**, **utenti**, **ruoli utente per segmento**, **tecnologie** (con bollino, testo alternativo, colore, velocità massime), **modalità di pagamento**, **offerte**, **costi di attivazione per tipo di cliente** (già clienti, nuovi nativi, nuovi in portabilità), **tabelle dinamiche** (con identificatore tra Prezzo, Costi, Servizi, titolo, contenuto in formato JSON e note), **storico dei cambi di stato**, **snapshot delle tabelle** congelate a ogni cambio di stato, **documenti** (con tipo, versione, flag di corrente). Esiste anche una tabella di **configurazioni globali** (es. coefficiente RDA).

### 10.4 Il documento DB contiene più versioni e non è coerente al suo interno

Il file DB riporta quattro schemi in sequenza (versione originale, NEW, NEW 2, NEW 3) senza indicare quale sia quella in uso; la specifica fisica dettagliata descrive la versione originale a 7 tabelle. Differenze rilevanti: la tecnologia e le modalità di pagamento passano da colonne dell'offerta, a tabelle di relazione molti-a-molti, a tabelle di anagrafica con singolo riferimento; i riferimenti ai file passano da colonne dello storico a una tabella documenti; l'identificatore del segmento passa da codice testuale a UUID; la modalità di pagamento ammette due valori nella specifica fisica e tre nei diagrammi (si aggiunge "sepa_pa") [CONTRASTO].

### 10.5 Scarti tra il modello e quanto emerso dalle call

Senza proporre soluzioni, questi sono i punti in cui il modello dati attuale **non copre** quanto emerso.

- **Date separate:** il modello ha un solo inizio e una sola fine validità per offerta; dalle call emerge che la **data di validità della Sintesi non coincide con quella della Trasparenza** (MAIL1).
- **Più codici AGCOM per offerta:** l'offerta ha un solo codice corrente, ma nella maggior parte dei segmenti si generano trasparenze distinte (ciascuna col suo codice) per combinazione offerta–punto prezzo.
- **Un solo prezzo base:** l'offerta ha un solo prezzo, mentre esistono più punti prezzo e le sintesi sono distinte per prezzo.
- **Velocità legate solo alla tecnologia:** non coprono i cluster mobile (giga shaped).
- **Una sola tecnologia per offerta** nella variante NEW 3: nel Fisso il naming della Sintesi include la tecnologia, e non è chiaro se la stessa offerta possa essere in più tecnologie (nelle varianti precedenti era previsto).
- **Campi liberi:** i campi liberi di testo (note, "Modifiche", "Funzioni per utenti con disabilità", testi lunghi sopra la pagina) non hanno una collocazione esplicita se non il campo delle note.
- **Tracciamento di tutte le operazioni:** il modello ha lo storico dei cambi di stato, non un log di tutte le modifiche, né delle modifiche massive, né delle cancellazioni (c'è solo una marcatura di eliminazione logica).
- **Caratteristiche trasversali:** non esiste un concetto equivalente.
- **RDA con valore dipendente dal canone:** la configurazione globale contiene un singolo valore per chiave.
- **Tabella documenti:** il tipo "TEMPLATE_DOCX / TEMPLATE_XLSX" è ambiguo, perché la descrizione parla a volte di template e a volte di file compilato; mancano i tipi esplicitamente dedicati alla Sintesi Word generata e alla Trasparenza Excel generata.

---

## 11. Registro sintetico di certezze e dubbi

### 11.1 Ciò che è sicuro

- Utenti = marketing di nove gruppi, ciascuno modifica solo il proprio mercato e segmento.
- Due documenti distinti (Sintesi e Trasparenza), con quattro output (Word e PDF; Excel e PDF), generabili separatamente.
- Formato della Trasparenza dettato da AGCOM, senza flessibilità.
- Le sole parti fisse dei documenti sono etichette e titoli; il resto è variabile.
- Struttura a tabelle con padre e figli, con numeri massimi che non vanno blindati.
- "ND" diventa "Non applicabile"; righe vuote eliminate; note sotto la tabella.
- La modifica massiva è il requisito prioritario, su tutti i documenti o su una selezione.
- Tre stati (Nuova, Aperta, Chiusa) dichiarati confermati.
- Codice AGCOM: arriva dopo il caricamento, entro 10 giorni, e va registrato.
- Gli utenti vogliono conservare i file precedenti al codice senza sovrascriverli.
- Tracciamento di tutte le operazioni degli utenti.
- Vincoli di Adobe su PDF e nome file; nome file con campo personalizzabile.
- Il Very Mobile deve avere il codice PO nel nome file.
- Distribuzione sui canali a carico degli utenti.

**Confermato dai file reali (v0.2):**

- Il codice AGCOM è un **UUID di 36 caratteri**, scritto nella cella "Stato dell'offerta" della Trasparenza.
- Stato e codice sono attributi della **Trasparenza**, non della Sintesi: nessuna delle venti Sintesi del campione li riporta.
- La Trasparenza ha una **griglia fissa** di circa 45 righe con etichette identiche, più una zona di note libere con una parte finale ricorrente.
- L'IVA dipende dal segmento: inclusa nei Consumer, esclusa nei Microbusiness.
- Lo schema padre-figlio è reale, ma assume **tre forme fisiche** (una, due e tre colonne).
- I testi comuni sono moltissimi, ma esistono in **più varianti** non identiche.
- Il prezzo e altri valori compaiono in più punti dello stesso documento, spesso dentro frasi, e il prezzo totale è la somma di componenti dichiarate nel testo.

### 11.2 Ciò che è probabile ma non formalizzato

- Modifica massiva su tutte le offerte non chiuse; chiuse non modificabili.
- Offerte modificabili anche dopo il codice AGCOM, compreso il codice.
- Visibilità trasversale agli altri gruppi, modifica solo del proprio.
- Avviso con conteggio prima della modifica massiva.
- Titolo per tutte le tabelle (soggetto a verifica regolamentare); nel campione la proposta di nuovi titoli per i servizi a pagamento non risulta ancora applicata.
- Il "totale" delle righe massime del REQ corrisponde alle righe fisiche della tabella Prezzo (vale per Mobile GA Consumer e Microbusiness, non per l'Etnico).
- Le divergenze di etichette tra documenti seguono per lo più il confine tra segmenti.
- La Trasparenza di Mobile CB rappresenta la composizione massima e copre più Sintesi.

### 11.3 Ciò che è aperto

- Che cosa è l'"offerta" come unità di gestione (rispetto a punto prezzo, tecnologia, Sintesi, trasparenza).
- Modifica in-place o creazione di nuova versione.
- Significato esatto di CHIUSA e comportamento delle chiuse rispetto agli aggiornamenti regolamentari.
- Stati realmente usati per segmento.
- Elenco dei campi soggetti a modifica massiva e regole per le tabelle senza schema.
- Rappresentazione delle caratteristiche trasversali e dei cluster Mobile.
- Chi può eseguire modifiche massive che attraversano più segmenti.
- Politica di storicizzazione, versioni e "documenti superati".
- Date di validità separate tra Sintesi e Trasparenza.
- Canale di consegna dei file e struttura delle cartelle.
- **Nuovi (v0.2):** come trattare le tabelle che si ripetono per ogni opzione collegata; il significato di "ND" contro "vuoto"; se le varianti dei testi comuni siano volute; come gestire le relazioni aritmetiche tra prezzo totale e componenti; la forma a tre colonne di Very; le due posizioni della griglia Excel (WINDTRE e Very); come si registra in pratica "Chiusa"; l'identità di un'offerta quando lo stesso nome commerciale compare con prezzi diversi.

---

## 12. Contraddizioni, sovrapposizioni e incoerenze tra i documenti

| # | Tema | Cosa dice una fonte | Cosa dice l'altra | Note |
|---|---|---|---|---|
| 1 | Dove si inserisce il codice AGCOM | REQ: nel campo "Stato dell'offerta" dell'Excel | BRIEF/DB: in un campo dedicato del form, con passaggio automatico ad APERTA | Vedi anche 2 |
| 2 | Chi usa APERTA | REQ: stati confermati, tre stati | Commenti: Very solo Nuova/Chiusa; Micro solo Nuova; Mobile GA Consumer non si riconosce | Gli stati non valgono per tutti |
| 3 | Significato di CHIUSA | REQ: non più sottoscrivibile | BRIEF/MAIL2: non più modificabile/sovrascrivibile | Concetto commerciale contro blocco di sistema |
| 4 | Formato codice AGCOM | REQ: alfanumerico unico, ~10 giorni; DB: lunghezza 10 o 36; MAN: esempi tipo `COD1234567` | MAIL2: UUID RFC 4122 (36 caratteri) | Tre formati diversi |
| 5 | Modificabilità dopo il codice | MAIL2 (Q3): sì, perché Sintesi e Trasparenza hanno cicli non allineati | REQ e Mobile CB: modifica del punto prezzo più alto = chiusura + nuova trasparenza | In-place contro nuova versione |
| 6 | Mobile CB Consumer | REQ 1.2.2: solo trasparenze del punto prezzo più alto | REQ (sezione trasparenze): si producono tutti gli output per punto prezzo e si sceglie il più alto | Interno al REQ |
| 7 | Numero di file | REQ: "4 file" (pre-codice e post-codice) | REQ: la chiusura aggiunge altri 2 file | Interno al REQ |
| 8 | Visibilità | REQ: l'utente gestisce solo il proprio segmento | MAIL2: vuole vedere anche gli altri | Raffinamento o contraddizione? |
| 9 | Naming della Sintesi WINDTRE | REQ: nome + tecnologia + prezzo + elemento diversificante (data o canale) | MAN: suffisso `_NUOVA` o codice AGCOM nel nome | Il MAN non contempla il diversificante e inserisce il codice nella Sintesi |
| 10 | Naming Very Mobile | REQ: struttura `data_prezzo_GB_attivazione_PO`, ma digitazione libera accettata | MAN: nome esattamente come digitato, senza regole | Compatibili solo se il nome libero rispetta il vincolo del PO |
| 11 | Codice AGCOM nella Sintesi | REQ: il codice riguarda la Trasparenza | MAN: segnaposto `{{agcom_code}}` nella Sintesi e codice nel nome della Sintesi | **v0.2:** nessuna delle 20 Sintesi del campione contiene il codice né uno stato; il codice è un attributo della Trasparenza |
| 12 | Posizione bollini | REQ: nel Fisso restano il primo e il terzo bollino, dentro le griglie | MAN: bollino inserito nella tabella 1, accanto alla tecnologia | Il MAN non copre il terzo bollino |
| 13 | Colori bollini | REQ: solo verde, giallo, rosso (Pantone AGCOM) | MAN: verde, giallo, e un grigio/blu per il 5G; il rosso non è mai usato | Il bollino 5G non rientra nei colori AGCOM descritti |
| 14 | IVA sul prezzo | MAN/DB: prezzo base mensile IVA inclusa | REQ (Fisso CB Micro): prezzi IVA esclusa salvo diversa indicazione | **v0.2:** chiarito dal campione. Il regime IVA dipende dal segmento (Consumer inclusa, Microbusiness esclusa); il MAN e il DB sbagliano a presumere "IVA inclusa" per tutti |
| 15 | Righe vuote | REQ (inizio): ipotesi di riempire le righe vuote con "non applicabile" oppure righe dinamiche | REQ (accordo successivo): ND = "Non applicabile", vuoto = riga omessa | Risolto più avanti nello stesso REQ; il MAN applica la seconda |
| 16 | "Trucco dello spazio singolo" | MAN: un valore " " impedisce l'eliminazione della riga e lascia la cella visivamente vuota | REQ: nessuna riga o cella vuota per accessibilità | Il trucco può reintrodurre celle vuote |
| 17 | Note della trasparenza | REQ: richiesta di dividere in parte fissa e parte variabile (proposta marketing Fisso) | REQ (commento): sul DB la nota sarà unica e l'utente modifica la parte desiderata | Richiesta e decisione divergenti |
| 18 | Righe massime | REQ 1.2.1: righe per sezione per segmento | REQ (mappatura): padri e figli per tabella | Metriche diverse non riconciliate |
| 19 | Titoli "Servizi" | Fisso CB Consumer: "Servizi a pagamento", separati da Costi | Fisso GA/CS: "Servizi non inclusi", con servizi inclusi accorpati ai costi | Stessi contenuti con titoli e accorpamenti diversi |
| 20 | Fisso GA Consumer | CB Micro: "valido anche per Fisso GA CNS" | Esistono anche sezioni distinte "Fisso CNS CVM/Cross Selling" e "Fisso GA/CS MB" | Non è chiaro quale struttura vale per quale segmento |
| 21 | Numero di tabelle Fisso | MAIL2: discrepanza tra tabelle emerse dagli utenti e tabelle mostrate nelle riunioni | — | Il file di confronto non è disponibile |
| 22 | Modello del DB | DB: quattro versioni (originale, NEW, NEW 2, NEW 3) e specifica fisica della prima | — | Non indicata la versione in uso |
| 23 | Standard "228/229/230" | MAN: li presenta come standard AGCOM | REQ: gli stessi comportamenti sono accordi interni, senza questa numerazione | Fonte della numerazione non tracciabile |
| 24 | Velocità | DB: dipende solo dalla tecnologia | MAIL1: nel Mobile esistono cluster (shaped) con velocità dipendente da altro | Il modello non copre il caso |
| 25 | Output e consegna | REQ: email con zip | DB: archiviazione cloud con versioni | Non necessariamente in contrasto |
| 26 | Date | DB: un solo intervallo di validità | MAIL1: validità Sintesi diversa da validità Trasparenza | Il modello non separa le due. **v0.2:** nel campione la Sintesi ha solo la data di disponibilità, la Trasparenza ha inizio e fine |
| 27 | Formato del codice AGCOM | MAN: esempi tipo `COD1234567`; DB: lunghezza 10 o 36; REQ: "alfanumerico" | CAMP: UUID di 36 caratteri in tutte le tre Trasparenze con codice | **v0.2:** il formato UUID è confermato; il valore da 10 caratteri non compare |
| 28 | Dove si scrive il codice | BRIEF: campo dedicato del form che causa il passaggio ad APERTA | REQ e CAMP: il codice è scritto nella cella "Stato dell'offerta" | **v0.2:** prevale la lettura del REQ; APERTA è uno stato interno non presente nel file AGCOM |
| 29 | "ND" e "Non applicabile" | REQ: ND diventa "Non applicabile" | CAMP: Mobile e Very mostrano "ND" letterale (18 celle in ogni Sintesi Very); il Fisso scrive "Non applicabile" | La regola cambierebbe il testo oggi visibile al cliente finale in Mobile e Very |
| 30 | Titolo della tabella 2 (Mobile Consumer) | REQ: "Descrizione Offerta" per Mobile GA e CB insieme | CAMP: GA = "Servizio/i e apparecchiature"; CB = "Descrizione Offerta" | GA e CB, accorpati nel REQ, hanno titoli e struttura diversi |
| 31 | Titoli dei servizi a pagamento nel Fisso | REQ: nuovi titoli "Servizi non inclusi" / "Servizi a pagamento" | CAMP (modificato a fine settembre 2026): tre tabelle tutte intitolate "Costi" | La proposta non risulta applicata nei documenti campione |
| 32 | Layout delle tabelle | MAN: due layout (due colonne affiancate; una colonna) | CAMP: tre layout fisici (Fisso a una colonna, Mobile a due, Very a tre con padre ripetuto) | Il layout di Very non è descritto nel MAN |
| 33 | Testo alternativo dei bollini | REQ e MAN: obbligatorio e significativo | CAMP: significativo in 6 Sintesi su 20; generato automaticamente da Word in 7; assente in 7 | Il requisito di accessibilità non è oggi rispettato in modo uniforme |
| 34 | Nome file e caratteri ammessi | REQ: solo punto, underscore, trattino; niente spazi | CAMP: nomi con virgole (nei prezzi), simbolo €, spazi; ordine degli elementi variabile in Very | Non è chiaro se questi sono i nomi dei Word o dei PDF finali |
| 35 | Velocità e tecnologia | DB: velocità massima come attributo della tecnologia | CAMP: Very "5,99" dichiara 3G-4G-5G con 30/30 Mbps; Very "1000 Giga" dichiara 2000/200 Mbps | La velocità dipende dal prodotto, non dalla sola tecnologia |
| 36 | FTTC e FTTC Extra | REQ: tra standard e full speed cambia solo la velocità e il bollino grafico | CAMP: nelle coppie FTTC/FTTC Extra il testo è identico o quasi e l'immagine del bollino è la stessa | La differenza non è visibile nel contenuto dei documenti |
| 37 | RDA | REQ: campo comune, valore variabile col canone | DB: una chiave di configurazione globale con un solo valore | CAMP: il valore sta dentro un testo (Mobile) o è solo un link (Fisso, Very) |
| 38 | Nome commerciale tra Sintesi e Trasparenza | REQ: il nome identifica l'offerta (nel nome file) | CAMP: "INTERNET 100 Professional" ha canoni 29,99 e 40,99 in due documenti; "INTERNET 100 Full Professional" (Sintesi) e "ABSOLUTE 100 Full Professional" (Trasparenza) hanno nome e prezzo diversi | Il nome non è un identificatore affidabile |
| 39 | Riferimento tra segmenti | Mobile Microbusiness "Professional Country": canone fisso convergente 24,99 | Fisso Microbusiness "Professional": canone convergente 25,99 (ultima modifica diversa) | Possibile deriva da aggiornamento non propagato |
| 40 | Target nella Trasparenza Very | Trasparenza Very "5,99 per nuovi numeri": target = nuovi clienti in portabilità | Stessa offerta: prezzi di attivazione compilati sui nuovi clienti nativi; la Sintesi parla di nativi | Verosimile errore di compilazione manuale |
| 41 | Stato e data di fine | REQ: alla chiusura si scrive "Chiusa" e la data di fine | CAMP: due Trasparenze Etnico con data di fine nel passato ma con stato = codice | Non è visibile come venga registrata la chiusura |
| 42 | Titolo del documento nel PDF/UA | MAN: output PDF/UA | CAMP: nessuno dei 20 Word ha il titolo del documento nelle proprietà | Il titolo è richiesto dallo standard PDF/UA |
| 43 | Sintesi contrattuale e data di validità | REQ: padre "Offerta valida fino al" con figli diversi | CAMP: in tutte le Sintesi WINDTRE il valore è la frase fissa "valida fino alla chiusura…", mai una data | La data di fine non compare in nessuna Sintesi |

### Ripetizioni (non contraddizioni)

Molte informazioni sono ripetute in più punti, per lo più coerenti: gli stati dell'offerta compaiono sia nel paragrafo "To-Be" sia nei commenti; la regola "chiusa = Excel e PDF nuovi con stato chiuso e data di fine" compare due volte nel REQ; il naming è ripetuto tra sezione generale, Sintesi e Trasparenze; la regola del codice AGCOM "10 giorni" e i processi per segmento sono ripetuti tra 1.2.2 e le note; il vademecum è citato più volte; le regole su righe vuote e "ND" sono ripetute tra REQ e MAN. Le duplicazioni sono utili da conoscere perché una modifica a una regola va riportata in tutti i punti.

---

## 13. Domande aperte da smarcare

Le domande sono raggruppate per tema; accanto a ciascuna indico perché conta. L'ordine riflette l'impatto sul modello dati.

### A. Unità di gestione

1. **Che cosa è, esattamente, una "offerta"** nel sistema? La combinazione nome–tecnologia–prezzo (come la Sintesi), nome–punto prezzo (come la Trasparenza), il PO (Very Mobile)? Una Sintesi può riferirsi a più trasparenze e viceversa?
2. **Cosa è un "punto prezzo"**, e quanti ce ne sono per offerta?
3. Una stessa offerta può essere disponibile in **più tecnologie**? Se sì, genera una Sintesi per tecnologia?

### B. Ciclo di vita e stati

4. **Ogni segmento usa tutti e tre gli stati?** Very, Micro Mobile GA e Micro Fisso CB dichiarano di usare solo "Nuova" (e Very anche "Chiusa"): per loro il codice viene comunque registrato? Si può passare da Nuova a Chiusa direttamente?
5. Il codice AGCOM va inserito in un **campo dedicato** o dentro il campo "Stato dell'offerta" dell'Excel? Cosa mostra l'Excel in ciascuno stato? *(v0.2: il campione mostra il codice dentro la cella "Stato dell'offerta"; resta da confermare con gli utenti e da chiarire cosa mostra il file in stato "Chiusa".)*
6. **Chiusa** significa "non più sottoscrivibile" o "non più modificabile"? Le offerte chiuse hanno ancora clienti per cui servono aggiornamenti regolamentari?
7. Una chiusura può essere **annullata** o corretta?
8. Un'offerta **Nuova** è modificabile in attesa del codice? E dopo il codice? Il codice stesso è modificabile? (risposte attuali non risolutive)
9. Una modifica a un'offerta già con codice **modifica lo stesso record** oppure ne crea uno nuovo che sostituisce il precedente (chiudendo il vecchio)? Vale per ogni campo o solo per quelli che toccano la Trasparenza?
10. La regola dei **quattro file** vale per la Sintesi, per la Trasparenza o per entrambe? E dopo la chiusura i file diventano sei?
11. Quale è il **formato esatto del codice AGCOM**: UUID, codice di 10 caratteri o altro? Dove si trova la fonte (Vademecum)? *(v0.2: nel campione tutti i codici sono UUID da 36 caratteri; resta da confermare che non esistano codici in altri formati, ad esempio per offerte più vecchie.)*
12. Per il **Mobile CB Consumer** valgono le trasparenze solo del punto prezzo più alto o tutti i punti prezzo con scelta successiva?

### C. Azioni massive

13. **Qual è l'elenco puntuale dei campi** per cui gli utenti vogliono modificare in massa, segmento per segmento, con frequenza? (Dal file "azioni massive PRECONTRATTI FISSO all.xlsx" e dall'equivalente Mobile.)
14. Quali di questi campi sono **scalari dell'offerta**, quali stanno **dentro tabelle** e quali sono **parti di testi liberi**?
15. Nei dati reali, il **problema dei sinonimi** ("download" contro "scaricamento") si verifica? Con che frequenza? Le etichette dei padri sono libere o provengono da un elenco condiviso? *(v0.2: il campione mostra cinque formulazioni per la sola "velocità massima", prevalentemente tra segmenti; manca la stima su un campione più ampio e la risposta su chi sceglie le etichette.)*
16. La modifica massiva deve agire sul **valore**, sull'**etichetta**, sulla **presenza/assenza di una riga**, o su tutti e tre?
17. Come si **seleziona** il gruppo di offerte? Per segmento, tecnologia, caratteristica comune, scelta manuale, filtri salvati?
18. Come vanno rappresentate le **caratteristiche trasversali** (assicurazione, Netflix, Amazon, coperture)? Sono tag decisi dagli utenti? Sono un insieme chiuso o aperto?
19. **Chi può eseguire** una modifica massiva su campi comuni a più segmenti (RDA, convergenza)? Serve un ruolo trasversale?
20. Una modifica massiva deve poter essere **annullata** o simulata prima di applicarla (anteprima)?
21. Dopo una modifica massiva, i file già generati diventano **"superati"**? Gli utenti devono poter vedere tutte le versioni o solo l'ultima?
22. Il **coefficiente RDA**: qual è la regola esatta che lega il valore al canone? Il valore è un numero per fascia di canone o un'intera tabella?
23. Il censimento delle occorrenze dei campi delle Sintesi del Fisso: **quali risultati** ha prodotto?

### D. Struttura dei documenti

24. Qual è il **numero reale di tabelle** per segmento (la discrepanza segnalata in MAIL2) e quali tabelle sono **identiche** tra segmenti?
25. Per il **Mobile**: quali differenze tra le tabelle fisse dei vari segmenti sono volute e stabili, e quali sono accidentali?
26. Il cluster **giga finiti / shaped / illimitati** è un attributo dell'offerta, e come incide su velocità e testi?
27. Le **date di validità** di Sintesi e Trasparenza: quali sono i campi esatti e quali regole li legano?
28. Quali sono i **campi liberi** previsti per ogni segmento e quali sono comuni a più segmenti?
29. Sulle righe massime: qual è la lettura corretta del "totale" per segmento? Il **limite non va blindato**, ma serve un massimo per layout?
30. **Il titolo di tutte le tabelle**: l'area regolamentare ha risposto? Titoli al singolare o al plurale?
31. Cosa significano **CVM** e **CDA**? Che struttura vale per **Fisso GA Consumer**?
32. Il regime **IVA** dipende sempre dal segmento (Consumer inclusa, Microbusiness esclusa) e dove va indicato? *(v0.2: il campione suggerisce di sì; da confermare, in particolare per Etnico, Very e per le offerte convergenti Consumer–Microbusiness.)*
33. Il bollino **5G** è un bollino AGCOM? Che colore deve avere? Dove deve comparire il terzo bollino della Fibra?

### E. Output e storicizzazione

34. L'output principale è l'**email con zip** o il **download dall'interfaccia**? Per quanto tempo i file devono restare disponibili?
35. Il **file di mappatura per Adobe**: abbiamo un esempio del formato CSV?
36. Il sistema deve **bloccare** la generazione se il PDF supera 2 MB, il nome supera 160 caratteri o contiene caratteri vietati, o deve solo avvisare?
37. **Cosa storicizzare** (stato, contenuto delle tabelle, file, versioni) e con quale granularità? Chi deve poter accedere allo storico?
38. Il campo **note della Trasparenza**: unico (come deciso) o diviso in parte fissa e variabile (come chiesto)?
39. Il **naming** della Sintesi WINDTRE deve includere l'elemento diversificante? E il codice AGCOM deve comparire nella Sintesi o nel nome file?

### F. Permessi, audit, dati

40. Gli utenti possono **vedere** tutti i segmenti e **modificare** solo il proprio? E per le offerte Cross Selling, chi è il titolare?
41. È prevista la **cancellazione** di un'offerta? Con quali effetti sui file e sull'audit?
42. Quali **operazioni** devono finire nel registro di audit, e per quanto tempo si conservano?
43. Quanti sono **offerte attive, offerte chiuse, documenti annui**? Va fatta una **migrazione** dei dati dai file esistenti?
44. Chi mantiene i **template** (Word ed Excel) e le **anagrafiche** (tecnologie, bollini, modalità di pagamento) quando cambiano?
45. Per i PDF, il sistema deve **garantire** l'accessibilità o solo agevolare il controllo manuale oggi svolto?

### G. Emerse dall'analisi dei file reali (v0.2)

46. **Tabelle ripetute per opzione:** quando un'offerta ha opzioni collegate (Reload Forever, Più Sicuri Mobile, ecc.), ogni opzione genera una propria coppia di tabelle (descrizione e prezzo) nel Mobile CB, un paragrafo nel Mobile GA/Etnico e una voce di costo nel Fisso. Quali sono le **opzioni previste** e come devono comparire nei documenti? La lista delle opzioni è chiusa?
47. Le Sintesi **FTTC** e **FTTC Extra** dello stesso prodotto sono praticamente identiche nel contenuto. Cosa le distingue, e per quale motivo si producono due documenti?
48. Le Sintesi "gemelle" differiscono per qualche riga dei testi comuni (es. "Modifiche"). Le **varianti dei testi comuni** sono volute (per segmento o mercato) o sono residui di aggiornamenti manuali? Quale versione è quella corretta?
49. Quando il **prezzo totale** è la somma di componenti dichiarate nel testo (canone, chiamate illimitate, rata modem), gli utenti inseriscono il totale, i componenti o entrambi? Il totale deve essere sempre calcolato dai componenti?
50. Cosa distingue **"ND" da un valore vuoto** per chi compila? E il "-" (usato nelle Trasparenze e in alcune celle delle Sintesi) deve diventare "Non applicabile" nella Sintesi?
51. Le **forme a tre colonne** di Very (padre ripetuto in ogni riga) sono volute? Il formato Very deve convergere con quello WINDTRE, come proposto nel REQ ("uniformare la struttura delle tabelle prezzi")?
52. Qual è l'**identificatore reale** di un'offerta WINDTRE, dato che lo stesso nome commerciale compare con prezzi diversi e che Sintesi e Trasparenza usano nomi diversi per lo stesso prodotto (es. "INTERNET 100" contro "ABSOLUTE 100")?
53. Una **Sintesi con più punti prezzo** (nuovi clienti, convergente con il mobile, seconda linea) corrisponde a quante Trasparenze? Come si lega la Sintesi alle Trasparenze che la riguardano?
54. Il **foglio Excel della Trasparenza** ha due posizioni (WINDTRE: etichette dalla colonna A; Very: dalla colonna B) e nomi di foglio diversi. Sono ammessi entrambi da AGCOM o uno è un errore?
55. **Valori composti con "/"** nelle celle (quattro valori per lo scatto alla risposta; due per le offerte convergenti): le regole del Vademecum definiscono l'ordine e il formato? E come si trattano formati numerici misti (punto e virgola) e unità diverse (Mbps e Gbps)?
56. Perché alcune Trasparenze con **data di fine nel passato** conservano il codice e non lo stato "Chiusa"? Come e quando si registra la chiusura?
57. Per le Trasparenze **Microbusiness** ferme a "Nuova" da anni: il codice AGCOM viene comunque assegnato e semplicemente non registrato, oppure viene assegnato solo in caso di modifica?
58. Il **riferimento incrociato tra segmenti** (es. canone fisso convergente indicato nella Sintesi del mobile e in quella del fisso, con 24,99 e 25,99): chi è il titolare del dato e come si garantisce l'allineamento?
59. I **numeri di nota** nelle etichette e nei testi ("(1)", "(2)", "(3/4)") sono assegnati a mano? Devono rimanere progressivi per documento?
60. I **segnaposto residui** ("XX", "XXX", "$Nome POPZ$", "link al sito …") sono errori da bloccare in generazione o convenzioni di lavoro?
61. **Titolo del documento e testo alternativo**: chi è responsabile di inserirli (template o utente)? Il testo alternativo del bollino deve derivare dalla tecnologia?
62. La Trasparenza **Mobile CB** protetta da password: quali altre Trasparenze o template sono protetti, e chi detiene le password? (Ho potuto leggere 11 Trasparenze su 12.)
63. Manca un campione per **Fisso GA e Cross Selling Consumer** (e la sigla "CR" nelle cartelle coincide con "CS"?). Può essere fornito?

---

## 14. Documenti da acquisire per completare il quadro

1. Vademecum AGCOM (PDF) e "Schema Vademecum.xlsx".
2. "Scheda trasparenza tariffaria vuota.xlsx" con la mappatura dei campi collegati e dei valori ammissibili, e le risposte ai dubbi in giallo.
3. "Azioni massive PRECONTRATTI FISSO all.xlsx" (e l'equivalente Mobile, se esiste) e "Confronti tabelle mkt FISSO.xlsx".
4. Le macro Excel dei gruppi Fisso e Mobile (per capire come gli utenti lavorano davvero).
5. Il template Word proposto per le Sintesi del Fisso e le immagini delle tabelle del REQ.
6. La proposta di File System e il formato CSV di Adobe.
7. Esempi reali di Sintesi e Trasparenze per segmento, in particolare per verificare i sinonimi nelle etichette. *(v0.2: ricevuto un campione di 32 file; mancano Fisso GA/CS Consumer, le Trasparenze di Mobile GA Consumer e Fisso CB Consumer, e la Trasparenza Mobile CB protetta da password. Sarebbe utile anche un campione più ampio per segmento, per misurare la variabilità delle etichette.)*
8. Le **coppie complete** Sintesi–Trasparenza della stessa offerta (stesso nome commerciale e stessa data), per verificare la coerenza tra i due documenti.
9. I **PDF finali** attualmente pubblicati (Sintesi e Trasparenze), per verificare accessibilità, nomi file reali e aspetto grafico dei bollini.
10. Il **modello AGCOM dell'Excel** in bianco, per capire se la griglia ha posizioni obbligatorie e quali valori sono ammessi per ciascun campo.

---

## Appendice. Glossario minimo

- **AGCOM**: Autorità per le Garanzie nelle Comunicazioni.
- **Sintesi Contrattuale**: documento per il cliente con le condizioni dell'offerta (Word e PDF).
- **Trasparenza Tariffaria**: scheda Excel con struttura imposta da AGCOM (più PDF per i siti).
- **Vademecum AGCOM**: regole di compilazione dell'Excel della Trasparenza.
- **Padre / Figlio**: voce principale e sotto-voci di una tabella.
- **Tabella dinamica**: tabella creata dall'utente con nome, padri e figli, senza schema predefinito.
- **Bollino**: icona colorata che identifica la tecnologia di rete.
- **Canvas / canvass**: cicli di revisione commerciale, 3-4 l'anno.
- **PO**: codice tecnico dell'offerta Very Mobile.
- **Adobe**: sistema di caricamento dei PDF delle sintesi su e-commerce e punti vendita.
- **MVP**: prototipo già sviluppato, con modello dati su Cloud Spanner.
- **CAMP**: campione di 32 file reali (20 Sintesi, 12 Trasparenze) fornito dal cliente.
- **UUID**: identificatore di 36 caratteri (formato RFC 4122) usato da AGCOM come codice dell'offerta.
- **FTTC / FTTC Extra / FWA / FTTH**: tecnologie di rete fissa (fibra fino all'armadio, variante "Extra", accesso radio fisso, fibra fino a casa). Il significato esatto di "Extra" e "NGA" nei nomi non è definito nei documenti.
- **Easy Pay (EP)**: modalità di pagamento dell'offerta con addebito su carta o conto, richiamata nei nomi di molte offerte Mobile.
