# Il violatore di Hall — design

**Data:** 2026-08-26
**Stato:** approvato in sessione, sezione per sezione
**Pezzo:** il quarto dei quattro dichiarati fuori dal piano `modello-hard-completo`
(§8 di `2026-08-24-modello-hard-completo-design.md`)

## 0. Perché questa spec, e cosa non copre

La fase 5 dell'`Analisi dei vincoli` di EDT — `Controllo dell'insieme di
attività non piazzabili` — è la funzione più sofisticata trovata nel prodotto,
ed è quella che `diagnostica.md` indica come «metà della differenza di UX che
vogliamo ottenere»: restituire *«queste 7 lezioni di 3ªA non possono stare
tutte nelle 6 fasce rimaste»* invece di `INFEASIBLE`.

Non usa il solver. È un conteggio di capienza, e vive sopra `domain/analysis`.

**Non copre**: il riquadro `Soluzione` operativo di EDT (la griglia delle
indisponibilità modificabile sul posto con `Rilancia la verifica`) — è UI, e in
questo repository non c'è UI. Vedi §8.

## 1. Le tre decisioni prese prima di scrivere

**1.1 — La fase 5 sta accanto alla fase 4, non al posto suo.** `capacity.py`
non si tocca. Le due fasi rispondono a domande diverse: la 4 attribuisce la
colpa a una *famiglia di vincoli*, disabilitandola e rimisurando; la 5 nomina
un *insieme di risorse*. Unificarle costringerebbe al minimo comune
denominatore, e la 4 sa già trattare vincoli che un flusso non esprime —
incompatibilità di materia, tetti orari, giorni liberi. In EDT le fasi sono
caselle indipendenti, spuntate singolarmente: la struttura è quella.

**1.2 — Il motore è flusso massimo e taglio minimo, una risorsa per volta.**
Le alternative scartate: enumerare sottoinsiemi di risorse (euristica, perde
violatori senza saperlo, nessun certificato minimale); estrarre l'UNSAT core da
CP-SAT (escluso in partenza — un core è un insieme di *vincoli*, non di
risorse, e `diagnostica.md` lo dichiara illeggibile).

**1.3 — L'oracolo è a due livelli: casi costruiti più oracolo differenziale
contro CP-SAT.** Il banco generativo dedicato resta fuori, perché il banco che
servirebbe **esiste già** e per questo scopo si usa al contrario (§6.2).

## 2. Il perimetro

**Le attività candidate** sono quelle non `SUSPENDED`, come già fa
`analyze_capacity`. Fra queste, quelle **già piazzate e immobili** (`FIXED`,
`LOCKED_IN_PLACE`) non sono candidate: **consumano capienza**. Le altre sono
candidate anche se attualmente piazzate — incluse le `NOT_SUSPENDABLE`, che
vincolano la sospensione e non la collocazione. La fase 5 risponde a «entra
tutto?»,
non a «l'orario di adesso è valido», quindi il piazzamento corrente di
un'attività mobile non è un dato ma l'oggetto della domanda.

È la disciplina di ADR-018 senza inventarla: il passato immobile riduce la
capienza, la deficienza si misura sul residuo.

**Le risorse** sono le chiavi di `activity_tokens`, le stesse su cui ragiona
`structural:occupation`. Non l'enumerazione `_units()` di `capacity.py`: lì
serviva l'unità didattica (classe / parte / gruppo), qui serve la risorsa che
**porta la capienza**, che è esattamente il token. La capienza di una cella per
la risorsa `r` è `Resource.simultaneous_capacity` (default 1; `Qtà > 1` per
aule e materiali cumulativi).

⚠ `Room.capacity` resta fuori: è **descrittiva, non un vincolo** — verificato in
UI, scritto in `aule.md`.

**Le settimane sono una dimensione, non un dettaglio.** La deficienza si cerca
**per firma di settimana**, riusando `week_signatures(schedule)` di
`conformity.py` — la primitiva **già condivisa** fra `check_schedule` e
`SolverContext`, non `_week_groups` di `capacity.py`. Le due non sono
equivalenti: `week_signatures` include nella firma anche le **indisponibilità
datate** e i **festivi**, non solo le maschere delle attività, ed è la stessa
firma su cui il modello CP-SAT posta i suoi vincoli. Usare l'altra
disallineerebbe la fase 5 dall'oracolo che deve confermarla.

Per ogni rappresentante si costruisce `ScheduleState.build(schedule, week=rep)`,
che filtra già le attività attive in quella settimana. Due
attività di settimane disgiunte non competono per la stessa cella, e trattarle
come concorrenti produce **falsi positivi** — il difetto peggiore possibile per
questa fase, che dice «impossibile» e manda l'utente a smontare vincoli sani.

⚠ Nota la direzione, perché su questo progetto le firme hanno già ingannato una
volta: in `MaxGapBuilder` unire le firme vincolava **di meno** (il difetto
corretto il 2026-08-24); qui unirle vincolerebbe **di più**. Stesso oggetto,
verso opposto. Per questo si riusa il codice di `_week_groups`, che il verso
giusto ce l'ha già, invece di riderivare il ragionamento.

### 2.1 La firma della funzione

```python
def analyze_hall(schedule) -> list[HallFinding]
```

⚠ **Diversamente da `analyze_capacity()`, la fase 5 richiede uno `Schedule`**:
le serve lo stato (piazzamenti delle immobili, indisponibilità datate della
settimana, festivi), e `ScheduleState` si costruisce solo da uno schedule. La
fase 4 lavora sull'anagrafica grezza e non ne ha bisogno.

Conseguenza sul comando: `manage.py analyze` esegue la fase 4 sempre e la
fase 5 **solo con `--schedule`**, dichiarandolo quando la salta invece di
tacere.

## 3. Il motore

### 3.1 La rete

Per ogni risorsa `r` e ogni firma di settimana:

| arco | capacità |
|---|---|
| sorgente → attività `a` | `duration_slots(a)` |
| attività `a` → cella `c` | **∞** |
| cella `c` → pozzo | `simultaneous_capacity(r)` − consumo delle immobili |

Le celle di `a` sono l'**impronta** dei suoi piazzamenti ammissibili: `c` è
raggiungibile se esiste un avvio ammissibile `s` con `s ≤ c < s + durata`.

Il flusso massimo è il numero di slot piazzabili. Se è minore della domanda,
c'è deficienza.

⚠ **L'unità della rete è lo slot, l'unità del finding è il minuto.** Il flusso
si calcola in slot — le capacità devono essere interi piccoli perché Dinic sia
veloce e il taglio esatto — e la conversione a minuti (`× grid.slot_minutes`)
avviene **solo** nel finding. Mescolare le due unità dentro la rete è il modo
più diretto per ottenere un certificato che non torna.

### 3.2 Perché ∞ sull'arco centrale

Con una capacità finita il taglio minimo può passare **attraverso** gli archi
centrali, e l'insieme che ne esce è un insieme di *archi*: non si traduce in
una frase che l'utente possa leggere. Con ∞ il taglio minimo è per forza fatto
di soli archi di sorgente e di pozzo, e vale

> deficienza = max su `T` di [ domanda(`T`) − capienza(`N(T)`) ]

dove `T` sono le attività raggiungibili dalla sorgente nel grafo residuo. È il
teorema di Hall in forma deficitaria, e `T` è il violatore.

⚠ ∞ non regala nulla di pericoloso: il totale che entra in una cella resta
limitato dall'arco verso il pozzo. L'unico allentamento è che una singola
attività potrebbe occupare due unità della **stessa** cella — possibile solo se
`simultaneous_capacity > 1` **e** durata > 1, cioè solo su aule e materiali
cumulativi, che oggi non sono nemmeno variabili di decisione. È un allentamento
nel verso sicuro (sovrastima la capienza) e **va scritto nel docstring**, non
lasciato implicito.

### 3.3 Il certificato si verifica, non si deduce

Ottenuto `T` per raggiungibilità, prima di emettere il finding si ricontano
`domanda(T)` e `capienza(N(T))` e si controlla che la differenza sia davvero
positiva. Se il controllo fallisce, il finding **non esce**.

Sono tre righe, e trasformano un argomento sui grafi residui — il genere di
ragionamento che su questo progetto si è già rivelato falso tre volte quando
dichiarato invece che misurato (§9.8 della spec precedente) — in una
**postcondizione controllata**.

### 3.4 Perché un verdetto negativo è una dimostrazione

Il rilassamento ignora la contiguità dei blocchi e le interazioni fra le
attività **dentro** l'insieme. Entrambe le omissioni *aggiungono* libertà,
quindi il flusso massimo **sovrastima** il vero massimo piazzabile: se nemmeno
la sovrastima copre la domanda, l'istanza è infattibile davvero.

È la stessa disciplina che `capacity.py` dichiara in testa al file, ed è la
ragione per cui l'oracolo differenziale di §6.2 ha senso.

Il verso opposto **non vale**, ed è l'incompletezza dichiarata di questa fase:
il solver può rispondere `INFEASIBLE` senza che nessun `T` sia deficiente.

## 4. Il dominio

Il dominio di ciascuna candidata è quello che `residual_domain` calcola già: le
celle dove il piazzamento **non introduce violazioni hard nuove** rispetto alla
baseline. È molto più stretto di un'intersezione di disponibilità — passa per
tutti i checker, quindi incorpora incompatibilità di materia, tetti orari,
buchi, sedi — e questo rende la fase 5 **più forte**, non solo più comoda:
domini più stretti significano più violatori trovati.

⚠ **«Resta sano perché la condizione di `residual_domain` è precisamente
l'ammissibilità» era falso**, e la review finale l'ha dimostrato con un falso
positivo riproducibile (§4.3). La condizione di `residual_domain` non è
l'ammissibilità: è «la `Finding.key` è cambiata». Le due coincidono solo per i
checker **monotoni**, e non tutti lo sono.

**Modifica mirata**: oggi `residual_domain` restituisce i conteggi (`S.P.`,
`Nr G.`). Si estrae la scansione in `admissible_starts(activity, state,
relaxed=False)`, e `residual_domain` conta quelli. Comportamento identico,
test esistenti invariati — la fase 5 passa `relaxed=True` (§4.3).

### ⚠ 4.1 La trappola dello spiazzamento

`residual_domain` spiazza **solo** l'attività in prova: tutte le altre restano
piazzate e le restringono il dominio. Per la fase 5 questo sarebbe sbagliato
nel **verso peggiore** — le candidate si toglierebbero domini a vicenda, la
capienza risulterebbe più bassa del vero, e uscirebbero **falsi positivi**.

Quindi: si costruisce lo `ScheduleState` della firma, si **spiazzano tutte le
candidate insieme**, e su quello stato — che contiene le sole immobili — si
calcolano tutti i domini. Ogni candidata vede le immobili e nessuna delle
sorelle. È esattamente la premessa del rilassamento: i domini sono individuali,
la competizione la esprime il flusso.

Questo difetto, se introdotto, **non si vedrebbe da nessun caso positivo** —
tutti continuerebbero a passare. Ha un test dedicato (§6.1).

### 4.2 Il costo

⚠ **Misurato al Task 7, e la previsione qui sotto era sbagliata di un ordine
di grandezza.** La proiezione originale — ~12 ms per attività (dal piano 2: la
colonna S.P. di 26 attività in ~0,3 s), quindi ~3,5 s sul Fermi intero per
firma di settimana — era un'estrapolazione lineare mai verificata. Misurato
`analyze_hall` sul Fermi intero (284 attività, `tests/test_analysis_hall.py::
test_fermi_intero_misurato`): **~0,4 s**, non ~3,5 s. La stima del piano 2
misurava `residual_domain` attività per attività con query ripetute; qui i
domini si calcolano **una volta per attività** dentro un solo `ScheduleState`
e si condividono fra tutte le risorse (perché non dipendono da `r`), e il
flusso per gruppo lavora su reti piccole — l'estrapolazione lineare ignorava
entrambi gli effetti.

⚠ **E anche questa misura dice meno di quanto sembri: è per una firma sola.**
Il Fermi ha **una** firma di settimana — nessuna indisponibilità datata,
nessun festivo, tutte le attività annuali — e `analyze_hall` cicla sulle
firme, ricostruendo lo `ScheduleState` e tutti i domini per ognuna. Il costo è
**lineare nel numero di firme**, ed è la dimensione che questo dataset non
esercita: la stessa forma di errore che §2 mette in guardia («le settimane sono
una dimensione, non un dettaglio»).

Misurato sul Fermi aggiungendo indisponibilità **datate** su settimane diverse
(che è il meccanismo reale — le assenze):

| firme | secondi | s/firma |
|---|---|---|
| 1 | 0,34 | 0,34 |
| 3 | 0,99 | 0,33 |
| 6 | 1,88 | 0,31 |
| 11 | 3,25 | 0,30 |
| 21 | 5,98 | 0,29 |

Circa **0,3 s per firma**, lineare (il costo per firma cala appena perché la
costruzione della fixture si ammortizza). Un anno reale ha 35-40 settimane, e
nel caso limite in cui ognuna faccia firma a sé si arriva a **~10-13 s** sul
Fermi.

Per una fase diagnostica lanciata a mano resta accettabile — e `--no-hall`
esiste apposta (§8). Ma «la più veloce delle famiglie di analisi» era una
conclusione generale tratta dall'unica dimensione che il dataset non ha:
va letta come «~0,3 s per firma», non come un numero assoluto.

### ⚠ 4.3 I checker non monotoni, e il falso positivo che ne è uscito

Trovato alla **review finale**, dopo sette review per-task e un oracolo a
quaranta semi che non potevano vederlo (§6.3). Riproduzione minima:
`mini_school()`, una riga `MIN_DISTRIBUTION` (`min_days = 3`) su un docente,
tre attività da un'ora sui giorni 0, 1 e 2. `check_schedule` non emette
**nessun** finding HARD, `solve` risponde `OPTIMAL` — e `analyze_hall`
restituisce **tre** finding «L'attività non ha nessuna collocazione
ammissibile».

**La causa.** `admissible_starts` scarta una cella quando il piazzamento di
prova introduce una `Finding.key` **nuova** rispetto alla baseline, e
`Finding.key` include `quantities`. Per un checker la cui violazione è una
**deficienza** — `MIN_DISTRIBUTION` esiste già a stato vuoto, con `days = 0` —
ogni piazzamento *migliora* il conteggio e con esso cambia la chiave: chiave
nuova a ogni cella, dominio vuoto, deficienza inventata. E §4.1 è ciò che
*crea* la condizione: spiazzando tutte le candidate insieme, la baseline
diventa lo stato in cui i minimi sono massimamente violati.

**La correzione.** Una classificazione **dichiarata** sul `Checker`, nella
stessa forma di `PLACEMENT_INDEPENDENT`: `PLACEMENT_MONOTONE`, default `True`,
`False` sulle famiglie in cui piazzare può *riparare* una violazione, oppure
spostare l'identità del finding senza aggravarlo. `admissible_starts` guadagna
`relaxed=False`; con `relaxed=True` esclude dal loop di prova i non monotoni, e
`hall.py` passa `relaxed=True`.

⚠ **Il default resta `relaxed=False`**, quindi `S.P.` non cambia di un bit.
Non è pigrizia: `S.P.` è una **stima di difficoltà** mostrata in una colonna
ordinabile, e un dominio più stretto è per l'utente informazione, non un bug.
La fase 5 è l'opposto — il suo verdetto negativo è una dimostrazione.

**Le sei famiglie non monotone**, classificate leggendo i checker uno per uno:

| famiglia | perché |
|---|---|
| `MIN_DISTRIBUTION` | deficienza: piazzare la ripara |
| `FREE_GUARANTEED` | e in **entrambe** le direzioni: `free_half_days` si conta solo sui giorni *con* attività, quindi occupare un giorno vuoto ne *aggiunge* una |
| `IMPOSED_SUCCESSION` | entrambi i rami: con A = B infilare un'occorrenza dentro lo scarto lo spezza; con A ≠ B e B assente ogni A è in violazione, e una sola B le ripara tutte |
| `MAX_GAP_HOURS` | il buco è `ultima − prima + 1 − conteggio`: piazzare *dentro* un buco lo riduce |
| `WEEKLY_ORDER` | deriva d'identità: il finding nomina l'argmin, e l'argmin si sposta senza che la violazione cambi |
| `structural:didactic_weight` | deriva d'identità: `activities` porta *tutte* le attività dell'unità, quindi un piazzamento di lunedì rikeya la violazione di venerdì |
| i quattro `PARTS_*` | deriva d'identità: il finding nomina l'intero secchio, non chi realizza il disordine |

⚠ Le prime tre erano nell'elenco della review, misurato su dieci semi. Le
altre vengono dalla **lettura**, e la misura non le vede: hanno bisogno di
un'attività **congelata** per manifestarsi, e il banco a testimone non congela
niente. `ARRIVAL_DEPARTURE`, che l'elenco della review dava come quarta, a
lettura è **monotona** — `compliant` non può che calare piazzando, quindi ogni
cambio di chiave è un peggioramento causato dalla prova — e marcarla non
cambia un finding su quaranta semi (misurato). Resta monotona.

**Rilassare fa perdere richiamo, mai precisione**: domini più larghi
significano più capienza, quindi meno deficienze trovate. È il verso giusto in
cui sbagliare, ed è il criterio con cui si decide una famiglia dubbia.

⚠ Su `WEEKLY_ORDER` e sui quattro `PARTS_*` il rilassamento costa richiamo e
**oggi non compra precisione**: i loro builder trattano ADR-018 vietando ai
liberi il secchio già sporco, quindi rispondono `INFEASIBLE` esattamente dove
`admissible_starts` non rilassato svuotava il dominio. Si rilassano lo stesso
perché `PLACEMENT_MONOTONE` è una proprietà del **checker**: legarla alla
scelta di un builder metterebbe in `domain/analysis` una dipendenza dal
solver — quella che il package esiste per non avere — e marcirebbe in silenzio
il giorno che il builder cambia idea.

## 5. Il finding

```python
@dataclass(frozen=True)
class HallFinding:
    statement: str                       # l'enunciato, letterale da EDT
    binding_label: str                   # la risorsa che porta la capienza
    resource_labels: tuple[str, ...]     # tutte le risorse implicate, nominate
    n_activities: int
    required_minutes: int
    placeable_minutes: int
    window: tuple[tuple[int, int], ...]  # N(T): le celle in cui l'insieme è intrappolato
    activities: tuple[int, ...]
    remedies: tuple[str, ...]
```

L'enunciato è quello osservato: *«La fascia di disponibilità comune delle
attività e delle rispettive risorse non permette di piazzare tutte le
attività.»* I rimedi sono i tre di EDT — `Diminuire le indisponibilità delle
risorse`, `… delle risorse comuni`, `Diminuire la durata delle attività`.

`resource_labels` si ottiene unendo le risorse delle attività di `T`, che è
come EDT compone quella riga (`11 docenti + 1A + LAB. ARTISTICA`).
`binding_label` è la risorsa `r` che porta la capienza, tenuta separata perché
è l'informazione che dice **dove** intervenire: le altre restringono, quella
satura.

### 5.1 La riducibilità

L'insieme `T` che esce dalla raggiungibilità è il **massimale**: sul Fermi
potrebbe nominare centinaia di attività, e nessuno legge una diagnosi così. Si
aggiunge una passata di riduzione greedy — si prova a togliere un'attività per
volta e la si toglie se il certificato regge — ripetuta fino a punto fisso.

Non è cosmesi: l'insieme che ne esce è **irriducibile**, cioè ogni attività
nominata è *necessaria* alla contraddizione. È una proprietà dimostrabile e
verificabile a posteriori, non un troncamento arbitrario. I 25 di EDT
suggeriscono che è la forma in cui l'informazione è ancora leggibile.

Costa O(|T|²) ricalcoli di `N(T)` su insiemi piccoli: irrilevante accanto ai
~0,4 s dei domini sul Fermi intero (misurato, §4.2).

### 5.2 Deduplicazione e caso singolo

Lo stesso violatore si trova spesso da più risorse (la classe e il docente
saturano insieme). Si deduplica su `frozenset(attività)`, come già fa `seen` in
`capacity.py`.

Il caso `|T| = 1` è la **fase 1** di EDT — l'attività che da sola non ha
nessuna collocazione, cioè `S.P. = 0`. Si emette lo stesso, con un enunciato
distinto e più semplice, invece di sopprimerlo: è la diagnosi più facile da
capire e da riparare, e nasconderla perché appartiene a un'altra fase sarebbe
fedeltà alla tassonomia contro l'utente.

## 6. Il criterio di riuscita e i test

⚠ Vincolo di struttura: `domain/analysis` **resta senza `ortools`** — è la
ragione per cui `domain/solver` è un package separato. L'oracolo differenziale
vive in `tests/`, che importa entrambi, e non introduce nessuna dipendenza
nuova nell'analisi.

### 6.1 Livello 1 — casi costruiti

Metà positivi, metà negativi. **I negativi contano di più**: il difetto temuto
è il falso positivo.

| caso | atteso |
|---|---|
| Sette lezioni da un'ora, un docente, sei celle disponibili | deficienza 1h, `T` = tutte e sette |
| L'incrociata: capienza dalla classe, domini ristretti dai docenti (forma del caso C osservato) | finding |
| Sette lezioni in sette fasce | **nessun finding** — il confine esatto |
| Due attività sull'unica cella, ma in firme di settimana disgiunte | **nessun finding** — trappola §2 |
| Sorelle già piazzate che produrrebbero una deficienza fantasma | **nessun finding** — trappola §4.1 |
| La stessa istanza con e senza un'immobile piazzata | finding / niente |
| Un'attività da tre ore | esercita l'impronta, non solo l'avvio |
| Irriducibilità | tolta una qualsiasi attività da `T`, il certificato cade |

### 6.2 Livello 2 — l'oracolo differenziale, nelle due direzioni

La direzione ovvia: ogni finding emesso deve corrispondere a un `INFEASIBLE`
del modello hard. Un violatore inventato diventa un rosso.

🔑 La direzione che vale di più, e che costa quasi nulla: **le istanze del
`solver_harness` esistente sono fattibili per costruzione** — hanno un
testimone. Quindi la fase 5 su ognuna di esse deve emettere **zero finding**,
su tutti i seed. Qualunque finding è un falso positivo *dimostrato*, non
sospettato.

È la ragione per cui il banco generativo dedicato resta fuori: il banco che
servirebbe esiste già, e per questo scopo si usa **al contrario** — non
istanze con violatori noti, ma istanze senza violatori su cui la fase 5 deve
tacere.

⚠ **Il limite, dichiarato**: questo misura la **precisione** (niente falsi
positivi), non il **richiamo** (quanti violatori veri trova). Il richiamo resta
coperto dai soli casi a mano, e la fase 5 è comunque incompleta per costruzione
(§3.4): non c'è un numero di richiamo da promettere. Va scritto nel consuntivo
invece che lasciato intendere.

### ⚠ 6.3 E il testimone dev'essere **denso**, o l'oracolo non misura niente

Trovato alla review finale, ed è la ragione per cui §4.3 è arrivato fin lì
indisturbato. L'oracolo di §6.2 girava su `build_witness(seed)`, e dopo quella
chiamata:

```
ResourceTimeConstraint.objects.count() == 0
SubjectConstraint.objects.count()      == 0
ResourceUnavailability.objects.count() == 0
```

Le righe di vincolo non le crea `build_witness`: le creano i **derivatori**,
che `build_witness` non chiama. Quaranta semi che esercitavano lo stesso
sottoinsieme dello spike a cinque vincoli — cioè **letteralmente** la frase che
`CLAUDE.md` porta già sul Fermi («non misura il modello completo: misura il
dataset»), non applicata qui.

**Correzione**: si estrae da `run_tutte_le_famiglie` la metà che **non chiama
il solver** — `costruisci_tutte_le_famiglie(seed)`, che deriva le righe di
tutte e ventisei le famiglie e **asserisce** che il testimone le soddisfi
insieme — e l'oracolo usa quella. Alla fase 5 il solver non serve, e non
pagarlo tiene il file a **~26 s** per quaranta semi invece dei minuti che il
`solve(time_limit=120)` costerebbe.

Su quei testimoni densi, prima della correzione di §4.3, la fase 5 era rossa
su **40 seed su 40** — da 6 a 15 falsi positivi per seed.

## 7. Struttura dei file

| file | cosa |
|---|---|
| `domain/analysis/flow.py` | **nuovo** — flusso massimo bipartito (Dinic) più la raggiungibilità residua. ~70 righe, nessuna dipendenza |
| `domain/analysis/hall.py` | **nuovo** — `HallFinding`, la rete, il certificato, la riduzione. ~200 righe |
| `domain/analysis/domain_size.py` | **modifica mirata** — si estrae `admissible_starts` |
| `domain/management/commands/analyze.py` | la fase 5 accanto alla 4, sotto `--schedule`, flag `--no-hall` |
| `tests/test_analysis_flow.py` | il massimo flusso da solo |
| `tests/test_analysis_hall.py` | livello 1 |
| `tests/test_hall_oracle.py` | livello 2 |

**Perché `flow.py` separato**: il massimo flusso è un algoritmo generico che
non sa niente di orari, e la sua correttezza si prova su grafi minuscoli
scritti a mano. Tenerlo dentro `hall.py` mescolerebbe la teoria dei grafi e la
semantica del dominio, e renderebbe impossibile dire, davanti a un rosso, quale
dei due ha sbagliato. È la separazione che `domain/solver` ha fra `model.py` e
i builder.

**Nel comando** la fase 5 esce dopo la 4, stesso formato `enunciato → dettaglio
→ soluzione → azioni`, e i suoi finding entrano nel riepilogo e nell'exit code.
Il flag `--no-hall` la spegne: EDT le fasi le fa spuntare singolarmente, tutte
attive di default, e — anche ai ~0,4 s misurati sul Fermi (§4.2), non ai
~3,5 s previsti — resta un costo in più da non imporre a chi vuole solo la
fase 4 in CI. Senza `--schedule` la fase 5 non si esegue affatto (§2.1) e il
comando lo scrive.

## 8. Fuori scope, dichiarato

- **Il riquadro `Soluzione` operativo** — la griglia delle indisponibilità
  modificabile sul posto con `Rilancia la verifica`. È UI, e qui non c'è UI.
  `HallFinding` porta però già `activities` e `window`, i due dati che quella
  schermata consumerebbe, e `activities` è ciò che alimenterebbe l'`Estrai` del
  prodotto: il pezzo non pregiudica quella strada.
- **Il richiamo**: nessuna promessa di trovare *tutti* i sottoinsiemi
  infattibili. Impossibile per costruzione (§3.4).
- **L'aula come variabile di decisione**: resta un token fisso, come oggi. Il
  pezzo la tratta come risorsa portante di capienza, non come scelta.

## 9. I modi noti in cui questo pezzo può sbagliare

Elencati qui perché siano cercati durante l'implementazione invece che scoperti
dopo:

1. **Falso positivo da firme unite** (§2) — verso opposto a quello del D.T.B.
2. **Falso positivo da sorelle non spiazzate** (§4.1) — invisibile ai casi
   positivi.
3. **`T` non irriducibile** — diagnosi corretta ma illeggibile.
4. **Certificato dedotto e non verificato** (§3.3) — il taglio minimo dà
   l'insieme giusto solo se gli archi centrali sono davvero infiniti.
5. **Impronta calcolata sugli avvii invece che sugli slot occupati** — una
   deficienza sottostimata sulle attività lunghe.
6. **Capienza delle immobili contata due volte**, una nello stato e una
   nell'arco verso il pozzo.

⚠ **Il settimo non era in elenco, ed è quello che è passato**: *falso positivo
da checker non monotono* (§4.3). Nessuna delle sei voci qui sopra lo copre —
sono tutte sul **motore** (le firme, il taglio, l'impronta, la capienza),
nessuna sul **dominio**, perché §4 dichiarava il dominio sano per definizione.
La lezione è la stessa che `CLAUDE.md` conta ormai a decine: la proprietà che
ha ceduto è quella che il documento affermava invece di misurare. E l'ottavo,
che non è un difetto ma un limite dichiarato: il **costo per firma** (§4.2),
misurato solo sull'unico dataset che di firme ne ha una.
