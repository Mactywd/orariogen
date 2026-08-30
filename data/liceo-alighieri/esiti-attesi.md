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
più densa, cioè il criterio di accettazione dell'ondata 7, non una taratura di
questa riga. Un test asserisce l'`OPTIMAL`, così diventerà rosso il giorno in
cui il banco si stringe.

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
diventerà rosso all'ondata 7.

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

## Ondate 6–7

Da scrivere prima di ciascuna, nell'ordine della spec §9: quote, criteri di
qualità e firme di settimana; poi il criterio di accettazione e i comandi.
