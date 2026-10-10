# Sintesi & Trasparenze — Documento di inquadramento per la progettazione del modello dati

**Versione:** 1.0 · **Data:** 5 ottobre 2026 · **Derivato da:** Documento descrittivo v0.2 (2 ottobre 2026)
**Destinatario:** un LLM (o un progettista) che deve aiutare a definire il **modello di business e il modello dati** dell'applicazione.

---

## 0. Scopo del documento e come usarlo

Questo documento contiene **solo ciò che serve a progettare il modello dati e a risolvere i problemi di fondo** del progetto. Sono stati volutamente esclusi i dettagli che incidono sull'implementazione ma non sul modello: regole grafiche dei bollini, accessibilità del PDF, vincoli di naming dei file e di Adobe, righe massime per sezione, layout dei template, consegna dei file, stack tecnologico di dettaglio. Sono elencati alla sezione 12 perché chi progetta sappia che esistono e verranno dopo.

Il documento **non propone soluzioni**. Descrive il dominio, i dati reali, i vincoli, i problemi da risolvere (sezione 9), i casi d'uso contro cui il modello deve reggere (sezione 10) e le decisioni di business ancora aperte che condizionano il modello (sezione 11). Il compito richiesto a chi lo legge è: proporre un modello dati e di business che soddisfi tutti i casi d'uso, esplicitando per ogni scelta le ipotesi sulle decisioni ancora aperte.

**Etichette di affidabilità usate nel testo**

| Etichetta | Significato |
|---|---|
| **[CERTO]** | Requisito formale del cliente, oppure confermato in modo coerente da più fonti o dai file reali |
| **[PROBABILE]** | Emerge da una sola fonte o è l'aspettativa di un singolo referente, non una decisione |
| **[APERTO]** | Nessuna risposta, risposta non pertinente o risposte divergenti |
| **[CONTRASTO]** | Due fonti dicono cose incompatibili |
| **[INFERENZA]** | Lettura dell'autore, non scritta in nessun documento: da verificare |
| **[CAMPIONE]** | Osservato in un campione di 32 file reali del cliente (20 Sintesi Word, 12 Trasparenze Excel; 11 leggibili): non rappresentativo in senso statistico |

---

## 1. Il progetto in una pagina

Un operatore telefonico (WINDTRE, più il marchio Very Mobile) deve produrre, per ogni offerta commerciale, due documenti regolamentari:

- la **Sintesi Contrattuale** (documento per il cliente, Word e poi PDF), organizzata in sezioni e **tabelle padre/figlio**;
- la **Trasparenza Tariffaria** (scheda **Excel con struttura rigida imposta da AGCOM**, più un PDF).

Oggi questi documenti sono file sparsi sui PC delle persone del marketing; ogni modifica comune a molte offerte va rifatta a mano su ciascun file, con errori frequenti.

Si vuole una **web app** in cui il marketing inserisce **una sola volta** i dati di un'offerta in un database centrale e da lì genera Sintesi e Trasparenze. Il requisito più enfatizzato è la **modifica massiva**: cambiare un valore una volta e propagarlo a tutte le offerte (o a un sottoinsieme) interessate, per Sintesi, Trasparenze o entrambe.

**Il nodo centrale:** le Sintesi contengono tabelle la cui struttura varia da offerta a offerta (e che l'MVP salva come JSON senza schema), mentre le modifiche massive e la storicizzazione richiedono che i dati siano **comparabili tra offerte e nel tempo**. Libertà di struttura e capacità di operare in massa sono in tensione. Il progetto deve risolvere questa tensione e definire cosa si storicizza.

Esiste già un **MVP** (modello dati su Cloud Spanner, dialetto PostgreSQL) che gestisce un sottoinsieme di campi e tabelle dinamiche JSON. I suoi limiti sono alla sezione 8.

---

## 2. Utenti e perimetro

Gli utenti sono circa venti persone del **marketing**, non tecniche, divise in **nove gruppi** (segmenti) [CERTO]:

| # | Segmento |
|---|---|
| 1 | Mobile GA Consumer |
| 2 | Mobile CB Consumer |
| 3 | Mobile GA Microbusiness |
| 4 | Fisso GA e Cross Selling Consumer |
| 5 | Fisso CB Consumer |
| 6 | Fisso GA e Cross Selling Microbusiness |
| 7 | Fisso CB Microbusiness |
| 8 | Etnico Consumer GA/CB |
| 9 | Very Mobile (struttura simile ma non identica a WINDTRE) |

Il segmento Mobile CB Microbusiness non è impattato. Sigle (interpretazioni probabili, non confermate): GA = acquisizione nuova clientela, CB = base clienti esistente, CNS/MB = Consumer/Microbusiness, CS (o CR) = Cross Selling.

**Permessi.** Ogni utente può **modificare** solo documenti del proprio segmento [CERTO]. Gli utenti hanno chiesto di poter **vedere** anche gli altri segmenti, modificando solo il proprio [PROBABILE]. Esistono campi **comuni a tutti i segmenti** (coefficiente RDA, condizioni della convergenza mobile–luce–gas) che vengono aggiornati in simultanea: chi può modificarli, se ognuno è titolare solo del proprio segmento, è [APERTO].

**Ritmo delle modifiche.** Le modifiche commerciali sono pianificate (*canvas*, 3-4 volte l'anno) e producono molte Sintesi e Trasparenze insieme; quelle regolamentari dipendono da delibere esterne e sono imprevedibili [CERTO].

---

## 3. I due documenti e cosa serve sapere per il modello

### 3.1 Sintesi Contrattuale

È un documento a sezioni. Ogni sezione contiene **tabelle** e, spesso, **campi di testo libero** (note, condizioni, sezioni strutturate), anche lunghi [CERTO]. Alcune sezioni/testi sono comuni a tutte le offerte, altre variano.

- **Fisso/variabile.** Concordato nel requisito: "i soli elementi fissi sono etichette e titoli; tutti gli altri campi sono variabili, con frequenze diverse" [CERTO].
- **Data.** Nei campioni la Sintesi ha una data di **disponibilità** (inizio) e la frase fissa "valida fino alla chiusura in sottoscrivibilità", **mai una data di fine** [CAMPIONE].
- **Stato e codice AGCOM non compaiono** in nessuna delle 20 Sintesi del campione [CAMPIONE]: sono attributi della Trasparenza.
- **Tecnologia di rete.** Compare nella Sintesi e determina un'immagine (bollino) associata automaticamente. Il dettaglio grafico è fuori scopo; conta che **la tecnologia è un attributo dell'offerta da cui discendono contenuti** (la sua modifica deve poter essere massiva).

### 3.2 Trasparenza Tariffaria

Scheda Excel con **griglia fissa di circa 45 righe con etichette identiche** per tutte le offerte, più una zona di **note libere** [CAMPIONE]. Il formato non è negoziabile [CERTO]. La griglia contiene, in ordine: operatore, stato (o codice), date di inizio e fine sottoscrivibilità, territorio, nome commerciale, tipologia (piano base oppure opzione/bundle), piani base compatibili, pagina web, mercato, modalità di pagamento, target clientela, tecnologia, velocità download/upload, prezzi di attivazione per target (già clienti, nuovi nativi, nuovi in portabilità) in due colonne ("a listino" / "in promozione"), durata promozione, costo di disattivazione, durata minima, costo di recesso, prezzi ricorrenti e a consumo (a regime / in promozione), servizi inclusi (minuti, SMS, GB).

Caratteristiche rilevanti per il modello:

- **Valori composti con separatore "/"** a significato posizionale (es. scatto alla risposta: 4 valori; offerte convergenti: primo valore fisso, secondo mobile).
- **Convenzioni di assenza**: "-" ≠ "ND" ≠ vuoto.
- **Vocabolari non controllati** (tecnologia, target, tipologia con varianti di maiuscole e spazi) e formati misti (39,99 / 39.99; Mbps / Gbps; date vere o testo).
- **Note**: una parte finale ricorrente e una parte iniziale specifica dell'offerta. Gli utenti del Fisso chiedono di tenerle separate; la decisione registrata è "una sola nota nel DB" [CONTRASTO].
- Per Very la stessa griglia è **spostata di una colonna** e il foglio ha nome diverso [CAMPIONE].
- **IVA**: dipende dal segmento (Consumer inclusa, Microbusiness esclusa) [CAMPIONE].

### 3.3 Il rapporto tra i due documenti

- Sono **documenti distinti** con contenuti e **cicli di vita non allineati**: una modifica all'uno non impatta necessariamente l'altro; molti aggiornamenti toccano solo la Sintesi [CERTO]. Il sistema deve poterli generare separatamente.
- Condividono però molti **dati duplicati** (prezzo, costo di attivazione, durata, velocità, tecnologia, nome): nella Sintesi sono celle o frasi, nella Trasparenza celle strutturate. Nel campione le due versioni a volte **divergono** (velocità 1600 Mbps in Trasparenza e 2,0 Gbps nella Sintesi dello stesso prodotto; prezzi diversi per lo stesso nome commerciale) [CAMPIONE].
- Come i campi delle tabelle della Sintesi alimentino i campi della griglia della Trasparenza (mappatura) non è documentato [APERTO]. È una questione di modello: serve una **fonte unica** per i dati comuni o due rappresentazioni indipendenti?
- Le coppie Sintesi–Trasparenza non si corrispondono uno a uno nei campioni (spesso c'è l'una senza l'altra) [CAMPIONE].

---

## 4. Modello concettuale emerso: entità e granularità

Le entità di dominio individuabili dai materiali sono le seguenti. Non è un modello dati, ma l'elenco dei concetti che il modello deve esprimere.

| Concetto | Descrizione | Stato di conoscenza |
|---|---|---|
| **Segmento** | Uno dei nove gruppi; porta permessi, regime IVA, struttura documentale | [CERTO] |
| **Offerta** | L'oggetto commerciale; **l'unità esatta non è definita** (sezione 4.1) | [APERTO] |
| **Punto prezzo** | Variante di prezzo di un'offerta (nuovi clienti, convergente col mobile, seconda linea, …); termine mai definito dal cliente | [APERTO] |
| **Tecnologia** | Attributo dell'offerta con bollino associato e velocità; nel Fisso compare nel nome | [CERTO] (la velocità non dipende dalla sola tecnologia, vedi 4.3) |
| **Opzione collegata** | Servizio aggiuntivo associato a un'offerta (Reload Forever, Più Sicuri Mobile, …) con proprie descrizioni/prezzi | [CAMPIONE] |
| **Sintesi** | Documento per il cliente generato da un'offerta | [CERTO] |
| **Trasparenza** | Scheda AGCOM con proprio codice, stato, date | [CERTO] |
| **Codice AGCOM** | UUID di 36 caratteri assegnato da AGCOM entro ~10 giorni dal caricamento; scritto nella cella "Stato dell'offerta" | [CERTO] (formato e posizione nel campione) |
| **Tabella** (con padri e figli) | Struttura dei dati della Sintesi (sezione 5) | [CERTO] |
| **Campo scalare** | Valore singolo dell'offerta (nome, tecnologia, prezzo base, costo di attivazione, date, …) | [CERTO] |
| **Testo libero / blocco comune** | Note e paragrafi, spesso ripetuti identici (o quasi) in molti documenti | [CAMPIONE] |
| **Caratteristica trasversale / cluster** | Gruppi di offerte che condividono un attributo (assicurazione, Netflix/Amazon, cluster Giga finiti/shaped/illimitati) | [APERTO] |
| **Documento generato** | File prodotti (Sintesi Word/PDF, Trasparenza Excel/PDF), con versioni | [CERTO] come output |
| **Registro di audit** | Traccia di ogni operazione degli utenti | [CERTO] |
| **Configurazione globale** | Parametri comuni (es. coefficiente RDA) | [CERTO] come esigenza |

### 4.1 Quale è l'unità "offerta"? (problema radice)

Nessun documento la definisce. I dati mostrano che Sintesi e Trasparenza usano granularità diverse e nessuna coincide con il nome commerciale:

- **La Sintesi** ha nome, tecnologia e prezzo propri, ma una singola Sintesi può contenere **più punti prezzo** ("nuovi clienti 31,99", "con utenza mobile abbinata 25,99", "seconda linea +10"); due Sintesi Fisso CB Consumer sono identiche tranne il costo di attivazione (1,99 per 24 mesi contro 2,00 per 12 mesi); le Sintesi FTTC e FTTC Extra dello stesso prodotto sono praticamente identiche nel testo e usano la stessa immagine [CAMPIONE].
- **La Trasparenza**, nella maggior parte dei segmenti, è **una per ogni combinazione offerta–punto prezzo**, ciascuna con il proprio codice [CERTO]. Eccezione: **Mobile CB Consumer** raggruppa le offerte per tipologia e riporta solo il punto prezzo più alto con un unico codice [PROBABILE]; il requisito si contraddice altrove ("si producono tutti gli output per punto prezzo e si sceglie il più alto") [CONTRASTO]. Nell'Etnico due Trasparenze distinte (due codici) differiscono per target, attivazione e prezzo [CAMPIONE].
- **Il nome commerciale non identifica l'offerta**: "INTERNET 100 Professional" compare con canoni 29,99 e 40,99 in due documenti; la Sintesi "INTERNET 100 Full Professional" corrisponde alla Trasparenza "ABSOLUTE 100 Full Professional" con prezzi diversi [CAMPIONE]. In Very l'unico identificativo tecnico è il codice **PO**.
- Una stessa offerta potrebbe esistere in più tecnologie [APERTO]; nell'MVP ne ha una sola.

Il modello deve quindi stabilire se esistono, e come si legano, almeno: un'entità "prodotto/offerta commerciale", una "variante" (tecnologia, prezzo, target), e i due tipi di documento con le loro cardinalità (N–N tra Sintesi e Trasparenze?).

### 4.2 Tecnologia e velocità

Nell'MVP la velocità massima è attributo della tecnologia. I file reali lo contraddicono: in Very un'offerta dichiara 3G-4G-5G con 30/30 Mbps e un'altra 2000/200 Mbps; le offerte Mobile "shaped" hanno più coppie di velocità (es. 2 Gbps/200 Mbps fino a una soglia di GB, poi 10 Mbps) [CAMPIONE]. La velocità è quindi un attributo **del prodotto (e del cluster)**, non solo della tecnologia.

### 4.3 Cluster e caratteristiche trasversali

Il Mobile classifica le offerte in tre cluster (**Giga finiti**, **Giga shaped**, **Giga illimitati**). Il cluster non è oggi un attributo dichiarato ma emerge dal testo e incide su velocità e testi. Dal Fisso è emersa la richiesta di modificare massivamente "tutte le offerte che condividono una caratteristica" (assicurazione, Netflix, Amazon, un tipo di copertura). Il modello oggi **non ha il concetto** di caratteristica/etichetta attribuibile a più offerte, né è chiaro chi la dichiari e se l'insieme sia chiuso o aperto [APERTO].

---

## 5. Le tabelle dinamiche (il cuore del problema)

### 5.1 Struttura logica [CERTO]

Una tabella ha un **titolo** e un insieme di **padri** (voci principali, es. "Costo mensile", "Costo di attivazione") ciascuno con **figli** (sotto-voci, es. "Già clienti", "Nuovi clienti in portabilità"). Un padre può avere valore proprio, essere solo un'intestazione, avere figli con valore, ecc. (quattro combinazioni documentate). Sotto la tabella possono esistere **note** riferite a padri o figli, con link. I figli si possono disporre affiancati o sotto. Il numero di padri/figli osservato è solo un massimo: **il modello non deve blindare** la possibilità di aggiungere righe o voci [CERTO].

Regole di valore: "ND" → in output "Non applicabile"; valore vuoto → la riga **non compare** [CERTO come accordo]. Nei file reali Mobile e Very scrivono "ND" letterale (Very: 18 celle per documento), il Fisso "Non applicabile", e si usa anche "-" [CAMPIONE]; la regola su quando un valore è ND e quando è vuoto è [APERTO].

### 5.2 Tre forme fisiche dello stesso schema [CAMPIONE]

| Segmento | Colonne | Esempio |
|---|---|---|
| Fisso | 1 | righe alternate: etichetta, poi valore ("Traffico internet" / "Illimitato") |
| Mobile, Etnico | 2 | intestazione del padre senza valore ("Costo mensile (salvo eventuali promozioni)"), poi "Già clienti \| …" |
| Very | 3 | il padre è ripetuto in ogni riga: "Costo ricorsivo (al lordo di eventuali promozioni) \| Già clienti \| ND" |

Lo schema logico (padre → figli → valore) è lo stesso; le forme fisiche sono presentazione. Per il modello conta che l'identità di una voce non può dipendere dalla forma di rendering.

### 5.3 Variabilità

- **Tabelle fisse e tabelle dinamiche.** Nell'MVP alcune tabelle sono predefinite nel template (struttura e voci note), altre sono create dall'utente con titolo, padri e figli. Nel Fisso alcune tabelle sono identiche in tutti i segmenti ("Servizio/i e apparecchiature", "Velocità", "Durata, rinnovo e risoluzione"), altre variano ("Prezzo", "Costi"). Nel Mobile quasi tutte differiscono leggermente tra segmenti [PROBABILE].
- **Presenza variabile.** La presenza stessa di una tabella cambia da offerta a offerta nello stesso segmento (tabella "Daily Pass" solo in alcune offerte; tabella "Costi" ripetuta due o tre volte nel Fisso; coppie di tabelle "Descrizione/Prezzi" ripetute per ogni **opzione collegata** nel Mobile CB: una Sintesi ne ha dieci, un'altra nove) [CAMPIONE].
- **Stessa informazione, forme diverse.** Gli stessi servizi aggiuntivi (Reload Forever, Più Sicuri Mobile) sono una tabella nel Mobile CB, un blocco titolo+testo nel Mobile GA e nell'Etnico, una voce di costo nel Fisso [CAMPIONE]. Il contenuto della sezione "Servizi aggiuntivi" non ha forma stabile.
- **Titoli non uniformi** tra segmenti per gli stessi contenuti ("Servizi a pagamento" / "Servizi non inclusi" / assorbiti in "Costi"; "Prezzo" / "Prezzi"; "Servizio/i e apparecchiature" / "Descrizione Offerta"). Si è proposto di dare un titolo a tutte le tabelle; l'ultima parola è dell'area regolamentare [APERTO].

### 5.4 Le etichette

L'MVP identifica le voci per **posizione** nei template (`parent_0_label`, `child_0_1_value`): la posizione non esprime il significato. Il BRIEF teme che operatori diversi chiamino lo stesso concetto in modo diverso ("velocità massima download" / "velocità massima scaricamento"). Nei file reali:

- Per il solo padre della velocità massima esistono **cinque formulazioni** ("Velocità massimo di connessione Internet" [sic, maschile] / "Velocità massima di connessione Internet" / "Velocità di connessione Internet massima stimata (n)" con n variabile da 1 a 4 / la stessa con aggiunta "(4) 200 Giga Full Speed" o "(3) Giga illimitati" / "…massima stimata(2)" minuscolo e senza spazio in Very) [CAMPIONE].
- Altri casi: "Costo disattivazione servizio" / "Costo disattivazione anticipata del servizio" / "Costo disattivazione"; "Eventuali sconti e loro durata" / "Eventuali scontistiche e loro durata"; il prezzo ricorrente è "Costo mensile (salvo eventuali promozioni)", "Costo mensile", "Costo ricorsivo (al lordo di eventuali promozioni)" o "Costo canone del servizio, salvo sconto canone dedicato".
- **Dentro lo stesso segmento le etichette sono molto stabili** (otto Sintesi Fisso Microbusiness con la stessa formulazione); la divergenza segue per lo più il confine di segmento/mercato [CAMPIONE; campione piccolo].
- L'etichetta **incorpora a volte riferimenti** (numero di nota variabile) **e informazioni commerciali** (indicazione del cluster): non è un puro nome.

L'esempio dei sinonimi *dentro* uno stesso segmento non è stato osservato nel campione; non è però escluso su un campione più ampio. Un censimento delle occorrenze dei campi delle Sintesi del Fisso, citato nelle email, non è stato fornito [APERTO].

---

## 6. Dove vivono i valori: ridondanza e relazioni

Il campione mostra che un "campo" non coincide con una cella: **lo stesso valore è sparso in più punti** dello stesso e di altri documenti. Questo ha un effetto diretto sia sul modello sia sulle modifiche massive.

**Tre posizioni possibili di un valore.**

1. **Scalare dell'offerta** (nome, tecnologia, prezzo base, costo di attivazione, date, codice).
2. **Dentro una cella di tabella dinamica** (costo SIM, SMS extra soglia, penali, durate).
3. **Dentro testo libero** (frasi che citano prezzi, rate, durate, riferimenti normativi).

**Ripetizione dello stesso valore.** Nella Sintesi Fisso "Professional" il prezzo 31,99 compare in tre blocchi (cella Prezzo e due paragrafi), la rata del modem 5,99 in tre, il costo di attivazione 1,99 in due. Nell'Etnico "Unlimited Full" il costo di attivazione 49,99 e la rata 2,08 compaiono in tre blocchi ciascuno. A questi si aggiungono il nome file e, nella Trasparenza, la cella strutturata e la nota testuale (es. "49.99" nella cella e "49,99" nella nota) [CAMPIONE].

**Relazioni aritmetiche tra campi.** Il prezzo totale è dichiarato nel testo come somma di componenti: "31,99 euro è composto, per i primi 48 mesi, da: 21 euro di canone, 5 euro di chiamate illimitate e 5,99 euro di rata del modem". Le somme tornano in tutti i casi controllati (21+5+5,99=31,99; 15+5+5,99=25,99; 19+9,99+3=31,99; 24+5,99=29,99; 30+5+5,99=40,99). Oggi la coerenza è mantenuta a mano [CAMPIONE]. Se l'utente inserisce il totale, i componenti o entrambi è [APERTO].

**Rateizzazione.** L'attivazione compare come importo totale e come rate ("49,99 euro" e "24 rate mensili di 2,08 euro") sia in tabella sia in nota [CAMPIONE].

**Valori dipendenti da altri.** Il **coefficiente RDA** (giga usabili in UE) è aggiornato annualmente in tutti i segmenti ma il valore **dipende dal canone** (7,5 GB a 4,99; 14,9 GB a 9,99; 29,8 GB a 19,99, cioè ~1,5 GB per euro [INFERENZA]; 25 GB per un'offerta Microbusiness a 12,99 IVA esclusa). Nel Mobile WINDTRE è un numero dentro un testo; in Fisso e Very è solo un link. Quindi non è un singolo valore globale (l'MVP lo modella come un valore per chiave) [CAMPIONE/CONTRASTO].

**Dipendenze tra segmenti.** La **convergenza** mobile–fisso e luce&gas compare in forme diverse in segmenti diversi (paragrafo in Mobile, blocco finale in Etnico, riga di prezzo in Fisso) e come **riferimento incrociato** tra segmenti: la Sintesi Mobile Microbusiness cita un canone fisso convergente di 24,99 euro, la Sintesi Fisso Microbusiness 25,99 (ultima modifica diversa: verosimile deriva da aggiornamento non propagato) [CAMPIONE/PROBABILE].

**Testi comuni con varianti.** Molti blocchi sono ripetuti in decine di documenti: frase introduttiva e di validità identiche in 18 Sintesi WINDTRE su 20; blocchi identici in 8-10 documenti Fisso. Ma la sezione "Modifiche" esiste in **8 varianti** su 18 documenti, "Agevolazione Economica Utenti Disabili" in 4 varianti su 10, il testo sul recesso del Fisso in 3 varianti su 10. Non è noto se le varianti siano volute (per segmento/mercato) o residui di propagazione manuale [CAMPIONE/APERTO]. Valori e riferimenti ricorrenti candidati a gestione centralizzata: costo SIM 10 € (6 Sintesi su 20), SMS extra soglia 0,29 € (6), GIGA giornaliero 0,99 € (4), disattivazione 10 € (4); delibere AGCOM citate nel testo (290/21/CONS in 12 Sintesi, 156/23/CONS in 10, 9/23/CONS in 8); link al roaming (10 su 20, con testi segnaposto) [CAMPIONE].

**Segnaposto residui.** 6 Sintesi su 20 contengono segnaposto non sostituiti ("XX", "XXX", `$Nome POPZ$`, "link al sito Roaming Europa") [CAMPIONE]: il controllo è oggi affidato alla persona.

---

## 7. Ciclo di vita, versioni e date

### 7.1 Stati

Tre stati sulla Trasparenza, dichiarati "confermati" nel requisito [CERTO ma vedi tensioni]:

- **NUOVA:** alla creazione; l'utente scrive "Nuova" nel campo stato e la data di inizio.
- **APERTA:** all'arrivo del codice AGCOM, che l'utente inserisce; nell'Excel il valore del campo "Stato dell'offerta" **diventa il codice**. Si produce un nuovo Excel e PDF.
- **CHIUSA:** quando l'offerta non è più sottoscrivibile; l'utente scrive "Chiusa" e la data di fine; si producono nuovi file che **non sovrascrivono** quelli di APERTA.

"APERTA" non compare mai nel file AGCOM: il campo contiene "Nuova", un codice o "Chiusa". APERTA sembra uno **stato interno del sistema** [INFERENZA]. Un'altra versione (BRIEF) dice che il codice si inserisce in un campo dedicato del form e causa il passaggio automatico ad APERTA [CONTRASTO sul dove, non sul formato del file].

### 7.2 Stati usati davvero [APERTO]

Gli utenti dichiarano usi diversi: Very solo Nuova e Chiusa; Microbusiness Mobile GA e Fisso CB solo Nuova; Mobile GA Consumer non si riconosce in APERTA; per il CB, APERTA serve a tracciare le modifiche su trasparenze già in linea. Nel campione: su 11 Trasparenze, 8 "Nuova", 3 con codice, **nessuna "Chiusa"**; "Nuova" dura **anni** (offerte del 2021, 2022, 2023 ancora "Nuova"); due Trasparenze Etnico hanno data di fine nel passato (1/2/2026) ma stato = codice, non "Chiusa" [CAMPIONE]. Come e quando si registra la chiusura è [APERTO].

### 7.3 Le tre tensioni che il modello deve sciogliere

1. **Modifica sul posto o nuova versione?** Il requisito dice che alla chiusura "per la nuova offerta si genera un nuovo record con stato 'nuova'", chiede la **duplicazione** di offerte e un naming coerente tra "versione chiusa e nuova"; per il Mobile CB la modifica del punto prezzo più alto chiude la trasparenza e ne apre un'altra. Le risposte alle email vanno invece verso la **modifica sul posto anche dopo il codice** ("direi di sì"; "non porre troppi vincoli"). I due modelli non sono equivalenti e le fonti non scelgono [APERTO/CONTRASTO].
2. **Cosa significa CHIUSA.** Nel requisito: non più **sottoscrivibile** (fatto commerciale). In email/BRIEF: non più **modificabile** (blocco di sistema). Un'offerta non sottoscrivibile può avere clienti attivi, e modifiche regolamentari (RDA, convergenza, riferimenti normativi) potrebbero doverla comunque raggiungere [APERTO]. Aspettativa di un referente: "la modifica massiva si applica alle offerte non chiuse; le chiuse non sono più editabili" [PROBABILE].
3. **Riapertura / correzione di una chiusura:** nessun documento ne parla [APERTO].

### 7.4 Quattro file

Gli utenti vogliono entrambi i file (Excel e PDF) sia prima che dopo il codice, senza sovrascrivere ("quattro file") [CERTO come richiesta]; con la chiusura se ne aggiungono altri due. Non è detto che la regola valga anche per la Sintesi [APERTO]. Per il modello: i documenti generati sono **eventi/versioni immutabili legati a uno stato**, non un campo sovrascrivibile.

### 7.5 Date

Il modello MVP ha un solo intervallo di validità per offerta. Dalle email: la validità della Sintesi **non coincide** con quella della Trasparenza [CERTO come esigenza]. Nel campione la Sintesi ha solo "disponibilità/inizio" (e una frase fissa), la Trasparenza ha inizio e fine sottoscrivibilità. Le date nei nomi file sono la data di produzione, non quella di inizio [CAMPIONE/INFERENZA].

---

## 8. Stato dell'MVP e scarti dal modello

L'MVP (documentazione "Database design", quattro versioni in sequenza: originale a 7 tabelle, NEW, NEW 2, NEW 3 — quella in uso non è indicata [CONTRASTO]) prevede: segmenti, utenti, ruoli per segmento (viewer/editor/admin), tecnologie (con bollino e velocità massime), modalità di pagamento, offerte, costi di attivazione per tipo di cliente (tre target), **tabelle dinamiche** (identificatore tra Prezzo/Costi/Servizi, titolo, contenuto JSON, note), **storico dei cambi di stato**, **snapshot delle tabelle congelati a ogni cambio di stato**, documenti (tipo, versione, flag corrente), configurazioni globali. Funzioni: creare offerte con campi fissi e tabelle dinamiche, generare Sintesi/Trasparenze da template con segnaposto (posizionali, in due layout), sostituire i bollini per tecnologia, modifica massiva su un **sottoinsieme di campi** con avviso del numero di offerte coinvolte.

**Vincoli tecnici già presenti (scelte di progetto, non requisiti del cliente):** Cloud Spanner (dialetto PostgreSQL), applicazione FastAPI/SQLAlchemy, chiavi UUIDv4 generate dall'applicazione, file su Cloud Storage, identità tramite OIDC aziendale. L'MVP riconosce che "la libertà delle tabelle dinamiche non consente modifiche massive, perché sono personalizzate sulla singola offerta".

**Dove il modello attuale non copre quanto emerso:**

| Scarto | Dettaglio |
|---|---|
| Date | un solo intervallo di validità per offerta; servono date distinte Sintesi/Trasparenza |
| Codici AGCOM | un solo codice corrente per offerta; servono più Trasparenze (una per offerta–punto prezzo), ognuna col suo codice |
| Prezzo | un solo prezzo base; esistono più punti prezzo, e il prezzo è somma di componenti |
| Velocità | solo funzione della tecnologia; non copre cluster shaped né Very |
| Tecnologia | una sola per offerta (NEW 3); da chiarire se un'offerta può averne più |
| Campi liberi | nessuna collocazione esplicita se non la nota; testi lunghi e blocchi comuni non modellati |
| Caratteristiche trasversali | concetto assente |
| RDA | un valore per chiave globale; il valore dipende dal canone |
| Storico | solo transizioni di stato; nessun log di tutte le modifiche, né delle massive, né delle cancellazioni (solo eliminazione logica) |
| Documenti | tipo `TEMPLATE_DOCX/XLSX` ambiguo (template o file compilato?); mancano tipi per Sintesi/Trasparenza generate |
| Copertura Trasparenza | non hanno corrispondenza nel DB: colonne "in promozione", durata promozione, costo di recesso, tipologia (piano base/opzione), piani compatibili, territorio, intero blocco servizi inclusi [INFERENZA sulle sole tabelle descritte] |

---

## 9. I problemi da risolvere

Sono i problemi di progetto in ordine di impatto sul modello. Per ognuno: cosa è difficile, quali vincoli noti, quali dati reali lo illustrano. Non sono indicate soluzioni.

**P1 — Unità di gestione.** Definire cosa è un'"offerta" e come si legano offerta, variante/punto prezzo, tecnologia, Sintesi e Trasparenze (sezione 4.1). Da questo dipendono chiavi, cardinalità, stati (su quale entità vive lo stato?), codici AGCOM multipli, naming, generazione e modifiche massive.

**P2 — Rappresentare le tabelle dinamiche in modo comparabile.** Le tabelle non hanno schema, ma devono potersi interrogare e modificare in massa. Occorre decidere cosa è l'**identità di una voce** (padre/figlio) indipendentemente da posizione, etichetta visibile, numero di nota, forma fisica (1/2/3 colonne) e segmento. Vincoli: non blindare righe/voci; nuove tabelle e voci senza sviluppo; presenza variabile di tabelle per offerta; tabelle ripetute per opzione collegata; stesse informazioni in forme diverse tra segmenti. Fatto rilevante: dentro un segmento le etichette sono stabili, tra segmenti no; l'etichetta incorpora talvolta numero di nota e cluster.

**P3 — Storicizzazione delle tabelle dinamiche.** Stabilire cosa conservare e con quale granularità per poter ricostruire "com'era l'offerta/il documento in un dato momento": solo snapshot a ogni cambio di stato (come l'MVP), ogni singola modifica, ogni modifica massiva come evento a sé; conservazione di struttura (quali tabelle/voci esistevano) oltre che dei valori; diff tra versioni; legame tra versione dei dati e file generati; storico con contenuto a schema variabile (anche voci eliminate o rinominate). Va coordinato con P5 (in-place o nuova versione) e con l'audit richiesto su **tutte** le operazioni.

**P4 — Modifiche massive su dati senza schema.** Distinguere i tipi di modifica richiesta: sul **valore** di una voce, sul **nome/etichetta**, sulla **presenza/assenza** di una riga o tabella, sul **testo libero**. Servono: selezione delle offerte (per segmento, tecnologia, caratteristica, scelta manuale), perimetro di voci coinvolte (che può non esistere in alcune offerte o esistere con altro nome), anteprima/conteggio prima dell'applicazione (già presente nell'MVP), eventuale annullamento, tracciabilità come evento unico, effetti sui documenti già generati. Esempi: cambiare il costo SIM da 10 a un altro valore in 6 Sintesi; aggiornare un riferimento normativo; cambiare la tecnologia con relativo bollino.

**P5 — Modifica sul posto o nuova versione; significato di CHIUSA.** Le due strategie hanno ricadute opposte su chiavi, storico, naming, duplicazione, modifiche massive (che versione modificano? solo le non chiuse?) e sui quattro/sei file (sezione 7.3). Servono ipotesi esplicite e un modello che non si rompa se la decisione cambia.

**P6 — Valori ridondanti e derivati.** Lo stesso valore vive in più posizioni (scalare, cella, frase, nota, nome file, Trasparenza) e alcuni valori sono somme di altri (sezione 6). Il modello deve stabilire se esiste una **fonte unica** per i dati comuni a Sintesi e Trasparenza, come i testi li citano (riferimenti ai valori invece di copie?), se i totali sono calcolati, e come gestire valori incorporati nel testo libero in modo che una modifica massiva non lasci incoerenze.

**P7 — Testi comuni con varianti.** Molti blocchi sono quasi identici con varianti non spiegate. Occorre stabilire il rapporto tra testo "di catalogo" condiviso e personalizzazione per segmento/offerta/mercato, e come si modifica "in massa" un testo che non è identico ovunque (sezione 6).

**P8 — Attributi dipendenti e dimensionali.** RDA in funzione del canone; velocità in funzione di cluster e soglie; punti prezzo; target (già clienti, nuovi nativi, portabilità) × prezzi "a listino/in promozione". Sono valori che dipendono da altri valori o da più dimensioni e non stanno bene né in un singolo scalare né in una tabella piatta.

**P9 — Raggruppamenti trasversali.** Caratteristiche trasversali, cluster Mobile e opzioni collegate (Reload Forever, Più Sicuri Mobile, assicurazione, Netflix/Amazon) come criteri di selezione per le modifiche massive e come contenuto dei documenti. Occorre capire chi li dichiara, se sono insiemi chiusi o aperti, e se sono semplici etichette o comportano contenuti propri (tabelle, voci di costo).

**P10 — Permessi nelle modifiche massive e dati condivisi tra segmenti.** Modifica solo del proprio segmento, ma campi comuni (RDA, convergenza) e riferimenti incrociati (24,99 contro 25,99). Servono titolarità del dato, ruolo trasversale e propagazione senza violare la segregazione. Visibilità trasversale richiesta dagli utenti.

**P11 — Doppio ciclo di vita Sintesi/Trasparenza.** Date e versioni separate, rigenerazione indipendente, documenti "superati" dopo una modifica massiva (flag? versione corrente?), coppie non allineate nel tempo.

**P12 — Vincolo del formato AGCOM rigido.** La Trasparenza ha griglia fissa con vocabolari quasi liberi e valori composti con "/"; la Sintesi ha tabelle variabili. Il modello deve garantire che i dati necessari alla griglia siano **strutturati e validabili** (UUID del codice, date, numeri, unità), pur lasciando libertà nelle tabelle della Sintesi. La mappatura Sintesi→Trasparenza è sconosciuta.

**P13 — Estensibilità.** Il database deve poter accogliere nuovi campi non previsti oggi [CERTO]. Il requisito stesso nota che la fattibilità di un unico database va verificata dopo la mappatura dei campi.

---

## 10. Casi d'uso contro cui validare il modello

Elenco derivato dai materiali (alcuni descritti esplicitamente, altri ricavati: marcati con ˆ). Un modello proposto dovrebbe essere verificato su tutti.

| # | Caso d'uso | Cosa mette alla prova |
|---|---|---|
| UC1 | Creare un'offerta Nuova con campi scalari e tabelle (anche dinamiche) e generare Sintesi, Trasparenza o entrambe | P1, P2, P12 |
| UC2 | Registrare il codice AGCOM (UUID) su una Trasparenza e passare ad APERTA, senza sovrascrivere i file precedenti | P1, P5, stati |
| UC3 | Modificare un'offerta già con codice (cambio di prezzo, tecnologia, testo) mantenendo la possibilità di ritrovare la versione precedente | P3, P5 |
| UC4 | Chiudere un'offerta (stato + data fine) e generare i nuovi file senza toccare i precedenti ˆ | P5, P11 |
| UC5 | Duplicare un'offerta, singolarmente o in blocco, per creare la nuova versione | P1, P5 |
| UC6 | Modifica massiva di un **campo scalare** (es. tecnologia, con bollino; prezzo base; costo di attivazione) su un insieme di offerte selezionate, con conteggio e conferma | P4, P6 |
| UC7 | Modifica massiva del **valore di una voce dentro una tabella dinamica** (es. costo SIM 10 € in 6 Sintesi; SMS extra soglia) quando la voce può chiamarsi in modi diversi o non esistere in alcune offerte | P2, P4 |
| UC8 | Modifica massiva che **aggiunge, rinomina o elimina una voce/tabella** in molte offerte ˆ | P2, P3, P4 |
| UC9 | Aggiornare un **testo libero comune** (es. sezione "Modifiche", riferimento a una delibera) che esiste in più varianti | P7 |
| UC10 | Aggiornamento annuale del **coefficiente RDA** in tutti i segmenti, con valore che dipende dal canone | P8, P10 |
| UC11 | Cambiare **naming/condizioni della convergenza** mobile–luce–gas, comune a più segmenti, mantenendo allineati i riferimenti incrociati (24,99 contro 25,99) | P6, P10 |
| UC12 | Modificare massivamente tutte le offerte che condividono una **caratteristica** (assicurazione, Netflix, Amazon, un tipo di copertura) o un **cluster** | P9 |
| UC13 | Mobile CB: modificare il punto prezzo più alto → chiudere la Trasparenza precedente e aprirne una nuova; modifiche sui punti inferiori non richiedono aggiornamenti | P1, P5 |
| UC14 | Una Sintesi con più punti prezzo e più Trasparenze (ognuna col proprio codice) collegate alla stessa Sintesi | P1 |
| UC15 | Offerta con **opzioni collegate** che portano proprie tabelle/prezzi (Mobile CB) o paragrafi/voci (altri segmenti) | P2, P9 |
| UC16 | Cambiare il **prezzo componente** e ottenere totale e frasi coerenti (21+5+5,99=31,99) ˆ | P6 |
| UC17 | Dopo una modifica massiva, individuare i **documenti generati superati**, rigenerare, e recuperare i file di una versione passata | P3, P11 |
| UC18 | **Audit**: chi ha creato/modificato/inserito il codice/chiuso/eliminato/eseguito una massiva; ricostruire lo stato di un'offerta a una data | P3 |
| UC19 | Un utente del segmento A **vede** le offerte del segmento B senza poterle modificare; una modifica comune a più segmenti ha un titolare | P10 |
| UC20 | **Migrazione iniziale** da Sintesi e Trasparenze esistenti (formati disomogenei, segnaposto residui, valori ridondanti) ˆ | P2, P6 |
| UC21 | Aggiungere un **nuovo campo o nuova tabella** non prevista senza sviluppo | P2, P13 |

---

## 11. Decisioni di business aperte che condizionano il modello

In ordine di impatto sul modello; dove possibile indicata la fonte per chi può rispondere (utenti del marketing, area regolamentare, cliente).

1. **Unità di gestione.** Cosa è "offerta"; cosa è "punto prezzo"; una Sintesi ↔ più Trasparenze e viceversa; più tecnologie per offerta.
2. **In-place o nuova versione**, e su quali campi (solo quelli che toccano la Trasparenza?). Significato di CHIUSA (sottoscrivibile o modificabile), possibilità di riapertura, ruolo delle chiuse nelle modifiche regolamentari.
3. **Cosa storicizzare** e con quale granularità; chi accede allo storico. Il cliente chiede una proposta con pro e contro per ciascuna opzione e non ha una preferenza espressa.
4. **Elenco puntuale dei campi per cui si vuole la modifica massiva**, segmento per segmento, con frequenza; quali sono scalari, quali dentro tabelle, quali parti di testo. È il dato più importante per il modello e non è disponibile (il file "azioni massive PRECONTRATTI FISSO all.xlsx" e l'equivalente Mobile non sono stati forniti).
5. **Tipo di modifica massiva:** sul valore, sull'etichetta, sulla presenza di una riga, oppure su tutte e tre.
6. **Etichette:** libere o da elenco condiviso; chi le decide; frequenza dei sinonimi dentro lo stesso segmento.
7. **Testi comuni:** le varianti sono volute o accidentali; quale è la versione corretta; come gestire gli override.
8. **Prezzo totale e componenti:** cosa inserisce l'utente; il totale è calcolato?
9. **Caratteristiche trasversali e cluster:** tag liberi o insieme chiuso, chi li dichiara, se contengono contenuti.
10. **Permessi:** chi esegue modifiche che attraversano più segmenti; visibilità trasversale; cancellazione di un'offerta (prevista?).
11. **Date:** quali campi e quali regole per Sintesi e Trasparenza.
12. **Stati realmente usati per segmento** (Nuova→Chiusa diretto?), e come si registra la chiusura; "quattro file" per Sintesi e Trasparenza?
13. **"ND" contro vuoto contro "-":** quando si applica ciascuno.
14. **Mobile CB:** solo punto prezzo più alto o tutti con scelta successiva?
15. **Volumi** (offerte attive, chiuse, documenti annui, utenti simultanei) e **migrazione** (tutte le offerte esistenti o solo alcune?): non esiste alcun numero.
16. **Mappatura Sintesi→Trasparenza** e valori ammissibili AGCOM (documenti "Schema Vademecum.xlsx" e "scheda trasparenza vuota" non forniti).

---

## 12. Argomenti esclusi da questo documento (rimandati alla fase di implementazione)

Esistono nei requisiti ma non incidono sul modello dati e sulla soluzione di fondo; saranno trattati dopo.

- Regole grafiche e accessibilità dei **bollini** (dimensioni, colori Pantone delibera 106/25/CONS, testo alternativo, posizione) e accessibilità del PDF (PDF/UA, titolo del documento, ordine di lettura). *Il solo aspetto rilevante per il modello — tecnologia → bollino automatico, con la tecnologia modificabile in massa — è nella sezione 3.1.*
- **Naming dei file** e vincoli **Adobe** (PDF ≤ 2 MB, nome ≤ 160 caratteri, caratteri ammessi, nomi unici), file di mappatura CSV per Adobe.
- **Righe massime** per sezione e per segmento, titoli e singolare/plurale delle tabelle, disposizione affiancata o sotto dei figli.
- **Layout dei template** Word/Excel, segnaposto e sintassi markdown/HTML nei valori.
- **Consegna** dei file (email con zip contro download), organizzazione in cartelle, durata di conservazione.
- Dettagli di **stack** e infrastruttura (Spanner, GCS, OIDC, SQLite di test) oltre a quanto indicato alla sezione 8.
- **Qualità dei dati** reali (formati misti, maiuscole, segnaposto residui), da affrontare come parte della migrazione (UC20).

---

## Appendice A. Esempi reali sintetici

**A.1 Stesso concetto in tre forme fisiche**

```
Fisso (1 colonna)         Mobile (2 colonne)                        Very (3 colonne)
------------------        ---------------------------------------   --------------------------------------------
Costo mensile             Costo mensile (salvo eventuali promoz.)   Costo ricorsivo (al lordo di ...) | Già clienti | ND
31,99 euro                  Già clienti            | 9,99 €         Costo ricorsivo (al lordo di ...) | Nuovi      | 5,99 €
```

**A.2 Etichette diverse per la stessa voce (velocità massima)**

```
Fisso Microbusiness : "Velocità massimo di connessione Internet"
Fisso CB Consumer   : "Velocità massima di connessione Internet"
Mobile/Etnico       : "Velocità di connessione Internet massima stimata (1..4)"
Etnico (cluster)    : "…massima stimata (4) 200 Giga Full Speed" / "… (3) Giga illimitati"
Very                : "Velocità di connessione internet massima stimata(2)"
```

**A.3 Un valore, molte posizioni (Sintesi Fisso "Professional")**

```
Prezzo 31,99 -> cella tabella Prezzo + paragrafo "composto da..." + paragrafo condizioni + nome file + Trasparenza (cella e nota)
Totale 31,99 = canone 21 + chiamate 5 + rata modem 5,99   (la rata 5,99 compare in 3 blocchi)
```

**A.4 Esempio di valore dipendente (RDA)**

```
canone 4,99 -> 7,5 GB ; canone 9,99 -> 14,9 GB ; canone 19,99 -> 29,8 GB ; Microbusiness 12,99 (IVA escl.) -> 25 GB
```

## Appendice B. Glossario minimo

- **AGCOM:** Autorità per le Garanzie nelle Comunicazioni. **Vademecum:** regole di compilazione dell'Excel della Trasparenza (delibera 252/16/CONS).
- **Sintesi Contrattuale / Trasparenza Tariffaria:** i due documenti (sezione 3).
- **Codice AGCOM:** UUID RFC 4122 di 36 caratteri assegnato dopo il caricamento.
- **Padre / Figlio:** voce principale e sotto-voci di una tabella. **Tabella dinamica:** tabella con padri e figli senza schema predefinito (JSON nell'MVP).
- **Punto prezzo:** variante di prezzo di un'offerta (definizione non fornita dal cliente).
- **Cluster (Mobile):** Giga finiti / shaped / illimitati. **RDA:** coefficiente annuale di giga utilizzabili in UE.
- **PO:** codice tecnico dell'offerta Very Mobile. **Canvas:** cicli di revisione commerciale, 3-4 l'anno.
- **Convergenza:** offerta fissa abbinata a SIM mobile o a luce&gas, con condizioni di prezzo dedicate.
- **FTTC / FTTC Extra / FWA / FTTH:** tecnologie di rete fissa. **EP / Easy Pay:** modalità di pagamento ricorrente nei nomi di offerta.
