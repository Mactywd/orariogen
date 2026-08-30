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

> ⚠ **Il punto 4 è stato corretto dall'ondata 3, nella forma non nella
> sostanza.** *Togliere la riga* si è rivelato non misurabile: senza funzione
> di costo sopra lo scarto ogni orario a zero scarti è ottimo, e ciò che torna
> dopo la rimozione dice quale ottimo ha trovato la ricerca, non se la riga
> mordeva. Al suo posto si **stringe di una tacca** e si pretende
> `INFEASIBLE` — una proprietà del modello, non del testimone. Vedi
> [l'ondata 3](#ondata-3--lasse-cardinalità) e [vincoli.md](vincoli.md).
>
> ⚠ **E l'ondata 4 lo ha corretto una seconda volta, allargandolo.** La tacca
> vale dove c'è un parametro da stringere; sui divieti di relazione non c'è, e
> *una proibizione non sparpaglia*. Al suo posto il **testimone puntato**: si
> impone con `pinned` la configurazione vietata e si pretende `INFEASIBLE` con
> la riga e `OPTIMAL` senza. Così la rimozione — la forma originale del punto
> 4 — torna misurabile. Vedi [l'ondata 4](#ondata-4--lasse-relazione) e
> [relazioni.md](relazioni.md).

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
si verifica all'ondata 7, quando le famiglie ci sono tutte — ed è verificato:
vedi [§8 dell'ondata 7](#8-stretto-ma-risolvibile-il-criterio-di-4).

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

⚠ Come per l'ondata 1, i numeri di questa tabella sono **il verbale di quella
misura**: l'ondata 4 li ha mossi (342 attività, 34 parti, 73 richieste d'aula,
N01 a 19 ore). Lo stato corrente sta nel [README](README.md).

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

## Ondata 3 — l'asse Cardinalità

Otto famiglie, dieci righe, e l'atteso scritto dal disegno di
[vincoli.md](vincoli.md): ogni riga dichiara **la forma** che deve produrre
nell'orario, non solo che nessun finding scatti.

| Famiglia | Atteso | Osservato |
|---|---|---|
| `min_distribution` (N02) | ≥ 4 giornate da 2 h | ✅ 4 su 5 |
| `max_hours` (M03) | mattina ≤ 3 h, giornata ≤ 5 h ⇒ ≥ 6 h di pomeriggio | ✅ **10** al pomeriggio |
| `max_presence` (L06) | 3 giornate lavorate, due intere vuote, presenza ≤ 5 fasce | ✅ giorni 0, 2, 4 |
| `arrival_departure` (A01) | prima fascia libera tutti i giorni | ✅ mai la fascia 0 |
| `free_guaranteed` (P01) | 2 giornate intere libere + 2 mezze | ✅ 3 giornate lavorate, 2 mezze libere |
| `max_half_days` `MMG` (2A) | ≤ 7 mezze giornate | ✅ esattamente 7 |
| `max_half_days` `MG` (R02) | mai mattina **e** pomeriggio | ✅ 5 giorni, 5 mezze |
| `max_site_changes` (R01) | ≤ 1 cambio al giorno e nella settimana | ✅ 2 giornate, 1 cambio |
| `max_gap_hours` (L03) | ≤ 1 ora di buco a settimana | ✅ esattamente 1 |
| Sonda | 8 builder nuovi | ✅ **12 su 27** (era 4) |
| Due fasi | `OPTIMAL`, zero scarti, 71 aule su 71 | ✅ 15 372 var, 8 758 constraint |

E l'atteso sul **bordo**, che è il vero contratto di questa ondata: per ogni
famiglia una tacca più stretta deve rendere il dataset `INFEASIBLE`.

| Famiglia | Tacca | Atteso | Osservato |
|---|---|---|---|
| `min_distribution` | `min_days 5`, `180`/g | `INFEASIBLE` | ✅ 2,4 s |
| `max_hours` | `day_minutes 240` | `INFEASIBLE` | ✅ 3,2 s |
| `max_presence` | `days 1` | `INFEASIBLE` | ✅ 3,6 s |
| `arrival_departure` | `not_before_slot 5` | `INFEASIBLE` | ✅ 2,2 s |
| `free_guaranteed` | `free_days 4` | `INFEASIBLE` | ✅ 1,0 s |
| `max_half_days` | `max_half_days 5` | `INFEASIBLE` | ✅ 4,4 s |
| `only_half_day` | la casella sulla 2A | `INFEASIBLE` | ✅ 4,8 s |
| `max_site_changes` | `per_day 0` | `INFEASIBLE` | ✅ 20,3 s |
| `max_gap_hours` | `max_gap_minutes 0` | `INFEASIBLE` | ❌ **`OPTIMAL`** |

### ⚠ Due attese smentite, e nessuna delle due è del motore

**La prima è del dataset.** Il D.T.B. non arriva al bordo: `max_gap_minutes = 0`
su L03 resta risolvibile, e lo resta anche **zero buchi per ogni docente e per
ogni classe insieme**. *Quale delle due era sbagliata*: l'attesa. La ragione si
conta — 40 fasce a settimana contro cattedre da 10–21 ore e classi da 28–32:
la contiguità dentro una mezza giornata è gratis. Stringerla vuole una griglia
più densa, non una taratura di questa riga. Un test asserisce l'`OPTIMAL`, così
diventerà rosso il giorno in cui il banco si stringe.
⚠ **E quel giorno non è l'ondata 7**, misurato: il criterio di §4 è
verificato **sulle risorse** (togline una e il banco scarta), e la contiguità è
stretta sulla **densità della griglia**. Sono due nozioni diverse di «stretto»,
e la spec ne dichiarava una sola.

**La seconda è del metodo, ed è la più importante.** La regola 4 di questo file
— *togliere la riga deve cambiare l'orario* — è stata implementata e misurata,
e **non regge come test**. Il modello di fase 1 non ha una funzione di costo
sopra lo scarto: ogni orario a zero scarti è ottimo, e il solver ne restituisce
uno arbitrario fra milioni. Se quello che torna dopo la rimozione viola la riga
tolta, è un fatto sulla **ricerca**, non sulla riga — misurato: cambiando una
sola riga *estranea* alla famiglia osservata il verdetto si ribaltava per **tre
famiglie su nove**, e a `workers=8` la stessa configurazione dava risposte
diverse a esecuzioni diverse.

*Quale delle due era sbagliata*: la regola, nella sua forma letterale. La
sostituisce lo **stringimento**, che dimostra la stessa cosa in modo più forte:
`INFEASIBLE` è una proprietà del modello, non del testimone che torna, e una
riga che non sopporta una tacca in più non può essere soddisfatta per caso. Il
punto 4 resta valido in sostanza — *una famiglia solo presente non è
esercitata* — ed è la sonda a prenderne la metà strutturale.

### ⚠ E un fatto che l'ondata 3 ha reso visibile

A orario **vuoto** l'Alighieri non produce più solo `activity_unplaced`: due
delle otto famiglie sono *deficienze* (`min_distribution` e `free_guaranteed`,
i due checker `PLACEMENT_MONOTONE = False` fra le righe del dataset) e valgono
zero quando non c'è niente di piazzato. Per loro **piazzare ripara**. Non è
una regressione, è la forma in cui l'analisi preventiva inganna chi la legge
distrattamente: un orario vuoto non è «conforme tranne che per le attività da
piazzare».

## Ondata 4 — l'asse Relazione

Tredici tipi, tredici righe, e l'atteso scritto dal disegno di
[relazioni.md](relazioni.md). ⚠ **Qui l'atteso ha due parti**, e la seconda è
la novità dell'ondata: la forma che la riga garantisce nell'orario, *e* il
**testimone puntato** — la configurazione che la riga vieta, imposta con
`pinned`, che deve rendere il modello `INFEASIBLE` con la riga e `OPTIMAL`
senza.

| Cosa | Atteso | Osservato |
|---|---|---|
| Tredici tipi, uno per riga | nessun tipo scoperto | ✅ |
| MAT e FIS di 5A | mai nella stessa mezza giornata | ✅ |
| LAT e GRE di 4B | mai lo stesso giorno | ✅ giorni {0, 2} contro {1, 3} |
| GRE di 3B | nessuna coppia di giornate a distanza 1 | ⚠ ✅ ma **tutte e tre lo stesso giorno** — vedi sotto |
| MOT → MAT in 4A | nessuna successione immediata | ✅ |
| MAT di 2A | ≤ 180′ per mezza giornata | ✅ max 120′ |
| ITA di 3B | ≤ 120′ al giorno | ✅ esattamente 120′ ×2 |
| LAT e GRE di 5B | la prima ora di latino precede la prima di greco | ✅ (0,1) contro (0,3) |
| Le due sessioni di FIS di 3A | a ≤ 1 mezza giornata l'una dall'altra | ✅ stessa mezza giornata |
| LAT di 1B | passo ≥ 2 mezze giornate | ✅ **arco 0→9**, un'ora al giorno |
| I quattro `PARTS_*` | l'ordine parte/classe dentro il secchio | ✅ |
| Testimone puntato | 13 su 13, in **due** direzioni | ✅ `INFEASIBLE` / `OPTIMAL` a zero scarti |
| Sonda | 13 builder nuovi | ✅ **25 su 27** (era 12) |
| Due fasi | `OPTIMAL`, zero scarti, 73 aule su 73 | ✅ 15 545 var, 11 783 constraint |

E l'atteso sul **bordo**, dove il tipo ha un parametro da stringere:

| Tipo | Tacca | Atteso | Osservato |
|---|---|---|---|
| `max_hours_half_day` | 180′ → 60′ | `INFEASIBLE` | ✅ 0,7 s |
| `max_hours_day` | 120′ → 60′ | `INFEASIBLE` | ✅ 2,6 s |
| `half_day_gap` | 2 → 3 | `INFEASIBLE` | ✅ 2,1 s |
| `two_days_incompatible` | GRE (3 h) → LAT (4 h) | `INFEASIBLE` | ❌ **`OPTIMAL`** |

### ⚠ Un'attesa smentita, e la sbagliata era l'attesa

Il disegno contava così: quattro ore di latino a due a due non adiacenti
vogliono quattro giornate, e l'insieme indipendente massimo di un cammino di
cinque nodi è tre. Il conteggio è giusto; la **premessa** no. *Niente obbliga
quattro ore della stessa materia a stare su quattro giornate distinte*, e
infatti il solver le impila — come impila le tre ore di greco del 3B, tutte
sullo stesso venerdì.

🔑 **È il fatto generale dell'asse Relazione, e va scritto una volta sola:
una proibizione non sparpaglia.** `same_day_incompatible` fra due materie è
sempre soddisfacibile da solo (A si concentra in un giorno, B in un altro);
`two_days_incompatible` con A = B pure; e trentanove fasce libere assorbono
quasi ogni altro divieto. È il motivo per cui la regola del bordo qui non è la
tacca dell'ondata 3 ma il **testimone puntato** — che vale per tutti e tredici
i tipi, parametro o no. Un test asserisce l'`OPTIMAL` di quella tacca, così
diventerà rosso il giorno in cui il banco stringerà abbastanza da forzare lo
sparpagliamento. ⚠ **Non è l'ondata 7**: vedi la nota sulle due nozioni di
«stretto» in [§8](#8-stretto-ma-risolvibile-il-criterio-di-4).

### 🔑 E la regola 4 torna misurabile, nella forma puntata

L'[emendamento dell'ondata 3](#ondata-3--lasse-cardinalità) diceva che
*togliere la riga* non è misurabile perché il solver restituisce un ottimo
arbitrario. Resta vero **finché il solver è libero**. Imponendo con `pinned`
la configurazione vietata, le due esecuzioni non rispondono più «quale
orario» ma `INFEASIBLE` e `OPTIMAL`: due proprietà del modello, in due
direzioni, nessuna delle quali dipende dal testimone che torna. La rimozione
torna quindi a essere il test che la regola 4 voleva — con il pin come
condizione, e con il ramo «senza la riga» come controllo obbligatorio, senza
il quale un pin illegale per un'altra ragione direbbe `INFEASIBLE` e non
proverebbe niente.

### ⚠ E una riga di dataset che l'ondata ha dovuto aggiungere

I quattro tipi `PARTS_*` vogliono quattro portatori che **non si implichino**:
un ordine per giornata su un'unità rende veri per costruzione gli omogenei su
ogni sotto-unità e su ogni mezza giornata. Con la sola 3A sdoppiata, due dei
quattro sarebbero stati *presenti e implicati* — cioè il difetto che la regola
4 esiste per non avere. Da qui il secondo laboratorio, in **4A**: +1
partizione, +2 parti, +2 attività, N01 da 18 a 19 ore, la quadratura `+/- = 0`
intatta. È la mossa del cappellano dell'ondata 3, e come quella è scritta
invece che nascosta.

## Ondata 5 — le risorse, il peso e le indisponibilità

Tre famiglie in una sola ondata, e stanno insieme per una ragione: sono
**tutto ciò che resta** perché la sonda arrivi al registro intero. I due
builder che l'ondata 4 lasciava fuori — `structural:unavailability` e
`structural:didactic_weight` — sono qui, e con loro le due risorse di
piazzamento che nessun dataset aveva mai avuto.

⚠ **Il contratto è misto, ed è la prima volta.** Le indisponibilità e i tetti
di peso *per giornata e per mezza giornata* sono divieti sul piazzamento,
quindi si provano col **testimone puntato** dell'ondata 4. Lo spezzone di
RICCI è invece un conteggio (tre ore in tre fasce), quindi ammette la
**tacca** dell'ondata 3. E il tetto **settimanale** non ammette né l'una né
l'altro, e il perché è la cosa più istruttiva dell'ondata — vedi sotto.

| Cosa | Atteso | Osservato |
|---|---|---|
| Righe di indisponibilità | 55 (37 + 3 + 5 + 3 + 2 + 5) | ✅ |
| Livelli usati | tutti e tre, su tre tipi di risorsa | ✅ |
| Risorse nuove | 1 tecnico, 1 materiale | ✅ |
| Attività col tecnico | 7 (3 blocchi di FIS + 4 ore di laboratorio) | ✅ |
| Attività col carrello | 9, con quantità 2 / 2 / 1 | ⚠ **13**, e la capienza 4 invece di 3 — vedi sotto |
| Materie con peso 2 | 3 (MAT, LAT, GRE) | ✅ |
| Sonda | **27 su 27** — il registro intero | ✅ |
| Due fasi | `OPTIMAL`, zero scarti, 73 aule su 73 | ✅ 15 233 var, 12 251 constraint, ~7 s |

E l'atteso **riga per riga**, che è dove l'ondata si gioca:

| Riga | Contratto | Atteso | Osservato |
|---|---|---|---|
| `ricci` (rossa, docente) | tacca | una fascia rossa in più → `INFEASIBLE` | ✅ 1,2 s |
| `orientamento` (rossa, classe) | testimone puntato | `INFEASIBLE` / `OPTIMAL` | ✅ 0,8 s / 8,1 s |
| `palestra` (rossa, aula) | testimone puntato | `INFEASIBLE` / `OPTIMAL` | ✅ 0,7 s / 6,8 s |
| `permesso` (gialla, docente) | testimone puntato **e** override | `INFEASIBLE`; `OPTIMAL` con `ignora_opzionali` | ✅ e ⚠ `INFEASIBLE` autorizzando le **aule** |
| `manutenzione` (gialla, aula) | testimone puntato **e** override | idem, sull'altra categoria | ✅ e ⚠ `INFEASIBLE` autorizzando i **docenti** |
| `preferenza` (verde, docente) | contro-testimone | `OPTIMAL`: il verde **non** vieta | ✅ |
| `max_weight_morning` 9 | testimone puntato | `INFEASIBLE` / `OPTIMAL` | ✅ (peso 10) |
| `max_weight_afternoon` 5 | testimone puntato | `INFEASIBLE` / `OPTIMAL` | ✅ (peso 6) |
| `max_weight_day` 12 | testimone puntato | `INFEASIBLE` / `OPTIMAL` | ✅ (peso 13) |
| tetto settimanale 3B = 40 | tacca | 39 → `INFEASIBLE` | ✅ 1,3 s |
| tecnico di laboratorio | testimone puntato | due laboratori insieme → `INFEASIBLE` | ✅ |
| carrelli | testimone puntato | i due livelli d'inglese insieme (2 + 2) → `INFEASIBLE` | ❌ **e per fortuna** — vedi sotto |

### ⚠ Un'attesa smentita, e la sbagliata era il **dataset**

Il disegno dava tre carrelli, così che i due livelli d'inglese (due l'uno) non
potessero stare nella stessa fascia. Il testimone sarebbe stato pulito, e il
dataset **rotto**: stare nella stessa fascia è *il senso* di un raggruppamento
trasversale — gli stessi alunni si dividono per livello nella stessa ora — e
lo ha detto per primo un test dell'ondata 2, diventando rosso.

Correzione: **quattro** carrelli, e il carrello anche sulle quattro ore di
laboratorio a mezza classe (che sono piccoli gruppi come gli altri). Il
testimone diventa a tre attività — `2 + 2 + 2 > 4` — e la forma dell'ondata 2
resta. 🔑 Il criterio generale, che vale per le ondate 6 e 7: **un'ondata che
rompe una forma dell'ondata precedente per accendere un builder sta misurando
sé stessa.**

### ⚠ E una misura che ha cambiato due test delle ondate 3 e 4

I tetti di peso per giornata e mezza giornata sono ~510 constraint da migliaia
di letterali l'uno, e sono il primo vincolo del banco che cambia il **regime di
ricerca**: stesso modello, **439 s** con un lavoratore contro **7 s** con otto.
I due test che cercavano con `workers=1` per riproducibilità sono passati a
`workers=8`; le loro asserzioni sono invarianti e non celle, quindi non
dipendono da quale ottimo torni.

### ⚠ Il tetto settimanale non ha un testimone puntato, e non è una lacuna

Un pin non lo può violare: la somma dei pesi di un'unità-studente lungo la
settimana **non dipende da dove le attività vanno**. È il caso che
`CLAUDE.md` chiama *il tetto inevadibile*, e l'unica leva che il modello ha
per rispettarlo è **scartare**. Quindi il suo contratto è la tacca, e a
`allow_unplaced=False` la tacca dice `INFEASIBLE`. Vale la pena scriverlo
perché è la differenza fra un vincolo che *forma* l'orario e uno che si limita
ad ammetterlo o rifiutarlo — e i due non si provano allo stesso modo.

### 🔑 L'atteso che riguarda il carrello — e il ramo che si è avverato è il secondo

Il carrello è l'unica risorsa del banco che **non ha una sede**: è della
scuola, e serve l'inglese alla centrale e l'informatica in succursale. Se il
modello lo tratta come tratta un docente o un'aula, allora due attività di
sedi diverse non potranno mai condividere una fascia sul carrello — e questo
sarebbe **sbagliato**, perché quattro carrelli non sono un corpo solo.
L'atteso era doppio, e scritto prima di misurarlo:

- con capienza abbondante e due attività di sedi diverse sulla stessa fascia,
  il modello dovrebbe essere `OPTIMAL` (la capienza basta) — **atteso**;
- se invece è `INFEASIBLE`, il colpevole è `structural:site_transition`, che
  posta la clausola «due sedi sulla stessa fascia» su *ogni* chiave di
  occupazione, e il banco ha trovato il suo secondo difetto.

**Osservato: il secondo.** `INFEASIBLE` a capienza 4 (domanda 3) e ancora
`INFEASIBLE` a capienza 9, quindi non è capienza; e `OPTIMAL` a zero scarti
appena le due attività dichiarano la **stessa** sede. È **L6** in
`docs/todo.md`, non riparato per la regola della spec §8, e fissato da un test
che asserisce il comportamento corrente.

### ⚠ E un difetto che il banco ha trovato *scegliendo dove* mettere una riga

Cercando l'aula su cui mettere l'indisponibilità gialla si è visto che le due
fasi la leggono in modo diverso: `structural:room_pool` conta i posti come se
l'aula fosse libera, `RoomsContext._filtra` la toglie dalle candidate. Su
un'aula a candidata unica non si vede (il pre-filtro toglie la cella prima);
su un'aula a più candidate la fase 1 piazza e la fase 2 **rinuncia** — cioè
esattamente ciò che ADR-021 esiste per non far succedere. È **L6bis**, e il
dataset porta la sua gialla su `LAB-SUCC` proprio per non ospitarlo: un banco
che porta un difetto noto smette di misurare le regressioni.

### 🔑 E il ramo di controllo dell'ondata 4 ha fatto il suo mestiere

L'ondata 5 ha spento un testimone dell'ondata 4, e lo ha **detto**. Il pin di
`forbidden_sequence` metteva le due ore di scienze motorie della 4A al lunedì
alle otto; la riga `palestra` rende quella cella indisponibile. Da quel
momento il primo `assert` del testimone restava verde per il motivo
sbagliato — `INFEASIBLE` per il pre-filtro, non per la riga osservata — e il
**secondo** è diventato rosso.

⚠ È esattamente il caso per cui la spec ha reso obbligatorio il ramo «senza la
riga»: senza di esso il testimone sarebbe rimasto verde e vuoto, e nessuno se
ne sarebbe accorto. Il pin si è spostato al martedì.

## Ondata 6 — le quote, la qualità e le firme di settimana

Tre cose che stanno insieme perché sono **tutto ciò che il motore ha e che
nessun dataset ha mai messo in moto**: gli alleggerimenti a quota, i criteri
di qualità e la seconda firma di settimana. Le prime due sono codice mai
eseguito su dati; la terza è un **debito dichiarato** (L3, 2026-08-30 — *i
criteri di qualità ignorano le firme di settimana*), e la spec §4.1 dice
cosa se ne deve fare: *«a quel punto il debito smette di essere un sospetto e
diventa un test rosso, che è il modo giusto di chiuderlo»*.

### La riga che porta la seconda firma: l'ora quindicinale

Il dataset ha una sola firma di settimana da cinque ondate — tutte le
maschere sono l'anno intero — e quindi `week_signatures` restituisce una
riga sola e nessuno se ne accorge. L'ondata 6 mette **la seconda ora di
scienze del 5B a settimane alterne**: una settimana in laboratorio col
tecnico, la settimana dopo teoria in aula. È la forma vera con cui una scuola
spende un laboratorio conteso, e nel nostro modello è una coppia di attività
con maschere **complementari**.

🔑 **Il monte ore non cambia, ed è il punto.** In ogni settimana ne è attiva
esattamente una, quindi il docente lavora le stesse 2 ore e l'alunno riceve
le stesse 2 ore: lo sdoppiamento delle ondate 2 e 4 costa un'ora al docente,
la quindicinale **no**. È la quinta forma, e la sola che non si paga.

| Cosa | Atteso | Osservato |
|---|---|---|
| Firme di settimana | **2** — 17 settimane pari, 16 dispari | ✅ |
| Attività | 342 → **343** | ✅ |
| Richieste d'aula | **73**, invariate: la metà di teoria non chiede il laboratorio | ✅ |
| Ore di N02 e monte ore del 5B | **invariati** — e il fixture lo verifica settimana per settimana | ✅ |
| Attività col tecnico | 7 → **8** | ✅ |
| Fase 1 | `OPTIMAL`, zero scarti; variabili e constraint **circa il doppio** (il vocabolario è per firma) | ✅ e ❌ — 15 330 / 13 817, cioè **+0,6 % e +12,7 %**; vedi sotto |
| Fase 2 | 73 su 73 | ✅ |
| Sonda | **27**, ferma: un'ondata che la fa salire ancora starebbe misurando sé stessa | ✅ |

#### ⚠ Un'attesa smentita, e la sbagliata era l'attesa

«Circa il doppio, il vocabolario è per firma» era una deduzione dalla forma del
codice, non una misura, e la forma del codice diceva un'altra cosa. Le
variabili derivate nascono **solo dove un builder posta qualcosa**, e
`OccupationBuilder` deduplica i constraint identici fra firme — la sua
`signature` è la coppia (cella, insieme di attività). Le uniche chiavi che
distinguono le due settimane sono quelle toccate dalle due metà.

| | Variabili | Constraint |
|---|---:|---:|
| Ondata 5 | 15 233 | 12 251 |
| + le due quote | 15 244 | 12 255 |
| + la quindicinale | 15 319 | 13 813 |
| Ondata 6 | **15 330** | **13 817** |

🔑 **Una seconda firma non raddoppia il modello: costa quanto le attività che
la distinguono.**

⚠ **E non contraddice `quality.py`**, che chiama le firme *«una dimensione
moltiplicativa (~0,3 s per firma, misurato sulla fase 5)»*: quella misura è su
`check_schedule`, che esegue *ogni* checker una volta per firma. Là è
moltiplicativo davvero. Nel solver no. Sono due cose diverse che si somigliano,
ed è il genere di somiglianza che fa scrivere numeri sbagliati con sicurezza.

### Le due forme dell'alleggerimento

⚠ **Le quote del dataset non devono essere consumate dal dataset**, e non è
un ripiego: `test_le_otto_forme_dichiarate` (ondata 3) pretende che l'orario
di base non porti **nessun** finding `HARD` oltre alle aule, e una quota
consumata è una violazione **nominata** — è l'invariante scritto in testa a
`relaxation.py`. Quindi le righe stanno nel dataset perché i builder le
leggano e postino i letterali, e la tensione la mette il **testimone**, come
per i divieti dell'ondata 4.

E stanno su due portatori scelti perché **non sono bordi di nessuna ondata
precedente**: allentare un bordo dell'ondata 3 renderebbe risolvibile la sua
tacca, cioè spegnerebbe un test scritto due ondate fa.

| Riga | Forma | Portatore | Perché lì |
|---|---|---|---|
| `HALF_DAYS`, 1 violazione | **deroga** | R02 Donati (il `MG`) | il bordo del `MG` sta sulla 2A, non su di lei |
| `MAX_PRESENCE`, 2 violazioni, `margine` 120 min | **margine** | R01 Colombo (il cappellano) | il bordo di `max_presence` sta su GENTI |

| Contratto | Atteso | Osservato |
|---|---|---|
| Base | quote **non consumate**: zero finding nuovi, l'orario di prima | ✅ (+11 variabili, +4 constraint: i builder le leggono) |
| Deroga, con tensione (`max_presence {days: 2}` su DONAT) | senza quota `INFEASIBLE`, con quota `OPTIMAL` | ✅ |
| Deroga consumata | il finding `HARD` **resta**: la quota autorizza, non nasconde | ✅ (`only_half_day`) |
| Margine, con tensione su COLOM | quota **0** → `INFEASIBLE`, **1** → `INFEASIBLE`, **2** → `OPTIMAL` | ✅, ma la **taratura** era sbagliata — vedi sotto |

#### ⚠ E un test che misurava il propagatore invece del modello

La prima taratura metteva la presenza a cinque fasce e faceva dimostrare al
caso di mezzo *5 + 7 = 12 fasce per dodici ore più la fascia di viaggio*.
L'aritmetica è giusta; il solver non ci arrivava — `UNKNOWN` a 180 s, e di
nuovo a 120 s. La ragione è visibile: il legame «solo due giornate sono
attive» passa da booleani che il rilassamento lineare non lega ai minuti, e i
tetti giornalieri restano postati su tutte e cinque le giornate.

Due correzioni, e nessuna delle due indebolisce l'affermazione: le due
giornate si dichiarano col **rosso** — il pre-filtro toglie le celle, e le
giornate diventano due *davvero* — e l'aritmetica si sposta tutta sulle ore
(quattro fasce di tetto, tre ore di margine: 4 + 4, 4 + 7, 7 + 7). I tre casi
chiudono in **37 s**.

🔑 **Un test che misura la potenza del propagatore invece di una proprietà del
modello è un test che un giorno diventa rosso da solo.**

🔑 **La terza riga è la più forte**, ed è la mutazione che il docstring di
`RelaxationQuota` chiede per nome: *«la quota è collegata» passa anche se il
margine vale dieci volte quello dichiarato*. Qui il **numero** conta: dodici
ore in due giornate con una sola fascia di viaggio non stanno in 5 + 7 fasce,
stanno in 7 + 7 — quindi servono **due** supplementi, e uno solo non basta.
È un argomento di conteggio, come le tacche dell'ondata 3.

### I criteri di qualità, e il debito che devono far vedere

L'atteso è **un rosso**, ed è dichiarato prima di misurarlo: il criterio
`gaps` calcola i buchi sull'**unione** delle settimane (`quality.py` lo
scrive come approssimazione dichiarata), mentre `check_schedule` valuta ogni
firma per conto suo. Con la quindicinale le due letture **devono** divergere.

Il testimone è aritmetico: 5B al lunedì, l'attività settimanale alla prima
fascia e un'altra alla quarta; la metà di laboratorio alla seconda, quella di
teoria alla terza.

| Settimana | Fasce occupate | Buchi |
|---|---|---|
| pari | 0, 1, 3 | **1** (la fascia 2) |
| dispari | 0, 2, 3 | **1** (la fascia 1) |
| unione (ciò che vede il criterio) | 0, 1, 2, 3 | **0** |

| Cosa | Atteso | Osservato |
|---|---|---|
| `check_schedule` con D.T.B. a zero sul 5B | il finding `max_gap` in **tutte** le settimane | ✅ 33 su 33, `gap_minutes` 60 |
| Il criterio `gaps` sullo stesso orario | **0** — cioè il difetto | ✅ |
| Ramo di controllo: la metà di teoria non piazzata | il criterio **conta** il buco | ✅ 180 (tre chiavi: la classe e le sue due parti) |

E la catena della qualità, misurata:

| Livello | Valore | Ottimo dimostrato |
|---|---:|---|
| `gaps_teachers` | 0 | ✔ |
| `gaps_classes` | 0 | ✔ |
| `isolated_all` | 71 | ✗ |
| `free_half_days_teachers` | 143 | ✗ (limite inferiore 19) |
| `regularity_classes` | 936 | ✗ (limite inferiore 101) |
| `preferences_all` | 0 | ✔ |

🔑 **E il verde dell'ondata 5 chiude qui il suo anello**: là si provava che
*non vieta*, qui che **conta**. ⚠ Ma i sei livelli portano un `solve` da 9 a
**82 s**, quindi `build()` non li installa: li chiede chi li vuole.

#### ⚠ E un'attesa smentita sul verde, che è del metodo

L'attesa diceva «`preferences_all` a zero, dimostrato», e la prima misura la
confermava. La seconda ha dato **1**. Non è il verde a essere incerto: i tre
livelli sopra di lui esauriscono il budget senza dimostrare il proprio ottimo,
quindi vengono fissati al valore che la ricerca *ha trovato*, che cambia da
esecuzione a esecuzione — e con esso cambia la regione in cui il verde deve
stare. 🔑 **Un livello sotto un livello non dimostrato eredita
l'indeterminatezza di quello.** Il test lo installa quindi da solo: così lo
zero è una proprietà del modello e non un fatto sulla ricerca. È la lezione
della mutazione per rimozione dell'ondata 3, in un posto nuovo — ed è la sola
attesa dell'ondata 6 che una misura ha corretto due volte.

⚠ **Non si ripara** (spec §8): diventa **L7** in `docs/todo.md`, fissato da un
test che sarà rosso il giorno in cui si chiude — come L5, L6 e L6bis.

### E una domanda che la quindicinale pone per prima

L'occupazione è **l'unico builder che distingue le firme** (lo dice il suo
docstring), e fino a qui nessun dataset gliel'ha chiesto. La quindicinale sì:
le due metà stanno sulla stessa classe, quindi condividono la chiave di
occupazione, e **possono stare nella stessa cella** solo perché le maschere
non si intersecano — che è poi come una scuola scrive davvero un'ora
quindicinale, «scienze al martedì alla terza», e cambia solo cosa ci si fa.

| Testimone puntato | Atteso | Osservato |
|---|---|---|
| le due metà sulla stessa cella | `OPTIMAL` | ✅ |
| una metà e l'ora settimanale sulla stessa cella | `INFEASIBLE` | ✅ |

## Ondata 7 — il criterio di accettazione e i comandi

L'ultima ondata non aggiunge righe al dataset per accendere un builder: quello
è finito all'ondata 5, e la sonda lo dice. Aggiunge la domanda che sta a valle
di tutte le altre — **i comandi hanno qualcosa di vero da dire su questo
dataset?** — che è §7 della spec: sette contratti, cinque per i comandi più
il criterio **«stretto ma risolvibile»** di §4, l'ultimo rimasto senza
verdetto, e il difetto che misurarlo ha trovato.

🔑 **E la forma della prova cambia di nuovo, per la quarta volta.** La tacca
(ondata 3), il testimone puntato (ondata 4) e la tensione con la quota
(ondata 6) provano tutte una proprietà del **modello**. Qui si prova una
proprietà del **dataset**: che sia abbastanza teso perché un comando
diagnostico produca un verdetto non banale. Un comando che gira e dice «niente
da segnalare» è verde e non prova niente — è lo stesso rischio di §6, alla
scala del prodotto invece che a quella del builder.

🔑 **E dove il verdetto è un numero che la ricerca sceglie, la quarta forma è
l'«argomento»**: il testimone si costruisce perché il verdetto sia vero *per
costruzione*, non perché è uscito così. Due contratti di quest'ondata sono
stati riscritti proprio per questo — vedi §4 e §6.

⚠ **Il metro è sempre il Fermi**, e la ragione è quella di §1: il Fermi non è
stato progettato per superare i nostri test, quindi ciò che *non* riesce a
dire misura una lacuna vera del dataset e non un difetto del comando.

### 1. `analyze` — la classifica deve ordinare famiglie **diverse**

| | Atteso | Osservato |
|---|---|---|
| causali distinte nella classifica dell'Alighieri | **≥ 5** | ⚠ **3** a riposo, **15** sulla variante satura |
| causali distinte nella classifica del Fermi | ≤ 2 | ✅ **1**, in tre righe |
| la classifica non è dominata da `unavailability` | la prima riga è di un'altra famiglia | ✅ la prima è `subject_half_day_gap` |
| `famiglie_silenziose()` non è vuota, e il comando la dichiara | il D.T.B. c'è | ✅ dodici famiglie, `max_gap_hours` fra loro |

La ragione per cui il numero del Fermi è basso non è un difetto del comando: è
la stessa misura che apre il pezzo. Zero `ResourceTimeConstraint`, zero
`SubjectConstraint` — non c'è nessuna famiglia da ordinare. Il suo esito è
**letteralmente** la frase di §7: `{"unavailability"}`, tre righe, tre docenti.

#### ⚠ Un'attesa smentita, e la sbagliata era l'attesa — ma non del tutto

Sul dataset **a riposo** le causali sono tre, non cinque: `unavailability`,
`arrival_departure`, `break_straddled`. Cioè le sole famiglie **unarie** —
quelle che escludono una cella guardando solo l'attività che ci si prova.

🔑 **La ragione non è il dataset, ed è scritta in `domain/analysis/blame.py`:
`free_candidates` spiazza *tutte* le candidate prima di calcolare i domini.**
Su un orario in cui nessuna attività è congelata, la pressione reciproca non
esiste — l'occupazione non occupa niente, e un vincolo *fra due ore* non ha
soggetto se sono libere entrambe. La classifica dei vincoli è uno strumento
per la domanda *«il calcolo è fallito, cosa allento?»*, e quella domanda si
pone su un orario **quasi fatto**: è così che la pone EDT, ed è così che va
misurata.

Sulla variante satura — tutto congelato tranne nove occorrenze, una per unità
che porta una riga dei due assi — le causali sono **quindici**:

| | a riposo | satura |
|---|---:|---:|
| righe di classifica | 5 | **63** |
| causali distinte | 3 | **15** |
| prima riga | `unavailability` (Ricci) | **`subject_half_day_gap` (1B)** |
| attività esaminate | 343 | 9 |

L'attesa era sbagliata nel numero e giusta nella sostanza: cinque famiglie non
si vedono su un orario vuoto, e su uno pieno se ne vedono tre volte tante.

### 2. `analyze` — un deficit di Hall **vero**, in una variante satura

Il portatore è dichiarato da [aule.md](aule.md) fin dall'ondata 1: la
succursale ha **un** laboratorio e nessun ripiego, e undici ore la settimana se
lo contendono. Restringendo `LAB-SUCC` con l'indisponibilità **rossa** fino a
lasciarne meno di undici, il teorema di Hall in forma deficitaria deve
nominarlo.

| | Atteso | Osservato |
|---|---|---|
| `analyze_hall` sul dataset base | **nessun** finding: il banco è teso ma risolvibile | ✅ vuoto |
| con `LAB-SUCC` ridotto sotto le undici celle | ≥ 1 finding, con `LAB-SUCC` fra le risorse | ✅ **1**, risorsa satura `LAB-SUCC` |
| il deficit dichiarato | = ore richieste − celle superstiti | ⚠ **no**: 9h00 contro 8h00 su **nove** attività |

#### ⚠ Un'attesa smentita, e la sbagliata era l'attesa

Undici ore e otto celle darebbero tre ore di deficit; il comando ne dichiara
**una**, su un gruppo di **nove** attività. Non è un errore per difetto: il
certificato di Hall è un **insieme deficiente minimale**, non un totale — la
riduzione toglie dal gruppo ogni attività che può stare altrove, e quel che
resta è il sottoinsieme che *dimostra* l'impossibilità.

🔑 **Ed è il verdetto più utile dei due.** «Mancano tre ore» non dice dove
guardare; «queste nove attività hanno in comune otto ore di finestra» nomina
il gruppo da spezzare. Un totale sarebbe un numero più grande su un insieme
più grande, cioè un consiglio peggiore.

⚠ **La prima riga è un atteso, non un contorno**: un dataset che desse un
deficit di Hall *a riposo* sarebbe un dataset rotto, non un dataset teso.

### 3. `Estrai` — almeno un'attività per ciascuno dei sei rilevatori

Serve una **variante guasta**, e i sei guasti si scrivono uno per uno perché
nessun orario sano li produce insieme. Cinque si iniettano; il sesto è
naturale, ed è quello che dice qualcosa sul prodotto.

| Rilevatore | Come lo si produce | Atteso | Osservato |
|---|---|---|---|
| `problemi_di_aule` | **niente**: fase 1 lascia 73 richieste da assegnare | ≥ 1 | **73** |
| `a_cavallo_dell_intervallo` | un blocco da due ore che parte all'ultima fascia della mattina | ≥ 1 | 1 |
| `fuori_griglia` | un blocco da due ore che parte all'ultima fascia del giorno | ≥ 1 | 1 |
| `problemi_di_sede` | due attività dello stesso docente, nelle due sedi, in fasce adiacenti | ≥ 1 | 2 |
| `non_conformi_ai_piani_di_studi` | si cancella un'attività: il monte ore non torna più | ≥ 1 | 3 |
| `non_rispettano_i_vincoli` | i guasti qui sopra bastano | ≥ 1 | **36** |

⚠ E nessuno dei sei è **muto** — cioè in nessuno la violazione esiste senza
un'attività da nominare. È il caso che `Rilevamento.muto` esiste per
distinguere, e su questo orario non si presenta.

🔑 **Il primo rigo è il più interessante**: un orario appena calcolato è
*sempre* «con problemi di aule» finché non gira la seconda fase. Non è un
guasto — è la forma a due fasi del prodotto, che il rilevatore vede.

### 4. `place_and_fix` — un'imposizione che costa **più di una** attività

Sul Fermi ne costa **una**, ed è la misura che §7 chiama insufficiente: con una
sola attività spostata il minimo lessicografico di `moved` non è messo alla
prova. Sull'Alighieri il portatore è la succursale — laboratorio unico, e le
tre ore d'informatica inchiodate al mercoledì pomeriggio.

| | Atteso | Osservato |
|---|---|---|
| l'imposizione scelta | `ok`, e `len(moved)` **≥ 2** | ✅ **3**, zero scartate |
| il rendiconto del comando | nomina le attività ricollocate, una per riga | ✅ `Attività ricollocate (3)` |

🔑 **E il testimone è un argomento, non una misura fortunata.** Si cerca una
cella dove due attività *diverse* confliggono con la terza — una per la
classe, una per il docente — e allora `len(moved) >= 2` è vero per
costruzione: entrambe devono sgomberare, e nessun ottimo può evitarlo. Il
numero **3** è invece ciò che la ricerca ha trovato, e non si asserisce.

⚠ La prima esplorazione impose otto attività della succursale su celle
occupate e ottenne **2** ogni volta: un dato incoraggiante e non una prova,
perché la cella bersaglio veniva da un calcolo precedente e sarebbe cambiata
alla prossima esecuzione.

### 5. `solve --popolazione` — il tetto che **morde**

Il contratto di §7 è per differenza, e non poteva essere altro: *alzare la
tolleranza cambia il risultato*. Con un tetto che non morde, i due valori
coincidono e l'arbitrato è decorativo.

| | Atteso | Osservato |
|---|---|---|
| `tolleranza 0` | i buchi dei docenti restano **peggiori** che con tolleranza alta | ⚠ **no**: zero, dimostrato, a ogni tolleranza |
| `tolleranza` alta | il valore scende, e la popolazione sacrificata peggiora | ⚠ **no**: non c'era da scendere |
| il rendiconto | dichiara base e tetto per ogni criterio sacrificato | ✅ |

⚠ **Due criteri, non i sei del dataset**, ed è una scelta dell'ondata 6 già
pagata: i livelli che non dimostrano l'ottimo si fermano al valore che la
ricerca *ha trovato*, e un test che li confrontasse misurerebbe la ricerca. I
`gaps` chiudono l'ottimo in un secondo — sono l'unico genere su cui una
differenza fra due esecuzioni è una proprietà del modello.

#### ⚠ Un'attesa smentita, e la sbagliata era il **dataset**

Sei configurazioni misurate — le due popolazioni, tolleranze da 0 a 6000, e la
base portata a zero da una prima ottimizzazione — e in **tutte** i buchi della
popolazione ottimizzata scendono a zero e lo dimostrano. Il tetto di
non-regressione non morde perché **non c'è competizione**: quaranta fasce per
ventinove ore di lezione lasciano a ciascuna popolazione abbastanza spazio da
non togliere niente all'altra.

| popolazione ottimizzata | tolleranza | base del sacrificato | esito |
|---|---:|---:|---|
| docenti | 0 / 60 / 600 | `gaps_classes` 7500 | `gaps_teachers` **0**, dimostrato |
| classi | 0 / 600 / 6000 | `gaps_teachers` 4380 | `gaps_classes` **0**, dimostrato |
| docenti, dopo aver azzerato le classi | 0 / 120 / 1200 | `gaps_classes` **0** | `gaps_teachers` **0**, dimostrato |

⚠ **E la strada del criterio non dimostrato è stata provata e scartata**, che
è il modo in cui l'ondata 6 si paga due volte: sacrificando
`free_half_days_teachers` i valori sono usciti 121 / 122 / 124 al crescere
della tolleranza — cioè nella direzione **sbagliata**, con un divario di
oltre cento. Non è un difetto: è un livello che non dimostra il proprio
ottimo, e la differenza fra due sue esecuzioni non dice niente sul modello.

🔑 **La risposta è la terza forma di verifica dell'ondata 6: si mette il
dataset in tensione.** Tre pezzi, ognuno necessario:

1. la base si porta a **zero** con un primo arbitrato sulle classi — che è
   letteralmente il primo dei due comandi di EDT;
2. la classe 1A si rende **indisponibile** alla seconda fascia del lunedì
   *prima* di quel calcolo, così l'orario di partenza resta legale. ⚠
   Invertire i due passi dà `base: None`, ed è il modo corretto in cui
   `_valori_di_base` dice *«l'orario di partenza non è rappresentabile in
   questo modello»*;
3. si **puntano** due ore di italiano ai due lati del buco, con lo stesso
   `pinned` dell'ondata 4.

| tolleranza | tetto | atteso | osservato |
|---:|---:|---|---|
| 0 | 0 | `INFEASIBLE` | ✅ |
| 60 | 60 | `INFEASIBLE` — **la riga che porta l'informazione** | ✅ |
| 180 | 180 | `FEASIBLE` | ✅ |

🔑 Il buco vale 60 minuti per **tre chiavi** — la classe e le sue due parti,
IRC e alternativa — quindi 180. È la stessa aritmetica del difetto **L7**, e
la stessa forma della quota dell'ondata 6: *una tolleranza «più di zero» non
basta, deve essere quella giusta.*

### 6. `assign_rooms` — la contesa che il gruppo di aule risolve

Il Fermi la misura già: senza `structural:room_pool` la fase 2 rinunciava a
**8 aule su 92**, e ADR-021 le ha recuperate. La domanda dell'ondata 7 è se
l'Alighieri porti la stessa contesa.

| | Atteso | Osservato |
|---|---|---|
| fase 1 **senza** il builder del gruppo di aule → fase 2 | ≥ 1 rinuncia | ✅ **1** su un calcolo libero |
| fase 1 **con** il builder → fase 2 | **0** rinunce, 73 su 73 | ✅ |
| il deficit misurato | = il numero di rinunce, come sul Fermi | ✅ |

⚠ **Se l'atteso della prima riga è smentito**, la smentita è del **dataset** e
non del motore: vorrebbe dire che l'Alighieri non ha una contesa d'aule con più
di una candidata abbastanza stretta, e la risposta è stringerla, non
riscrivere l'attesa.

🔑 **Ma il calcolo libero non è la prova, ed è la lezione dell'ondata 4 di
nuovo.** «Una rinuncia» su un solve senza pin è una proprietà dell'ottimo che
la ricerca ha scelto — la seconda esecuzione ne ha date **due**. Il testimone
è invece **puntato**: tre ore di fisica su classi e docenti tutti diversi,
imposte sulla stessa cella. Le loro candidate sono le stesse due aule, quindi
il principio dei cassetti dice che non ci stanno.

| | con `structural:room_pool` | senza |
|---|---|---|
| fase 1 | **`INFEASIBLE`** | `OPTIMAL`, zero scarti |
| fase 2 | — | ≥ 1 rinuncia, fra le tre puntate |

Il secondo ramo non è decorativo: senza, un `INFEASIBLE` dovuto a qualunque
altra ragione sembrerebbe una prova.

### 7. `assign_rooms` — la rinuncia **inevitabile**

L'altra metà, e la più importante: la rinuncia esiste come stato ammesso, e un
dataset che non sappia produrla non prova che il modello la ammetta.

| | Atteso | Osservato |
|---|---|---|
| un'attività **immobile** in una cella dove le sue candidate sono tutte rosse | 1 rinuncia | ✅ 72 su 73 |
| fase 1 in quella configurazione | tace, ed è corretto: non è una sua decisione | ✅ `OPTIMAL`, zero scarti |

⚠ **E la fase 1 non tace su tutto: tace sulla cosa giusta.** Senza il
ricalcolo le rinunce sono **due**, perché un'altra ora di laboratorio stava in
quella cella; il gruppo di aule conta zero posti e la manda altrove. Le due
condotte sono opposte e sono entrambe corrette — sulle libere agisce, e
sull'immobile no, perché lì non c'è niente da decidere.

🔑 **La seconda riga è il vero contenuto.** `RoomPoolBuilder` esce quando
nessuna delle attività in causa è libera (*«un fatto, non una decisione»*):
qui la si mette alla prova, perché la configurazione è illegale e nessun
piazzamento la può riparare.

### 8. «Stretto ma risolvibile», il criterio di §4

L'ultimo criterio della spec rimasto senza verdetto, e tre file del banco lo
rimandavano qui: *«la fase 1 chiude `OPTIMAL` con zero scarti, ma togliendo una
sola aula o un solo docente comincia a scartare»*. Le ondate 3-6 lo hanno
verificato **famiglia per famiglia**; qui si verifica sul dataset intero.

| risorsa spenta | atteso | osservato |
|---|---|---|
| `LAB-SUCC`, il laboratorio unico della succursale | scarta | ✅ **11** scarti, cioè le attività che lo chiedono |
| `RICCI`, lo spezzone da tre ore | scarta | ✅ **3** |
| `COLOM` / `VITAL` | scarta | ✅ 12 / 20 |
| `LAB-INF`, `AUL-DIS`, `A101`, `AULA-MAGNA` | — | 0 scarti, ed è corretto |

⚠ **«Una» aula, non «qualunque»**: l'aula magna non la usa nessuno, e toglierla
non deve costare niente. Il criterio dice che il banco ha un punto in cui è
teso, e i punti si misurano.

🔑 **E il criterio è soddisfatto senza portare al bordo né il D.T.B. né la
tacca dei divieti**, che è la cosa da capire: sono **due nozioni diverse di
«stretto»**. Questa è stretta rispetto alle **risorse** — togline una e
qualcosa cade. La contiguità che il D.T.B. chiede è stretta rispetto alla
**densità della griglia**: quaranta fasce contro cattedre da 10–21 ore la
rendono gratis, e per negarla servirebbe una griglia più corta, cioè un altro
banco. I due test che asseriscono l'`OPTIMAL` restano quindi verdi e restano
giusti, e la frase «diventerà rosso all'ondata 7» che li accompagnava era
sbagliata — l'ondata 7 stringe le risorse, non la griglia.

### 9. ⚠ E misurando il bordo il banco ha trovato il suo quinto difetto: **L8**

Spegnendo la **palestra** il modello non scarta: risponde `INFEASIBLE`, che è
ciò che `allow_unplaced=True` dovrebbe rendere impossibile.

| | osservato |
|---|---|
| palestra spenta | **`INFEASIBLE`**, zero scarti |
| la stessa, tolta la riga `free_guaranteed` | `OPTIMAL`, **10** scarti |

La causa è **una sola riga**, isolata togliendone dieci una per volta:
`free_guaranteed` su P01 Zanetti, il docente di scienze motorie. Con la
palestra spenta gli restano le sole ore della succursale, e il solver ne piazza
**una**, su **un** giorno. La riga chiede due giornate libere — che ci sono — e
due **mezze** giornate libere, che non ci sono: una mezza giornata libera conta
solo su un giorno **lavorato** (`libera = attivo AND NOT meta`), perché è così
che la conta `FreeGuaranteedChecker`, e un giorno interamente vuoto contribuisce
zero. Con un giorno lavorato il massimo è uno.

🔑 **È l'immagine speculare della trappola che il builder documenta**, e non è
un errore del builder: contare le mezze libere su tutti i giorni accetterebbe
orari che il checker boccia, cioè la direzione sbagliata. Il fatto nuovo è la
**conseguenza**: una famiglia che conta una quantità *sui giorni in cui si
lavora* può diventare insoddisfacibile **perché si lavora meno**, e lì lo
scarto non è una via d'uscita. Un prodotto che risponde `INFEASIBLE` invece di
«queste dieci attività non si piazzano» dà all'utente la diagnosi peggiore
delle due.

Non riparato (spec §8), fissato da un test col suo ramo di controllo, aperto
come **L8** in [`docs/todo.md`](../../docs/todo.md).
