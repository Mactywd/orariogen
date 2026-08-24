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
