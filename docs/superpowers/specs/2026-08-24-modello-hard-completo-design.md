# Il modello hard completo — design

**Data.** 2026-08-24
**Stato.** Approvato in sessione, sezione per sezione.
**Precede.** Il piano di implementazione (sette ondate, vedi §6).
**Segue.** Lo spike CP-SAT ([spec](2026-08-09-solver-cpsat-spike-design.md),
merge `060336b`), che ha tradotto cinque vincoli su ventisette.

---

## 0. Perché questa spec, e perché non copre tutto

Lo spike ha dimostrato che i predicati di `domain/analysis/` e i builder di
`domain/solver/` possono vivere sullo stesso registro, e ha lasciato ventidue
famiglie non tradotte più quattro sottosistemi. Messi insieme sarebbero una
spec sola solo di nome.

La decomposizione decisa è in **quattro pezzi**:

| | pezzo | dipende da |
|---|---|---|
| **1** | **Il modello hard completo** — ADR-018 e i 21 builder | — |
| 2 | L'assegnazione delle aule come variabile di decisione | niente |
| 3 | Alleggerimenti a quota e ottimizzazione lessicografica | **1** |
| 4 | Il violatore di Hall | niente (non usa il solver) |

Questa spec copre **il pezzo 1 e nient'altro**. Il 2 e il 4 sono indipendenti e
possono essere affrontati in qualsiasi momento; il 3 richiede che il modello
hard sia completo, perché non si può allentare un vincolo che non è stato
modellato.

**Il conto esatto è 21, non 22.** `structural:coverage` non ha un builder — la
ragione è in §4.4, ed è una conclusione, non una dimenticanza.

## 1. Le decisioni prese prima di scrivere

Tre decisioni sono state prese in sessione e vincolano tutto il resto.

**1.1 — L'input sporco non blocca il solver** ([ADR-018](../../decisioni.md)).
Quando un vincolo mescola attività congelate già in violazione e attività
libere, il constraint si posta comunque, sui soli letterali liberi, con il
tetto ridotto e clampato a zero. Il criterio di riuscita diventa
**differenziale**. La forma operativa è in §2.

**1.2 — Conservativo ammesso, ma con la direzione dimostrata.** Un builder può
postare un vincolo più stretto del proprio checker, a condizione che la spec
**dimostri** che lo scarto va in quella direzione, invece di dichiararlo. Mai
un orario illegale; al più si perdono soluzioni legali.

Il motivo di questa cautela è storico e va scritto: nello spike la stessa
frase — «questa semplificazione è conservativa» — è stata asserita tre volte e
si è rivelata falsa una volta su tre, sempre perché nessuno l'aveva
controllata contro il checker. La regola non è «non semplificare»: è
**dimostrare il verso**. Il §4 la rende eseguibile invece che testuale.

**1.3 — Se il Fermi cade, si diagnostica.** Con tutti e ventisette i vincoli
attivi il Fermi può rispondere `INFEASIBLE` — il triennio ha 30 ore su una
griglia di 30 fasce, e gli alleggerimenti stanno nel pezzo 3. In quel caso
l'ultimo compito del piano è usare `manage.py analyze` e l'analisi di capienza
per dire **quale famiglia** rende infattibile l'istanza. Serve a distinguere
«il dataset è sovravincolato» da «un builder mente», che è la domanda che
conta.

## 2. Il vocabolario delle variabili derivate

### 2.1 Il problema

Ventuno builder hanno bisogno delle stesse costruzioni intermedie. Due esempi
concreti: `MAX_PRESENCE` e `ARRIVAL_DEPARTURE` ragionano sulla prima e
sull'ultima fascia occupata, che è esattamente il trittico
`before`/`after`/`covered` già scritto dentro `MaxGapBuilder`; sei vincoli di
materia ragionano su «la materia A occorre in quel secchio», che è la stessa
somma indicata.

Se ogni builder si costruisce le proprie variabili, la stessa codifica non
banale viene riscritta più volte — cioè viene riscritta più volte proprio la
costruzione che in questo progetto è già stata sbagliata una volta. E un
difetto si corregge in tanti posti quanti sono i consumatori.

### 2.2 La soluzione

Un modulo `domain/solver/vocabulary.py` con una classe `Vocabulary`, costruita
insieme al contesto e raggiunta come `ctx.vocab`. Ogni primitiva è **memoizzata
sulla chiave completa, firma di settimana inclusa**, esattamente come
`SolverContext.occupied()` fa già oggi.

| primitiva | cosa vale | consumatori |
|---|---|---|
| `occupied(key, day, slot, sig)` | la chiave è occupata in quella cella | tutte le cardinalità |
| `covered(key, day, span, sig)` | la fascia sta fra la prima e l'ultima occupata **dentro `span`** | `MAX_GAP_HOURS`, `MAX_PRESENCE` |
| `day_active(key, day, sig)` | la chiave lavora quel giorno | `MIN_DISTRIBUTION`, `MAX_PRESENCE`, `FREE_GUARANTEED` |
| `half_active(key, half, sig)` | la chiave lavora quella mezza giornata | `MAX_HALF_DAYS`, `FREE_GUARANTEED` |
| `subject_day(keys, subject, day, sig)` | la materia occorre in quella giornata sull'unità | `SAME_DAY`, `TWO_DAYS` |
| `subject_half(keys, subject, half, sig)` | idem per mezza giornata | `SAME_HALF_DAY`, `IMPOSED_SUCCESSION`, `HALF_DAY_GAP` |
| `pos(activity)` | intero `giorno × fasce_per_giorno + fascia`, canalizzato da `x` | `WEEKLY_ORDER` |
| `site_at(key, day, slot, sig)` | la sede occupata in quella cella | `MAX_SITE_CHANGES`, `structural:site_transition` |

### 2.3 Il parametro `span`, e perché non è cosmetico

Oggi `covered` vive dentro `MaxGapBuilder` ed è calcolato **per mezza
giornata**, perché il D.T.B. non conta mai buchi a cavallo del pranzo.

`MAX_PRESENCE` ha bisogno della stessa costruzione **sulla giornata intera**:
`_presence_minutes` in `checkers/time_constraints.py` calcola
`(slots[-1] - slots[0] + 1) * sm` sui slot di tutto il giorno, senza passare da
`_halves`.

Sono due cose diverse che si somigliano abbastanza da essere confuse.
Parametrizzare `covered` sullo `span` rende la differenza **un argomento
visibile alla chiamata**, invece di due copie divergenti in due file.

### 2.4 Conseguenza sul contesto

`vocabulary.py` accoglie `occupied()`, che oggi sta in `context.py`.
`SolverContext` scende a circa 100 righe e torna a essere solo stato: ciò che i
builder **leggono**, non ciò che i builder **costruiscono**.

## 3. ADR-018 nel modello

### 3.1 La regola, nella forma giusta

I letterali delle attività congelate sono **costanti al momento della
costruzione**: una congelata ha `ctx.cells[aid]` di cardinalità uno, riceve
comunque `AddExactlyOne`, quindi si sa già in quale cella cade. Di conseguenza
ogni espressione lineare del modello si spezza **esattamente** in «parte
costante + parte libera», e da lì discendono due casi e non ventuno giudizi.

**Sui tetti.** `costante + libere ≤ tetto` equivale a
`libere ≤ tetto − costante`. Quel residuo **può essere negativo**, ed è
esattamente il caso in cui le congelate sono già in violazione: ADR-018 impone
di clamparlo a zero invece di lasciare il modello infattibile. Le libere
semplicemente non possono aggiungere nulla lì.

```
Σ (peso × letterale) sui soli letterali liberi  ≤  max(0, tetto − consumo delle congelate)
```

**Sui minimi garantiti.** `costante + libere ≥ soglia` equivale a
`libere ≥ soglia − costante`, che **non è mai infattibile per colpa del
passato**: se le congelate già bastano, il requisito è vacuo. Nessun clamp,
nessun rischio. Tre dei sette vincoli orari (`MIN_DISTRIBUTION`,
`ARRIVAL_DEPARTURE`, `FREE_GUARANTEED`) sono minimi, non tetti.

**Sulle implicazioni e sull'ordine.** I vincoli che vietano una combinazione
(`¬(P ∧ Q)`), le successioni, gli ordinamenti: si postano se **almeno un**
letterale è libero; se sono tutti congelati non si postano, perché il vincolo
è un fatto e non una decisione. È la regola già in vigore nello spike, estesa
al caso misto — dove oggi si posterebbe comunque, ed è il buco che ADR-018
chiude.

### 3.2 L'helper

Un solo helper, `residual_cap(ctx, terms, cap) → (letterali_liberi,
tetto_residuo)`, in `domain/solver/residual.py`. I builder di cardinalità lo
chiamano; nessuno rifà il conto a mano. Un builder che calcolasse il residuo
per conto proprio è un difetto da segnalare in review.

### 3.3 L'oracolo differenziale

Il criterio di riuscita non è più «zero finding `HARD`», ma:

> l'insieme dei finding `HARD` **dopo** il solve è **contenuto** in quello
> **prima**.

Contenuto, non uguale: il solver può anche **riparare** una violazione
preesistente spostando un'attività libera, e quello è un successo, non una
discrepanza. I finding preesistenti restano visibili — non vengono nascosti,
solo non attribuiti al solver.

## 4. I ventuno builder

Ogni riga qui sotto è stata derivata **leggendo il checker corrispondente**,
non ricordandone la semantica. È la contromisura diretta ai tre difetti dello
spike, tutti nati da un piano che ragionava a memoria su cosa un vincolo
facesse.

### 4.1 I sette vincoli orari

| vincolo | traduzione | forma |
|---|---|---|
| `MAX_HOURS` | `Σ occ ≤ cap` per giornata, mattina e pomeriggio | tetto |
| `MAX_PRESENCE` | `Σ covered(span = giornata) × sm ≤ cap`; più `Σ day_active ≤ max_days` | tetto |
| `MAX_HALF_DAYS` | `Σ half_active ≤ cap`; più `¬(mattina ∧ pomeriggio)` per giorno se `only_half_day_per_day` | tetto |
| `MIN_DISTRIBUTION` | `qualifies[d]` reificato su `Σ occ × sm ≥ soglia`, poi `Σ qualifies ≥ min_days` | minimo |
| `ARRIVAL_DEPARTURE` | `compliant[d]` = nessuna occupazione nella zona proibita; `Σ compliant ≥ days` | minimo |
| `FREE_GUARANTEED` | `Σ ¬day_active ≥ n`; e `free_half[d,h] = ¬half_active[d,h] ∧ day_active[d]` | minimo |
| `MAX_SITE_CHANGES` | `change[s,t]` = occupata in `s` e in `t` con sedi diverse e **tutto vuoto in mezzo** | tetto |

Tutti e sette **esatti**.

**⚠ `FREE_GUARANTEED` è la trappola grossa, ed è la stessa forma del D.T.B.**
`FreeGuaranteedChecker` conta le mezze giornate libere **solo sui giorni che
hanno attività** (`for day, slots in days.items()`): un giorno completamente
vuoto contribuisce **zero**, non due. Sommare `¬half_active` su tutte le mezze
giornate produrrebbe *più* mezze giornate libere, renderebbe `≥ soglia` *più
facile*, e farebbe **accettare orari che il checker boccia** — la direzione
sbagliata. Da qui il termine `∧ day_active[d]`, che non è un dettaglio ma il
vincolo stesso.

**⚠ `MAX_PRESENCE` usa la giornata intera**, non la mezza giornata: vedi §2.3.
Sbagliare `span` qui produce un vincolo più largo del checker.

**`ARRIVAL_DEPARTURE` si semplifica da sola.** «La prima fascia è ≥
`not_before`» equivale a «nessuna occupazione prima di `not_before`»;
«l'ultima è < `not_after`» a «nessuna occupazione da `not_after` in poi». Non
serve alcuna variabile di primo o ultimo, e il giorno vuoto risulta conforme
gratis — che è ciò che il checker fa esplicitamente con `compliant += 1`.

**`MAX_SITE_CHANGES` costa poco.** L'encoding «tutto vuoto in mezzo» è
O(fasce²) booleani per (chiave, giorno): con `slots_per_day = 6` sono quindici
coppie al giorno. Trascurabile.

### 4.2 I dodici vincoli di materia

**Cinque meccanici**, stesso pattern di `SAME_DAY_INCOMPATIBLE` già tradotto:

- `SAME_HALF_DAY_INCOMPATIBLE` — identico a `SAME_DAY`, secchio diverso.
- `MAX_HOURS_DAY`, `MAX_HOURS_HALF_DAY` — somme pesate contro `row.param`,
  con il residuo di §3.
- `TWO_DAYS_INCOMPATIBLE` — `¬(subject_day[A,d] ∧ subject_day[B,d+1])`.
- `FORBIDDEN_SEQUENCE` — proibizione di coppie di celle: B che inizia
  esattamente dove A finisce, stesso giorno.

**Sette d'ordine**, e nessuno richiede di ordinare davvero:

- **`WEEKLY_ORDER`** — `min(pos su A) ≤ min(pos su B)` con `AddMinEquality`.
  ⚠ Il checker esce senza vincolare in **due** casi, non uno:
  `if row.subject_a_id == row.subject_b_id or not a or not b: return`. Cioè
  anche quando **A = B** — che nelle altre dodici famiglie è il caso dominante.
  Entrambi si conoscono staticamente e si saltano a build time. Esatto.
- **`IMPOSED_SUCCESSION`, A = B** — «gli scarti fra occorrenze consecutive ≤
  `delay`» si esprime senza ordinamento: per ogni coppia di mezze giornate
  `u < v` con `v − u > delay`, vieta
  `subject_half[u] ∧ subject_half[v] ∧ (nessuna occorrenza fra le due)`.
  Su dieci mezze giornate sono 45 coppie. Esatto.
- **`IMPOSED_SUCCESSION`, A ≠ B** — per ogni occorrenza di A a `ha` serve una B
  in `(ha, ha + delay]`: un OR reificato su `subject_half` di B. Esatto.
- **I quattro `PARTS_*`** — `before` è, per ogni coppia (attività di parte `p`,
  attività di classe `c`) nello stesso secchio, `fascia_p ≤ fascia_c`;
  l'uguaglianza è impossibile perché parte e classe condividono i token di
  occupazione. `after` specularmente. I due omogenei — che differiscono
  soltanto per il secchio, giornata contro mezza giornata — chiedono «≤ 1
  transizione nella sequenza di etichette», che equivale a «tutte le parti
  prima di tutte le classi **oppure** tutte le classi prima di tutte le
  parti»: un booleano per (riga, secchio) e le due implicazioni. Tutti e
  quattro esatti.
- **`HALF_DAY_GAP`** — l'unico dei dodici dove serve il conservativo.

#### La dimostrazione per `HALF_DAY_GAP`

`HalfDayGapChecker` non vincola tutte le coppie: ordina le occorrenze e
vincola le **coppie consecutive nell'ordinamento**, e con A ≠ B soltanto
quelle a cavallo fra le due materie (`crossed = same or s1 != s2`).

Il builder vincola invece **tutte** le coppie incrociate.

*Direzione.* L'insieme delle coppie consecutive incrociate è un sottoinsieme
dell'insieme di tutte le coppie incrociate. Un piazzamento che soddisfa il
vincolo su **tutte** le coppie lo soddisfa in particolare sulle consecutive.
Quindi ogni soluzione accettata dal modello è accettata dal checker: il
modello è **più stretto, mai più largo**. ∎

### 4.3 I due strutturali

- **`structural:didactic_weight`** — somme pesate per mattina, pomeriggio,
  giornata e settimana su ciascuna **unità-studente** (le parti nei token, o
  la classe se non ha partizioni). Il peso di un'attività è
  `subject.didactic_weight × duration_slots`, cioè una **costante nota a build
  time**: il vincolo è cardinalità pura col residuo di §3. Esatto.

  ⚠ Due dettagli che il checker ha e che è facile perdere. Il tetto
  **settimanale** non è quello d'istituto se la classe ne dichiara uno proprio:
  `class_caps[part_class[key]]` prevale su `settings.max_weight_week`, e si
  ricade sull'istituto solo se è `None`. E **ogni tetto `None` è spento**, non
  zero — in una base reale del prodotto tutti e quattro sono a `nessuno`, il
  che significa che questo builder sul Fermi non posterà nulla. Va bene così:
  il generatore a testimone (§5.1) accende i tetti apposta.
- **`structural:site_transition`** — il secondo conservativo.

#### La dimostrazione per `site_transition`

`SiteTransitionChecker` costruisce la sequenza delle occupazioni con sede nota
e vincola le **coppie consecutive** in quella sequenza. Il builder vincola
tutte le coppie.

*Direzione.* Per una coppia lontana, `s₂ − s₁ − 1 ≥ needed` è già vero e il
vincolo è vacuo; le righe effettive si aggiungono solo sulle coppie vicine, che
includono tutte le consecutive. Quindi il modello è più stretto, mai più
largo. ∎

### 4.4 Il ventiduesimo, che non si scrive

`structural:coverage` **non ha un builder**, e non è una dimenticanza.
`CoverageChecker` dichiara `PLACEMENT_INDEPENDENT = True`: confronta le
attività esistenti con i servizi dei piani di studi e non guarda **mai** dove
le attività sono piazzate. Il solver non crea né distrugge attività, quindi
non c'è alcuna decisione da vincolare.

Resta un predicato utile — è il test anti-inversione STO/SCI — ma vive
interamente nell'analisi. Va scritto qui perché al prossimo censimento «21 su
22» non sembri un lavoro lasciato a metà.

### 4.5 Il bilancio

Dei ventuno builder, **diciannove sono esatti**. Il permesso di essere
conservativi, concesso in §1.2, serve **due volte**, e in entrambi i casi la
dimostrazione sta in tre righe. È molto meno di quanto la decisione lasciasse
temere.

## 5. Il criterio di riuscita e i test

### 5.1 Il generatore a testimone

Il meccanismo centrale, e risolve insieme due problemi finora affrontati a
mano. Per ogni famiglia:

1. si genera **un orario valido a caso**;
2. si derivano da quell'orario le righe di vincolo che esso **soddisfa**;
3. si chiede al solver di trovare un orario da zero.

L'orario di partenza è un **testimone**: prova che una soluzione esiste. Da
qui due asserzioni:

- se il solver risponde `INFEASIBLE` è un **fallimento duro** — c'era un
  testimone;
- se risponde con una soluzione, quella soluzione riapplicata e riletta da
  `check_schedule` non deve produrre alcun finding `HARD` **nuovo** di quella
  famiglia (§3.3).

Le due direzioni sono coperte da un test solo.

**E l'oracolo non può diventare vacuo.** Senza il testimone, un builder che
postasse `1 == 0` renderebbe ogni istanza infattibile e passerebbe per sempre
qualunque test che si accontenti di «se c'è una soluzione, allora è pulita».
Con il testimone fallisce al primo colpo. È la generalizzazione sistematica di
`test_oracolo_puo_fallire`, che oggi copre a mano due famiglie su cinque.

### 5.2 Il conservativo entra nel generatore, non nei commenti

Per le due famiglie dichiarate conservative in §4.2 e §4.3, il testimone si
genera contro la regola **più stretta**, quella del modello, non contro quella
del checker. Così il testimone resta valido per entrambi, e la differenza fra
le due regole è scritta in **codice eseguibile** invece che in una nota di
spec.

È ciò che «direzione dimostrata» (§1.2) deve significare in pratica: la
dimostrazione in §4.2 e §4.3 è per il lettore, il generatore è per la macchina.

### 5.3 Le firme di settimana sono una dimensione del generatore

Le maschere delle attività si randomizzano insieme al resto, così ogni famiglia
esercita più di una firma di settimana fin dal primo test.

Questo è deliberato. Il difetto del D.T.B. trovato in review il 2026-08-24 è
passato **proprio** perché tutti i banchi di prova avevano un'unica firma — la
scuola giocattolo, il Fermi per una classe e il Fermi intero, tutti con ogni
attività annuale — e la riparazione è stata un test scritto a mano *dopo*. Con
la varietà di firme dentro il generatore, nessuno deve ricordarsene.

### 5.4 La copertura è verificata dal registro

Il test enumera `BUILDERS` e **fallisce su qualunque chiave priva di
generatore**. Registrare un builder senza il suo banco di prova diventa
impossibile. È lo stesso meccanismo che `domain/analysis/` già usa per
garantire la copertura dei checker.

### 5.5 Cosa deliberatamente non si testa

**L'equivalenza piena modello ⟺ checker.** La decisione §1.2 rende
l'implicazione valida in un verso solo: ogni soluzione del modello è pulita
per il checker, non il contrario. Un test di equivalenza fallirebbe
legittimamente sulle due famiglie conservative. Va scritto qui perché nessuno
lo aggiunga e poi passi una giornata a "ripararlo".

### 5.6 Il Fermi

Misurato con tutti e ventisette i vincoli attivi, e riportato qualunque cosa
risponda. Se `INFEASIBLE`, diagnosticato con `manage.py analyze` e l'analisi di
capienza per nominare la famiglia colpevole (§1.3).

## 6. Struttura dei file

```
domain/solver/
  vocabulary.py       le primitive derivate — accoglie occupied() da context.py
  residual.py         l'helper di ADR-018
  context.py          torna a essere solo stato (~100 righe)
  model.py            invariato
  registry.py         invariato
  builders/
    grid.py  unavailability.py  occupation.py        (esistono)
    time_counting.py    MAX_HOURS · MAX_HALF_DAYS · MIN_DISTRIBUTION ·
                        FREE_GUARANTEED · ARRIVAL_DEPARTURE
    time_presence.py    MAX_GAP_HOURS (si sposta) · MAX_PRESENCE
    time_sites.py       MAX_SITE_CHANGES · structural:site_transition
    subject_buckets.py  SAME_DAY (si sposta) · SAME_HALF_DAY ·
                        MAX_HOURS_DAY/HALF_DAY · TWO_DAYS · FORBIDDEN_SEQUENCE
    subject_order.py    WEEKLY_ORDER · IMPOSED_SUCCESSION · HALF_DAY_GAP
    subject_parts.py    i quattro PARTS_*
    weight.py           structural:didactic_weight
```

`builders/time_constraints.py` e `builders/subject_constraints.py`
**spariscono**: i loro due builder si spostano nel file del proprio *pattern*.

La struttura segue il pattern di traduzione, non la famiglia di vincolo.
`domain/analysis/checkers/` tiene un file per famiglia (otto checker in 197
righe, tredici in 284), ma i builder CP-SAT sono molto più prolissi dei
predicati: le stesse famiglie darebbero due file da 600–900 righe. Sette file
da 150–250 righe sono più maneggevoli, e raggruppano ciò che condivide davvero
la codifica.

Le chiavi del registro **non cambiano**: lo spostamento è puro e i test
esistenti restano.

## 7. Le sette ondate

1. **Fondamenta** — `vocabulary.py`, `residual.py`, l'oracolo differenziale, e i
   tre builder esistenti riscritti sulla nuova macchina. **Zero vincoli nuovi**:
   i 173 test verdi devono restare verdi. Un refactor a comportamento
   invariato è l'unico momento in cui una rottura è inequivocabile.
2. **Il banco di prova** — il generatore a testimone (§5.1) e l'enumerazione del
   registro (§5.4).
3. **Orari** — i sette di §4.1.
4. **Materia meccanici** — i cinque di §4.2.
5. **Materia d'ordine** — i sette di §4.2.
6. **Strutturali** — i due di §4.3.
7. **Il Fermi** — misura, e diagnosi se cade (§5.6).

**Perché il banco di prova sta prima dei builder.** L'ondata 2 non ha nulla da
testare nel momento in cui la si scrive, il che è scomodo. La alternativa —
generatore insieme al primo gruppo di builder — è più comoda e ha un difetto
preciso: chi scrive il test dopo aver scritto il builder tende a scrivere il
test che il builder passa. La scomodità è il prezzo dell'indipendenza fra
l'oracolo e ciò che deve giudicare.

## 8. Fuori scope, dichiarato

- **L'aula come variabile di decisione** — pezzo 2. Oggi l'aula è un token
  fisso sull'attività; renderla decidibile è l'unico cambio di *encoding*
  rimasto, e tocca solo `context.py` e `occupation.py`. Nessuno dei ventuno
  builder parla di aule.
- **Alleggerimenti a quota e ottimizzazione lessicografica** — pezzo 3.
- **Il violatore di Hall** — pezzo 4. Non usa il solver: è un conteggio di
  capienza sopra `domain/analysis/capacity.py`.
- **Un comando `manage.py solve`** — ha senso quando esistono gli
  alleggerimenti. Prima di quelli saprebbe dire soltanto `INFEASIBLE`.

## 9. Esito — a consuntivo

Scritto a lavoro finito, il 2026-08-25. Questa sezione **corregge** le
sezioni precedenti dove l'implementazione le ha smentite: le previsioni
restano scritte com'erano, ma qui si dice quali erano sbagliate.

### 9.1 I numeri

| | |
|---|---|
| checker nel registro | **27** |
| builder | **26** — il ventisettesimo (`structural:coverage`) non ne ha uno, ed è dichiarato |
| suite | **424 passed, 15 skipped** |
| modello completo sul banco (5 seed) | 22–23 famiglie con righe su 26, 48–73 righe, **OPTIMAL** ovunque, oracolo pulito |
| Fermi intero | 284 attività, 8140 variabili, 1082 constraint, **OPTIMAL in ~0,56 s** |

I quindici skip sono tutti vacuità misurate e attribuite, non fallimenti
mascherati.

### 9.2 ⚠ Il Fermi non misura il modello completo — misura il dataset

§5.6 dava per scontato che il Fermi fosse la prova del modello completo, e
prevedeva perfino la diagnosi in caso di `INFEASIBLE`. È sbagliato, e la
prova sta nei numeri: **8140 variabili e 1082 constraint sono esattamente
quelli dello spike a cinque vincoli** del 2026-08-09, con lo stesso tempo.

Il dataset Fermi ha **zero** righe `ResourceTimeConstraint`, **zero**
`SubjectConstraint` e i quattro tetti di peso a `None`. Delle ventisei
famiglie ne esercita cinque — griglia, indisponibilità (42 righe),
occupazione, sedi, D.T.B. — e ventuno builder non postano nulla. «OPTIMAL sul
Fermi col modello completo» è quindi una frase vera e priva di contenuto.

La misura del modello sta invece in
`tests/test_solver_witness.py::test_modello_completo`, aggiunto qui: tutte le
famiglie attive **insieme** sullo stesso testimone. Non esisteva — `test_famiglia`
prova ventisei modelli da una famiglia ciascuno, e due traduzioni corrette
separatamente possono contraddirsi una volta postate insieme.

Il Fermi resta per l'altra metà, la **scala**: 284 attività su una griglia
stretta, contro le 14–32 del banco.

### 9.3 ⚠ I derivatori non sono componibili in ordine qualunque

Trovato componendoli. Due formulazioni **dense** (Ruling 34) non osservano il
testimone, lo **riparano**, e la riparazione si vede dalle altre famiglie:

- `_derive_site_transition` riassegna la **sede** a tutte le attività — e le
  sedi sono ciò che `max_site_changes` conta;
- `_sintonizza_parti` riassegna la **materia** dell'attività di ogni parte — e
  la materia è ciò su cui ogni riga `SubjectConstraint` è ancorata.

In ordine alfabetico la composizione risponde `INFEASIBLE` su 2 seed su 3.
Entrambe le docstring dichiaravano di non disturbare nessuno: vero per il
testimone *in sé* (griglia e occupazione non cambiano), falso per le **righe
già derivate** da altri. Corrette. La precedenza è ora esplicita (`MUTANTI`):
chi ripara va per primo.

### 9.4 Esatto contro conservativo, a consuntivo

Il bilancio di §4.5 — «diciannove esatti su ventuno, il conservativo serve due
volte» — era una previsione, e va corretto in **entrambe** le direzioni.

- ⚠ **`HALF_DAY_GAP` non è conservativo: è esatto.** §4.2 lo chiama «l'unico
  dei dodici dove serve il conservativo», e il piano ne faceva il caso
  vetrina. Le due regole — coppie consecutive (checker) e tutte le coppie
  incrociate (builder) — sono **equivalenti**: se esiste una coppia incrociata
  troppo corta, ne esiste una adiacente altrettanto corta. Dimostrato, e
  verificato su 200 000 casi sintetici con zero divergenze.
- ⚠ **`MAX_GAP_HOURS` (il D.T.B.) era conservativo nel verso sbagliato**, ed è
  stato corretto il 2026-08-24 prima di questo piano: trattare tutte le
  attività come co-attive **allarga** invece di stringere, perché
  un'occupazione di un'altra firma riempie un buco che nelle settimane reali
  resta scoperto. Ora posta un budget **per firma**.
- Resta conservativo **`structural:site_transition`** (§4.3), per la ragione
  già scritta lì.

Il conto a consuntivo: **venticinque builder esatti su ventisei**, non
diciannove su ventuno. Il permesso di essere conservativi, concesso in §1.2,
è servito **una volta sola**.

### 9.5 ⚠ ADR-018 ha cinque casi, non due, e uno non è risolvibile

§3.1 dichiara «due casi e non ventuno giudizi»: tetti (clamp) e minimi
(nessun clamp). All'atto pratico i casi sono **cinque**, e la differenza non è
cosmetica. ⚠ Il quinto è stato aggiunto il 2026-08-26 dalla review finale, che
ha falsificato due affermazioni scritte qui — vedi il caso 5.

1. **Tetto separabile** — `residual_cap`, come da §3.1. È il caso più comune.
2. **Minimo garantito separabile** — §3.1 lo dà per «mai infattibile per
   colpa del passato». ⚠ **Falso**: su `ARRIVAL_DEPARTURE` una congelata in
   una fascia proibita **consuma** la quantità contata, e nessuna mossa sulle
   libere la recupera. Corretto col residuo *per forzatura*
   (`frozen_occupies`, non `residual_cap`): i termini già persi non generano
   letterali e la soglia scende a quanto resta raggiungibile.
3. **Clausola** — si posta se almeno un letterale è libero; tutta congelata è
   un fatto, non una decisione. Come da §3.1. ⚠ Con una sola congelata la
   clausola resta ed è un **divieto**, che ADR-018 concede anche quando
   produce `INFEASIBLE`.
4. **⚠ Tetto inevadibile** — non previsto da nessuna parte, e trovato al Task
   16. Il secchio **settimanale** del peso didattico contiene *tutte* le celle
   candidate di ogni attività dell'unità, quindi `AddExactlyOne` rende la
   somma dei letterali liberi una **costante**: col residuo clampato a zero il
   vincolo diventa `costante positiva ≤ 0`, falso comunque vada il
   piazzamento. Non «inagibile»: **contraddittorio**. Il clamp, che altrove è
   il trattamento corretto, qui produce esattamente ciò che ADR-018 vieta —
   misurato, `INFEASIBLE` con due congelate e una libera.

5. **⚠ Minimo non separabile** — trovato dalla review finale, e la ragione
   per cui questa sezione è stata riscritta il 2026-08-26. `MIN_DISTRIBUTION`
   e `FREE_GUARANTEED` contano una quantità che **non è una somma di
   contributi per attività** — giorni qualificanti, giorni liberi, mezze
   giornate libere — quindi il residuo non è additivo: una congelata non
   «consuma una quota», toglie gradi di libertà, e né `residual_cap` né il
   residuo per forzatura lo esprimono.
   ⚠ La versione precedente di questo elenco diceva che `FREE_GUARANTEED` era
   risolto dal caso 2 e che `MIN_DISTRIBUTION` «regge davvero». **Entrambe le
   affermazioni erano false**, e nessuna delle due si vedeva rileggendo il
   documento: sono cadute solo misurando. `MinDistributionBuilder` postava la
   soglia grezza pur avendo il controesempio scritto nella propria docstring —
   due congelate sullo stesso giorno, una libera, `min_days=3`: `INFEASIBLE`
   anche forzando lo *status quo*. `FreeGuaranteedBuilder` clampava le due
   soglie **indipendentemente**, ma i due conteggi si escludono a vicenda
   (`libera = attivo AND NOT meta` conta una mezza solo se il giorno lavora),
   quindi ciascuna era raggiungibile da sola e la congiunzione no.
   Il trattamento è la **disgiunzione reificata** già in uso su
   `WeeklyOrderBuilder` — «ripara *oppure* non peggiorare» — con le due
   soglie di `FREE_GUARANTEED` sotto **lo stesso** booleano. `B` si legge
   chiamando il checker di `domain/analysis`, mai riscrivendone la
   condizione.
   ⚠ E il ripiego, quando lo *status quo* non è rappresentabile, **non è
   simmetrico fra le due**: su `MIN_DISTRIBUTION` l'occupazione è monotona,
   quindi `B` contato su un sottoinsieme è un valore raggiungibile da ogni
   assegnazione; su `FREE_GUARANTEED` più occupazione *toglie* giorni liberi,
   quindi «`B` sulle sole congelate» è una sovrastima — è letteralmente il
   bound che causava il difetto — e il ripiego è zero.

Il criterio che unifica i cinque casi è più preciso di «tetto o minimo»:

> `INFEASIBLE` che nasce dal **vietare un peggioramento** è ammesso;
> `INFEASIBLE` che nasce dal **pretendere una riparazione** non lo è.

E dove ogni piazzamento è un peggioramento — il caso 4 — non c'è niente da
vietare: si salta.

**⚠ Una metà del caso 4 non è risolvibile da nessun builder**, e va detta.
Anche saltando il vincolo, la soluzione porta comunque il finding
`weight_week`, e la sua `Finding.key` non è quella di prima: `activities`
cresce delle libere e `quantities["weight"]` cambia. Le libere vanno
collocate, e ovunque vadano pesano. Quindi **l'oracolo differenziale a tutto
campo va formulato su una chiave più grossolana** (causale + risorsa) per le
famiglie indipendenti dal piazzamento, oppure quelle famiglie vanno dove EDT
le mette davvero: nell'**analisi di capienza**, che si esegue *prima* del
calcolo e non dentro.

Lo stesso vale, in piccolo, per la Ruling 22: `quantities` dentro
`Finding.key` rende «peggiorato» e «migliorato» entrambi finding *nuovi*.
Con `CODICI` esteso a ventisei famiglie la questione è ora reale, non teorica.

⚠ **E il fenomeno è più largo di quanto questa sezione dichiarava** (misurato
dal banco che congela, 2026-08-26 sera). Non riguarda solo le famiglie
indipendenti dal piazzamento: riguarda **ogni famiglia il cui finding nomina in
`activities` la coppia argmin o la coppia consecutiva** invece del secchio
intero — chi viola, non chi partecipa. Piazzare una libera accanto a una
congelata cambia allora *quale* coppia è l'argmin lasciando causale, risorsa e
quantità **identiche**: misurato su `subject_imposed_succession`. È la stessa
causa a monte del tie-break di `_placed_of` in «Ancora aperto» di `CLAUDE.md`.
Il banco lo tratta con una chiave grossolana **dichiarata** (`_grossa` in
`tests/solver_harness.py`), non con un'eccezione implicita.

### 9.6 Il criterio di riuscita, e quale metà lo regge davvero

`CODICI` in `tests/test_solver_oracle.py` era rimasto alle cinque famiglie
dello spike per dieci task: l'oracolo differenziale del Fermi era cieco su
ventuno famiglie su ventisei. Esteso qui, con una guardia che gli impedisce
di reinvecchiare — una causale nuova deve finire in `CODICI` oppure in
`FUORI`, per decisione esplicita.

⚠ **E il passo 3 di `run_family` è un rilevatore debole**, misurato. Il passo
dice: «qualunque soluzione il solver restituisca dev'essere pulita». Sulle
quattro famiglie `PARTS_*` le righe derivate sono violabili **118 volte su
120** — forzando la violazione, `INFEASIBLE` col builder acceso e `FEASIBLE`
con quello spento — eppure il banco, che risolve e guarda, coglie un builder
rotto **1 volta su 11**. Non sono le righe a essere vacue: è la forma. CP-SAT
non cerca la soluzione cattiva, e quasi mai la trova per caso.

Decisione sulla sonda esatta di violabilità (Rulings 65, 86, 104):
**adottata come forma dei test scritti a mano, non come criterio del banco.**

- Come **forma di test** è già la regola della casa (Ruling 85): chi dimostra
  che un vincolo morde costruisce il modello, **forza** la violazione con
  `model.Add(x[...] == 1)` e attende `INFEASIBLE`. Costo per i vincoli
  d'ordine: cinque righe, perché la condizione di violazione *è* una clausola
  sulle variabili che il builder già costruisce.
- Come **criterio di `potere`** resta esclusa, e l'obiezione della Ruling 65
  regge: richiederebbe di riesprimere in CP-SAT la condizione di violazione di
  ogni famiglia, cioè una seconda implementazione di ventisei vincoli dentro
  il banco che li verifica. E i numeri dicono che non servirebbe: le righe
  hanno già potere: è il passo 3 a non saperlo sfruttare.

Il banco resta prezioso per i suoi **altri due** passi — il passo 1 sorveglia
il derivatore, il passo 2 (`INFEASIBLE` con un testimone disponibile)
sorveglia i builder troppo stretti, ed è quello che ha trovato più difetti.

### 9.7 Debiti dichiarati

- ~~**Il banco non congela mai nulla** (Ruling 20)~~ — **chiuso il 2026-08-26
  (sera)**, e la voce resta perché quel che ha trovato conta più della voce.
  `tests/test_solver_frozen.py` congela: `run_modello_sporco` costruisce la
  premessa di ADR-018 — congelate **già in violazione**, libere da piazzare — e
  chiede due cose: che il modello **ammetta lo status quo forzato** (la prova
  che morde) e che il solve libero non introduca violazioni nuove.
  Ha trovato al primo colpo che **`SiteTransitionBuilder` non aveva il
  guardiano ADR-018** che il suo commento di modulo, e il docstring di
  `tests/test_solver_sites.py::test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca`,
  gli attribuivano: `any_free` guarda chi **tocca** le due fasce, non chi
  **realizza** la coppia di sedi vietata, e la clausola postata ha entrambi i
  letterali forzati a 1 dalle congelate. §9.8 alla tredicesima occorrenza.
  ⚠ Il banco **non sostituisce** i test scritti a mano: sul clamp di
  `residual_cap` non aggiunge un solo rosso (misurato su sette mutazioni).
  Aggiunge la sola cosa che nessuno di loro sapeva fare — trovare un difetto
  che nessuno cercava. ⚠ E la stessa misura ha **bocciato metà del banco**: un
  secondo `test_famiglia_con_congelate` su baseline pulita, 78 test e 28
  secondi, non è diventato rosso su nessuna delle sette mutazioni ed è stato
  rimosso.
- **`coverage_mismatch` sul testimone** (Ruling 102): i `Service` della
  fixture sono per (piano, materia) mentre `student_units` attribuisce il
  monte ore alle **parti**. Innocuo — `structural:coverage` non ha un builder
  e non entra mai nel modello — ma un oracolo differenziale a tutto campo sul
  banco lo incontrerebbe. Si ripara **nella fixture**.
- **Il filtro di `_coppie_di_sede`** (Ruling 39, Minor 3): la docstring
  dichiarava un'inefficacia che non ha — 8277 chiamate su 18308 filtrano
  davvero, e con le sedi correlate alle classi taglia fino al −63%. Resta non
  applicato alle fasce **intermedie**, dove sta il grosso delle variabili
  sprecate a molte sedi.
- **Due tie-break di `domain/analysis` sono artefatti dell'ordine
  d'inserimento**, non semantiche: `MaxSiteChangesChecker` e `_placed_of`.
  Vanno decisi lì prima di poter essere tradotti fedelmente. Entrambi in
  «Ancora aperto» di `CLAUDE.md`.
- **⚠ Il ramo *status quo* è pigro, e nel caso misto può spegnere la riga.**
  Riguarda l'intera famiglia dei rami disgiuntivi — `WeeklyOrderBuilder` dal
  Task 12, `MinDistributionBuilder` e `FreeGuaranteedBuilder` dal 2026-08-26.
  Il modello non ha funzione di costo: `riparato` e `riparato.Not()` sono alla
  pari, e CP-SAT non ha nessun motivo di preferire la riparazione quando anche
  lo *status quo* è soddisfacibile. Nel solve incrementale «poche congelate +
  libere non ancora piazzate» la baseline del checker è quasi sempre già
  violata — perché **nulla è piazzato** — `B` vale quanto qualificano le sole
  congelate, e il ramo *status quo* diventa **vacuo**: la riga smette di
  vincolare. Misurato: una congelata, sei libere mai piazzate, `min_days=3` —
  ammassarle tutte su due giorni è ammesso, e prima della correzione era
  vietato (al prezzo però di `INFEASIBLE` su 33 istanze sporche su 45).
  È perdita di **qualità**, non di correttezza: nessun finding nuovo,
  l'oracolo differenziale regge. ⚠ **Misurato anche dal banco che congela**
  (2026-08-26 sera) — la prima volta che questo debito si vede da solo invece
  di essere dichiarato, e in una forma più precisa: è uno **scambio**, non un
  peggioramento secco. `free_guaranteed` passa da `free_days 4 / free_half_days
  1` a `free_days 1 / free_half_days 4` — ripara la soglia delle mezze e rompe
  quella dei giorni, che era soddisfatta. Le due soglie stanno sotto lo stesso
  booleano proprio per impedirlo, ma con le libere non ancora piazzate
  `_status_quo_rappresentabile` è falso, il ramo scende a `>= 0` e scavalca il
  booleano. Il banco lo esenta **strettamente**: solo
  un peggioramento su una (causale, risorsa) già violata, mai una violazione su
  una risorsa pulita. Tre strade, nessuna adottata: `AddHint` sul
  booleano di riparazione (zero rischio semantico, meccanismo nuovo per questo
  branch); clamp sul massimo raggiungibile (non pigro, ma è una **sovrastima**
  — sarebbe il quarto «bound dichiarato conservativo e non lo è»); oppure
  dichiararlo, che è ciò che si è fatto. ⚠ Va deciso sulla **famiglia**, non
  builder per builder.

### 9.8 Il metodo, e cosa ha effettivamente trovato

La frase «questa semplificazione è conservativa» era stata asserita tre volte
e falsificata tre volte prima che questo piano cominciasse (§1.2). Il piano
stesso l'ha ripetuta: `HALF_DAY_GAP` dichiarato conservativo ed esatto, il
D.T.B. come soglia singola invece che budget, l'insieme di chiavi «sufficiente»
di ADR-017. E ne ha aggiunte di nuove: derivatori senza `return` (tre volte),
docstring che dichiarano di non disturbare nessuno, `residual_cap` dichiarato
sufficiente per ogni tetto.

Il pattern è sempre lo stesso: **il documento dichiara vera una proprietà che
si rivela falsa solo controllandola contro il checker o contro i dati, mai a
colpo d'occhio sul documento**. Le due contromisure che hanno funzionato:

1. **misurare il derivatore del piano prima di scrivere il builder** — ha
   intercettato quattro difetti fatali, ciascuno dei quali avrebbe reso una
   famiglia intera verde per non aver fatto nulla;
2. **la mutazione** — spegnere il builder e contare i rossi. Un test che non
   diventa rosso quando il codice che afferma sparisce non sta affermando
   niente.
