# Esiti attesi

🔑 **Questo file si scrive prima di eseguire.** Il rischio di un banco è
preciso e fatale: lo si aggiusta finché è verde, e a quel punto non prova più
niente. Il Fermi si difende con `vincoli-attesi.md`, dove i conflitti sono
scritti *prima* di lanciare il solver; l'Alighieri eredita la disciplina,
rinforzata da quattro regole (spec §6):

1. L'esito si scrive **prima** della prima esecuzione, dal disegno.
2. Ogni riga di vincolo dichiara la famiglia che deve far scattare.
3. Se l'osservato smentisce l'atteso, si scrive **quale delle due** era
   sbagliata — e se era l'attesa, si dice perché. Non si riscrive l'attesa in
   silenzio.
4. **Verifica per mutazione**: togliere la riga di una famiglia deve cambiare
   l'orario. Una famiglia la cui rimozione non cambia niente non è esercitata,
   è solo *presente* — ed è il modo in cui un dataset «completo» può essere
   vuoto.

⚠ Il punto 4 è il vero contratto. Senza, «l'Alighieri copre tutte le famiglie»
significa solo «l'Alighieri ha righe in tutte le tabelle».

E ha una forma economica e automatica che sta a monte della mutazione: la
**sonda** ([`tests/sonda.py`](../../tests/sonda.py)), che avvolge `restrict` e
`build` di ogni builder e conta celle tolte e constraint postati. Non
sostituisce la mutazione — un builder può postare un vincolo vacuo — ma prende
in un secondo il caso «la riga c'è e il builder non la vede», che sul Fermi
vale ventiquattro builder su ventisette.

---

## Ondata 1 — l'anagrafica

⚠ **I numeri di questa sezione sono quelli dell'ondata 1, e l'ondata 2 li ha
mossi** (340 attività, 361 ore erogate, 71 richieste d'aula). Restano qui
com'erano: sono il verbale di quella misura, non lo stato corrente — che sta
nel [README](README.md).

Qui l'atteso è **aritmetico**: quadri orari, cattedre e attività devono dire lo
stesso numero. Le cinque quantità qui sotto sono state derivate dal disegno
prima di scrivere il codice che le costruisce, e confermate al primo giro.

| Grandezza | Atteso | Osservato |
|---|---:|---|
| Ore-classe | 345 | ✅ |
| Attività | 323 | ✅ |
| Righe di servizio | 107 | ✅ |
| Assegnazioni docente × classe | 127 | ✅ |
| Cattedre a `+/- = 0` | 21 su 21 | ✅ |

E l'atteso sul **motore**:

| | Atteso | Osservato |
|---|---|---|
| `analyze_capacity` | nessun verdetto negativo | ✅ |
| `check_schedule` su orario vuoto | solo `activity_unplaced`, 323 volte | ✅ |
| Fase 1 | `OPTIMAL`, zero scarti | ✅ 2,5 s, 13 583 var, 5 493 constraint |
| Fase 2 | 66 richieste su 66, zero rinunce | ✅ 0,2 s |
| Sonda | 4 builder su 27 | ✅ occupation, room_pool, site_transition, grid |

⚠ **Un atteso che l'ondata 1 non pretende.** La spec (§4) chiede un dataset
*stretto*: `OPTIMAL` con zero scarti, ma una sola aula o un solo docente in
meno e comincia a scartare. Senza una riga di vincolo la tensione non c'è, e
fingere il contrario sarebbe il primo modo di aggiustare il banco. Il criterio
si verifica all'ondata 7, quando le famiglie ci sono tutte.

## Ondata 2 — gli sdoppiamenti

Quattro forme, tutte diverse. L'atteso è scritto dal disegno di
[gruppi.md](gruppi.md), e la parte che conta è la **copertura**: ogni atomo
deve ricevere esattamente il proprio piano, e nessuna delle quattro forme deve
produrre uno scostamento.

| Cosa | Atteso | Osservato |
|---|---|---|
| IRC/alternativa su 12 classi | nessun `election_mismatch` | ✅ |
| IRC e ALT nella stessa fascia | ammesso — parti disgiunte | ✅ |
| Un'ora a classe intera contro l'IRC | `resource_occupied` | ✅ |
| 2C articolata, due piani | nessun `ambiguous_study_plan` | ✅ |
| Gli ordinari non ricevono informatica | atomi disgiunti | ✅ |
| Sdoppiamento 3A: costo per il docente | N01 da 17 a 18 ore | ✅ |
| Raggruppamento ING1: 1A e 1B accoppiate | `resource_occupied` fra livelli e classe intera | ✅ |
| I due livelli fra loro | conviventi | ✅ |
| Copertura sul dataset intero | solo `activity_unplaced` | ✅ 340 |
| Due fasi | `OPTIMAL`, zero scarti, 71 aule su 71 | ✅ |

### ⚠ Un atteso smentito, e la smentita è del motore

**Atteso**: le attività **allineate** stanno insieme. 📦 Lo XSD dichiara che
*l'allineamento genera l'attività complessa*, e il dataset dichiara 15
allineamenti su 38 attività — le dodici coppie IRC/alternativa, il latino
contro l'informatica della 2C, il laboratorio di 3A, i due livelli di inglese.

**Osservato**: **13 allineamenti su 15 escono dal solve senza una sola
coincidenza.** I due livelli di inglese finiscono su sei celle diverse; il
latino e l'informatica della 2C non sono mai in parallelo. Nessun finding, e
nessun vincolo violato — perché **nessun builder e nessun checker legge
`alignment_ident`**.

**Quale delle due era sbagliata**: né l'attesa né il dato. È il **motore** a
non avere la famiglia, ed è esattamente ciò che questo banco esiste per
trovare. Non si ripara qui (spec §8: *nessuna modifica al motore*); è un debito
in [todo.md](../../docs/todo.md), e un test ne fissa il comportamento sbagliato
perché diventi rosso il giorno in cui si chiude.

⚠ E non è un dettaglio cosmetico: senza allineamento metà classe resta a scuola
in un'ora in cui non ha lezione, e l'orario che consegneremmo sarebbe
sbagliato pur essendo, per i nostri vincoli, impeccabile.

## Ondate 3–7

Da scrivere prima di ciascuna, nell'ordine della spec §9: asse Cardinalità,
asse Relazione, sedi e peso didattico, quote e criteri di qualità, criterio di
accettazione.
