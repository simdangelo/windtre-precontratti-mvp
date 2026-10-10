# Un'offerta reale, passo per passo — dati concreti in ogni tabella

> Documento complementare a `database-design-v2.md`. Invece di descrivere gli scenari in astratto, seguiamo **una singola offerta immaginaria** dalla nascita alla chiusura, mostrando ad ogni passo il contenuto *reale* delle tabelle coinvolte.

---

## 0. Cosa è cambiato rispetto alla v2

**Rimossa la tabella `payment_method`.** Non avendo attributi propri collegati (a differenza di `technology`, che porta con sé bollino/velocità/network), non c'era un reale vantaggio a normalizzarla. È stata sostituita da una colonna diretta su `offer`:

```sql
ALTER TABLE offer
  ADD COLUMN payment_method varchar NOT NULL;

ALTER TABLE offer
  ADD CONSTRAINT ck_offer_payment_method
  CHECK (payment_method IN ('CREDITO_RESIDUO', 'ABBONAMENTO', 'SEPA_PA'));
```

Con questa modifica, `payment_method` diventa concettualmente identico agli altri "enum soft" già presenti nello schema (`status`, `role`, `target_type`, `doc_type`, `table_identifier`) — un dominio piccolo e stabile, vincolato da `CHECK`, senza tabella dedicata. Lo schema è quindi **più coerente al suo interno**: l'unica vera anagrafica rimasta con attributi propri è `technology`. Se in futuro un metodo di pagamento avesse bisogno di attributi propri (es. `requires_iban`), varrebbe la stessa regola generale già discussa: a quel punto ha senso tornare a una tabella.

**Cosa NON è ancora incluso in questo esempio** (decisioni ancora aperte, discusse ma non confermate — per trasparenza, così non sembra che siano state introdotte silenziosamente):
- le colonne "congelate" `frozen_max_download_mbps`/`frozen_max_upload_mbps` su `offer`;
- il controllo "tutte e 3 le sezioni (PREZZO/COSTI/SERVIZI) devono esistere prima della pubblicazione".

Questo esempio usa quindi lo schema `v2` + rimozione `payment_method`, così com'è confermato oggi.

**Nota di leggibilità**: per non riempire le tabelle di UUID illeggibili, uso identificatori mnemonici (`offer_001`, `usr_giulia`...). Nel database reale sarebbero tutti `UUIDv4`.

---

## 1. I dati di contesto (seed data, invariati per tutta la storia)

Queste righe esistono già prima che la nostra offerta venga creata, e non cambiano nel corso della storia.

**`user`**

| id | email | first_name | last_name | is_active | created_at |
|---|---|---|---|---|---|
| `usr_giulia` | giulia.rossi@verymobile.it | Giulia | Rossi | true | 2024-01-10 |
| `usr_marco` | marco.bianchi@verymobile.it | Marco | Bianchi | true | 2024-01-10 |
| `usr_paola` | paola.verdi@verymobile.it | Paola | Verdi | true | 2024-02-01 |

*Giulia è l'editor che crea e affina la bozza. Marco è l'admin che inserisce il codice AGCOM e pubblica. Paola è l'admin che, mesi dopo, chiuderà l'offerta.*

**`segment`**

| id | code | name | max_dynamic_table_rows | created_at |
|---|---|---|---|---|
| `seg_verymobile` | `VERY_MOBILE` | Very Mobile | 3 | 2024-01-01 |

**`technology`**

| id | code | network_name | badge_color | max_download_mbps | max_upload_mbps | is_active |
|---|---|---|---|---|---|---|
| `tech_ftth` | `FTTH` | Fibra Ottica GPON | `#2ECC71` | 1000 | 300 | true |

**`user_segment_role`**

| user_id | segment_id | role |
|---|---|---|
| `usr_giulia` | `seg_verymobile` | editor |
| `usr_marco` | `seg_verymobile` | admin |
| `usr_paola` | `seg_verymobile` | admin |

---

## 2. Scenario 1 — Creazione della bozza (`NUOVA`)

**01/09/2026** — Giulia crea una nuova offerta FTTH per il segmento Very Mobile, e carica subito i template di partenza. Compila per ora solo la sezione PREZZO.

**`offer`** — nuova riga

| id | segment_id | technology_id | payment_method | commercial_name | base_price | po_code | current_agcom_code | status | date_start | date_end | created_at | updated_at | deleted_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `offer_001` | `seg_verymobile` | `tech_ftth` | `ABBONAMENTO` | Very 200 Full | 9.99 | `PO-VM-2026-0456` | `NULL` | `NUOVA` | `NULL` | `NULL` | 2026-09-01 09:00 | 2026-09-01 09:00 | `NULL` |

`po_code` è valorizzato perché `segment.code = VERY_MOBILE` (§5.3 del documento v2). `date_start`/`date_end` sono ancora `NULL`: la finestra di validità commerciale non è ancora decisa.

**`offer_activation_fee`** — Giulia seleziona 2 dei 3 target possibili

| id | offer_id | target_type | price |
|---|---|---|---|
| `fee_001` | `offer_001` | `gia_clienti` | 5.00 |
| `fee_002` | `offer_001` | `nuovi_nativi` | 10.00 |

**`dynamic_table`** — solo la sezione PREZZO, per ora

| id | offer_id | table_identifier | sequence_order | title | created_at |
|---|---|---|---|---|---|
| `dt_001` | `offer_001` | `PREZZO` | 1 | Prezzo mensile | 2026-09-01 09:10 |

`dt_001.structural_content`:
```json
{
  "columns": ["Voce", "Importo"],
  "rows": [
    { "label": "Canone mensile Very 200 Full", "value": "9,99 €" }
  ]
}
```
`dt_001.note_links`: `{}` (nessuna nota ancora)

*Nota: 1 riga su un limite di 3 per il segmento VERY_MOBILE (§5.6) — ampiamente rispettato.*

**`offer_document`** — Giulia carica i template di partenza

| id | offer_id | state_history_id | doc_type | gcs_uri | version | is_current | created_by | created_at |
|---|---|---|---|---|---|---|---|---|
| `doc_001` | `offer_001` | `NULL` | `TEMPLATE_DOCX` | `gs://vm-docs/offer_001/template_sintesi_v1.docx` | 1 | true | `usr_giulia` | 2026-09-01 09:15 |
| `doc_002` | `offer_001` | `NULL` | `TEMPLATE_XLSX` | `gs://vm-docs/offer_001/template_trasparenza_v1.xlsx` | 1 | true | `usr_giulia` | 2026-09-01 09:16 |

`state_history_id` è `NULL` per entrambi: nessuna transizione di stato è ancora avvenuta (§4.2).

**Tabelle NON toccate in questo scenario**: `offer_state_history`, `dynamic_table_snapshot` — coerente con §5.2: la creazione di una bozza non è una transizione, quindi non genera nessuna riga qui. Entrambe sono ancora **vuote** per `offer_001`.

---

## 3. Scenario 2 — Modifiche e affinamento della bozza

**05/09/2026** — Giulia completa l'offerta: aggiunge uno sconto promozionale alla sezione PREZZO, crea le sezioni COSTI e SERVIZI mancanti, e — dopo un confronto col team commerciale — cambia idea su un target: toglie `nuovi_nativi` e attiva `nuovi_portabilita`. Aggiorna anche il template Word.

**`offer`** — solo `updated_at` cambia (nessun campo di business toccato in questo esempio)

| id | ... | updated_at |
|---|---|---|
| `offer_001` | *(invariato)* | 2026-09-05 14:30 |

**`offer_activation_fee`** — applicato il pattern "diff" (§ discussione precedente): si cancella solo la riga deselezionata, si inserisce solo quella nuova, `fee_001` resta intatta

| id | offer_id | target_type | price |
|---|---|---|---|
| `fee_001` | `offer_001` | `gia_clienti` | 5.00 |
| ~~`fee_002`~~ | ~~`offer_001`~~ | ~~`nuovi_nativi`~~ | *(riga cancellata)* |
| `fee_003` | `offer_001` | `nuovi_portabilita` | 15.00 |

```sql
DELETE FROM offer_activation_fee WHERE id = 'fee_002';
INSERT INTO offer_activation_fee (id, offer_id, target_type, price)
  VALUES ('fee_003', 'offer_001', 'nuovi_portabilita', 15.00);
```

**`dynamic_table`** — `dt_001` aggiornata, `dt_002` e `dt_003` create

| id | offer_id | table_identifier | sequence_order | title | updated_at |
|---|---|---|---|---|---|
| `dt_001` | `offer_001` | `PREZZO` | 1 | Prezzo mensile | 2026-09-05 14:32 |
| `dt_002` | `offer_001` | `COSTI` | 2 | Costi di attivazione | 2026-09-05 14:35 |
| `dt_003` | `offer_001` | `SERVIZI` | 3 | Servizi inclusi | 2026-09-05 14:38 |

`dt_001.structural_content` (aggiornato, aggiunta riga sconto — **2 righe, ancora sotto il limite di 3**):
```json
{
  "columns": ["Voce", "Importo"],
  "rows": [
    { "label": "Canone mensile Very 200 Full", "value": "9,99 €" },
    { "label": "Sconto promozionale primi 6 mesi", "value": "-3,00 €" }
  ]
}
```
`dt_001.note_links` (aggiornato):
```json
{
  "footnotes": [
    { "marker": "1", "text": "Lo sconto è applicato automaticamente nei primi 6 mesi di attivazione." }
  ]
}
```

`dt_002.structural_content` (nuova — **rispecchia le fee correnti, gia_clienti 5,00€ e nuovi_portabilita 15,00€**):
```json
{
  "columns": ["Voce", "Importo"],
  "rows": [
    { "label": "Attivazione clienti già Very Mobile", "value": "5,00 €" },
    { "label": "Attivazione nuovi clienti in portabilità", "value": "15,00 €" }
  ]
}
```

`dt_003.structural_content` (nuova):
```json
{
  "columns": ["Servizio incluso"],
  "rows": [
    { "label": "Modem Wi-Fi 6 in comodato d'uso" },
    { "label": "Assistenza clienti 24/7" }
  ]
}
```

> ⚠️ **Osservazione**: i valori in `dt_002` (COSTI) sono testo libero dentro un JSON — non c'è nessun vincolo di database che li tenga sincronizzati con i valori strutturati in `offer_activation_fee`. In questo esempio coincidono perché Giulia li ha aggiornati manualmente insieme, ma nulla impedisce che in futuro si disallineino (es. se aggiorna solo `offer_activation_fee` dimenticandosi di aggiornare il testo della tabella COSTI). Vale la pena segnalarlo come possibile punto di attenzione.

**`offer_document`** — Giulia carica una nuova versione del template Word; l'Excel resta quello iniziale

| id | offer_id | state_history_id | doc_type | version | is_current | created_by | created_at |
|---|---|---|---|---|---|---|---|
| `doc_001` | `offer_001` | `NULL` | `TEMPLATE_DOCX` | 1 | **false** | `usr_giulia` | 2026-09-01 09:15 |
| `doc_002` | `offer_001` | `NULL` | `TEMPLATE_XLSX` | 1 | true | `usr_giulia` | 2026-09-01 09:16 |
| `doc_003` | `offer_001` | `NULL` | `TEMPLATE_DOCX` | **2** | **true** | `usr_giulia` | 2026-09-05 14:40 |

`doc_001` passa a `is_current = false` nello stesso momento in cui `doc_003` viene inserita — questo è esattamente ciò che l'indice unique parziale di §4.1 garantisce: non può mai esistere più di un `TEMPLATE_DOCX` corrente per la stessa offerta.

**Tabelle NON toccate**: `offer_state_history`, `dynamic_table_snapshot` restano vuote — nessuna transizione di stato è ancora avvenuta, quindi nessuna fotografia viene scattata. Tutto ciò che abbiamo appena visto (lo sconto aggiunto, il target cambiato) **non è tracciato in nessun audit trail** — è esattamente il punto della Domanda aperta §6.2 del documento precedente.

---

## 4. Scenario 3 — Pubblicazione (`NUOVA → APERTA`)

**22/09/2026, ore 10:14** — Tre settimane dopo la creazione, arriva il codice AGCOM. Marco lo inserisce nel sistema.

**`offer`** — l'`UPDATE` di Marco innesca il trigger `trg_auto_publish`, che aggiorna `status` nella stessa operazione

| campo | prima | dopo |
|---|---|---|
| `current_agcom_code` | `NULL` | `AG23091501` |
| `status` | `NUOVA` | `APERTA` |
| `date_start` | `NULL` | `2026-09-22` *(valorizzato contestualmente alla pubblicazione)* |
| `updated_at` | 2026-09-05 14:40 | 2026-09-22 10:14 |

*(tutti gli altri campi restano invariati rispetto allo Scenario 2)*

**`offer_state_history`** — creata automaticamente dal trigger, insieme all'`UPDATE` sopra

| id | offer_id | old_status | new_status | agcom_code_used | changed_by | timestamp |
|---|---|---|---|---|---|---|
| `hist_001` | `offer_001` | `NUOVA` | `APERTA` | `AG23091501` | `usr_marco` | 2026-09-22 10:14 |

**`dynamic_table_snapshot`** — creata a cascata dall'`INSERT` sopra (§5.2, cardinalità 1:1 obbligatoria)

| id | state_history_id | created_at |
|---|---|---|
| `snap_001` | `hist_001` | 2026-09-22 10:14 |

`snap_001.tables_payload` — copia congelata **esatta** di `dt_001`, `dt_002`, `dt_003` così come si presentavano in questo istante (identici ai valori mostrati a fine Scenario 2):
```json
[
  {
    "id": "dt_001", "table_identifier": "PREZZO",
    "structural_content": {
      "columns": ["Voce", "Importo"],
      "rows": [
        { "label": "Canone mensile Very 200 Full", "value": "9,99 €" },
        { "label": "Sconto promozionale primi 6 mesi", "value": "-3,00 €" }
      ]
    }
  },
  {
    "id": "dt_002", "table_identifier": "COSTI",
    "structural_content": {
      "columns": ["Voce", "Importo"],
      "rows": [
        { "label": "Attivazione clienti già Very Mobile", "value": "5,00 €" },
        { "label": "Attivazione nuovi clienti in portabilità", "value": "15,00 €" }
      ]
    }
  },
  {
    "id": "dt_003", "table_identifier": "SERVIZI",
    "structural_content": {
      "columns": ["Servizio incluso"],
      "rows": [
        { "label": "Modem Wi-Fi 6 in comodato d'uso" },
        { "label": "Assistenza clienti 24/7" }
      ]
    }
  }
]
```

**Da qui in poi**, anche se qualcuno modificasse `dt_001`/`dt_002`/`dt_003` in futuro (se l'offerta lo permettesse — §6.3), `snap_001` **non cambierà mai**: è la prova immutabile di cosa era pubblicato in questo istante.

**`offer_document`** — ora che `status = APERTA`, il sistema genera i documenti pubblici

| id | offer_id | state_history_id | doc_type | version | is_current | created_by | created_at |
|---|---|---|---|---|---|---|---|
| `doc_004` | `offer_001` | `hist_001` | `SINTESI_PDF` | 1 | true | `usr_marco` | 2026-09-22 10:15 |
| `doc_005` | `offer_001` | `hist_001` | `TRASPARENZA_PDF` | 1 | true | `usr_marco` | 2026-09-22 10:15 |

Questa volta `state_history_id` **è** valorizzato — questi documenti nascono legati a una precisa transizione (§5.5), a differenza dei template caricati in bozza. La FK composita di §4.2 verifica che `offer_id = 'offer_001'` combaci con l'`offer_id` di `hist_001` — combacia, quindi l'inserimento è valido.

---

## 5. Scenario 4 — Chiusura (`APERTA → CHIUSA`)

**15/01/2027, ore 09:00** — Quattro mesi dopo, Paola chiude l'offerta (sostituita da una nuova campagna).

**`offer`**

| campo | prima | dopo |
|---|---|---|
| `status` | `APERTA` | `CHIUSA` |
| `date_end` | `NULL` | `2027-01-15` *(valorizzata contestualmente alla chiusura)* |
| `updated_at` | 2026-09-22 10:14 | 2027-01-15 09:00 |

**`offer_state_history`** — nuova riga

| id | offer_id | old_status | new_status | agcom_code_used | changed_by | timestamp |
|---|---|---|---|---|---|---|
| `hist_001` | `offer_001` | `NUOVA` | `APERTA` | `AG23091501` | `usr_marco` | 2026-09-22 10:14 |
| `hist_002` | `offer_001` | `APERTA` | `CHIUSA` | `AG23091501` | `usr_paola` | 2027-01-15 09:00 |

`agcom_code_used` resta lo stesso codice (nessun nuovo codice viene assegnato in chiusura) — coerente con quanto segnalato come ancora da confermare in via definitiva (§6.5 del documento precedente).

**`dynamic_table_snapshot`** — nuova riga, generata automaticamente insieme a `hist_002`

| id | state_history_id | created_at |
|---|---|---|
| `snap_001` | `hist_001` | 2026-09-22 10:14 |
| `snap_002` | `hist_002` | 2027-01-15 09:00 |

`snap_002.tables_payload` è **identico** a `snap_001`: se l'offerta è davvero immutabile mentre `APERTA` (ipotesi §6.3), nessuno ha potuto toccare `dynamic_table` tra pubblicazione e chiusura, quindi la seconda fotografia coincide con la prima. Il fatto che venga comunque scattata separatamente (invece di essere "riusata") è proprio il senso dell'approccio audit-strict: ogni transizione ha la sua prova indipendente, anche se il contenuto sottostante non è cambiato.

**`offer_document`** — **nessuna riga nuova** in questo esempio.

> Questo riflette la Domanda aperta §6.4, ancora senza risposta confermata: non generiamo nuovi PDF "di chiusura", assumendo che gli ultimi Sintesi/Trasparenza pubblicati (`doc_004`, `doc_005`) restino i documenti di riferimento anche a offerta chiusa. Se la decisione finale fosse diversa, qui comparirebbero `doc_006`/`doc_007` con `state_history_id = hist_002`.

---

## 6. Scenario 5 — Ispezione e Audit AGCOM (sola lettura)

**01/03/2027** — Un auditor deve verificare cosa era esattamente pubblicato per `offer_001` il **15 ottobre 2026** (un giorno qualunque durante il periodo `APERTA`). Nessuna scrittura: solo query.

**Passo 1 — stato e cronologia**

```sql
SELECT * FROM offer_state_history WHERE offer_id = 'offer_001' ORDER BY timestamp;
```

| id | old_status | new_status | agcom_code_used | changed_by | timestamp |
|---|---|---|---|---|---|
| `hist_001` | `NUOVA` | `APERTA` | `AG23091501` | `usr_marco` | 2026-09-22 10:14 |
| `hist_002` | `APERTA` | `CHIUSA` | `AG23091501` | `usr_paola` | 2027-01-15 09:00 |

L'auditor vede subito: il 15 ottobre 2026 l'offerta era `APERTA` (siamo tra `hist_001` e `hist_002`), quindi la transizione rilevante è `hist_001`.

**Passo 2 — contenuto esatto in quel momento**

```sql
SELECT tables_payload FROM dynamic_table_snapshot WHERE state_history_id = 'hist_001';
```

→ restituisce **esattamente** il JSON di `snap_001` mostrato nello Scenario 3 — comprese le due righe di PREZZO con lo sconto, i due costi di attivazione, i due servizi inclusi. Indipendentemente da cosa contenga `dynamic_table` *oggi* (marzo 2027), questa è la prova di cosa c'era scritto il 22 settembre 2026, e resta valida anche per il 15 ottobre perché nessuna modifica è intervenuta nel frattempo.

**Passo 3 — i documenti pubblicati in quel momento**

```sql
SELECT * FROM offer_document WHERE offer_id = 'offer_001' AND state_history_id = 'hist_001';
```

| id | doc_type | gcs_uri | version |
|---|---|---|---|
| `doc_004` | `SINTESI_PDF` | `gs://vm-docs/offer_001/sintesi_v1.pdf` | 1 |
| `doc_005` | `TRASPARENZA_PDF` | `gs://vm-docs/offer_001/trasparenza_v1.pdf` | 1 |

L'auditor ha ora, con tre query, una ricostruzione completa e difendibile: **chi** ha pubblicato, **quando**, **con quale codice AGCOM**, **cosa c'era scritto** e **quali documenti** erano effettivamente disponibili al pubblico in quel preciso istante — senza mai dover fidarsi dello stato "vivo" e mutabile di `dynamic_table`.

---

## 7. Stato finale consolidato — tutte le tabelle, tutte le righe

A percorso concluso (post-chiusura, marzo 2027), questo è il contenuto integrale di ogni tabella toccata da `offer_001`.

**`offer`**

| id | segment_id | technology_id | payment_method | commercial_name | base_price | po_code | current_agcom_code | status | date_start | date_end |
|---|---|---|---|---|---|---|---|---|---|---|
| `offer_001` | `seg_verymobile` | `tech_ftth` | `ABBONAMENTO` | Very 200 Full | 9.99 | `PO-VM-2026-0456` | `AG23091501` | `CHIUSA` | 2026-09-22 | 2027-01-15 |

**`offer_activation_fee`**

| id | offer_id | target_type | price |
|---|---|---|---|
| `fee_001` | `offer_001` | `gia_clienti` | 5.00 |
| `fee_003` | `offer_001` | `nuovi_portabilita` | 15.00 |

*(`fee_002` non esiste più — è stata cancellata nello Scenario 2, nessuna traccia strutturata del suo passaggio resta nel DB, coerente con la Domanda aperta §6.2)*

**`dynamic_table`** — 3 righe, contenuto identico a fine Scenario 2 (mai più modificate, per ipotesi §6.3)

| id | offer_id | table_identifier | sequence_order |
|---|---|---|---|
| `dt_001` | `offer_001` | `PREZZO` | 1 |
| `dt_002` | `offer_001` | `COSTI` | 2 |
| `dt_003` | `offer_001` | `SERVIZI` | 3 |

**`offer_state_history`**

| id | old_status | new_status | changed_by | timestamp |
|---|---|---|---|---|
| `hist_001` | `NUOVA` | `APERTA` | `usr_marco` | 2026-09-22 10:14 |
| `hist_002` | `APERTA` | `CHIUSA` | `usr_paola` | 2027-01-15 09:00 |

**`dynamic_table_snapshot`**

| id | state_history_id |
|---|---|
| `snap_001` | `hist_001` |
| `snap_002` | `hist_002` |

**`offer_document`** — 5 righe totali, di cui 4 correnti (`is_current = true`)

| id | doc_type | version | is_current | state_history_id |
|---|---|---|---|---|
| `doc_001` | `TEMPLATE_DOCX` | 1 | false | `NULL` |
| `doc_002` | `TEMPLATE_XLSX` | 1 | true | `NULL` |
| `doc_003` | `TEMPLATE_DOCX` | 2 | true | `NULL` |
| `doc_004` | `SINTESI_PDF` | 1 | true | `hist_001` |
| `doc_005` | `TRASPARENZA_PDF` | 1 | true | `hist_001` |

---

## 8. Cosa mostra questo esempio, in sintesi

- **La bozza (Scenario 1-2) è un "laboratorio" senza audit**: si può modificare liberamente, cancellare e reinserire righe (`offer_activation_fee`), sovrascrivere JSON (`dynamic_table`) — nulla di tutto questo lascia traccia in `offer_state_history`/`dynamic_table_snapshot`. Se questo vi sembra un rischio (Domanda §6.2), ora avete un esempio concreto di *cosa esattamente andrebbe perso* in caso di dispute su una bozza.
- **La pubblicazione (Scenario 3) è l'unico momento in cui tutto si "congela"**: una sola operazione dell'utente (inserire il codice AGCOM) innesca a cascata tre scritture automatiche (`offer_state_history`, `dynamic_table_snapshot`, `offer_document` ×2) — il cuore dell'approccio audit-strict.
- **La chiusura (Scenario 4) ripete lo stesso pattern**, anche se il contenuto sottostante non cambia — ogni transizione ha sempre la sua prova indipendente.
- **L'audit (Scenario 5) non tocca mai `dynamic_table` "viva"**: legge solo dati storici immutabili, il che è esattamente l'obiettivo dell'intero design.
