# Task 9 — Le sedi — review

Diff rivisto: `6a6d9b0..31ff9de` (commit `4035980` dell'implementatore +
`31ff9de` del controller). Metodo: ogni affermazione qui sotto è accompagnata
dalla sonda che l'ha prodotta e dal caso di controllo vicino. Tutte le sonde
sono state eseguite in questo worktree e poi **rimosse**; `git status` è pulito
(verificato in chiusura). Nessun file del repo è stato modificato dalla review.

**Verdetto: chiudibile con due Important da girare al controller** — nessuno dei
due è una svista dell'implementatore, entrambi sono difetti che la sua
esplorazione ha sfiorato ma non misurato fino in fondo. Le quattro correzioni
del brief sono applicate e **corrette**. Dettaglio sotto.

---

## 1. Conformità al brief e al piano

| | esito |
|---|---|
| Correzione 1 (Ruling 27) — «nessuna sede nota in mezzo» | ✅ implementata, **riprodotta** e verificata esatta |
| Correzione 2 (Ruling 28) — clamp ADR-018 | ✅ implementata, entrambi i test **mordono** (RED riprodotto) |
| Correzione 3 (Ruling 29) — niente `test_sedi_sul_banco`, derivatori `0`/`1` | ✅ |
| Correzione 4 (Ruling 30/31) — flusso rng separato | ✅ corretta e verificata |
| `SiteTransitionBuilder` non toccato salvo `any_free` | ✅ (unica differenza: `any_free(ctx, tocca)` al posto del controllo a mano — è la primitiva già esistente, conforme al vincolo globale 5) |
| `domain/analysis/` non importa `ortools` | ✅ (`grep -rn ortools domain/analysis/` → nessuna occorrenza) |
| Chiavi del registro invariate, due sole aggiunte | ✅ |
| Un solo commit dell'implementatore col trailer | ✅ |

### Correzione 1 — riprodotta, e poi misurata oltre quanto chiesto

**Sonda.** Istanza a tre fasce su un solo giorno (sede A / senza sede / sede B),
`per_day = 0`, `site_transition_slots = 0`.

Con il builder **corretto** (codice in albero):

```
STATUS: INFEASIBLE {'attivita': 3, 'libere': 3, 'variabili': 21, 'constraint': 22, 'secondi': 0.018}
PIAZZAMENTI: {}
```

Rimettendo la formulazione del piano (`occupied(m).Not()` al posto di
`site_occupied(m, sito).Not()` per ogni sede), **stessa istanza**:

```
STATUS: OPTIMAL {'attivita': 3, 'libere': 3, 'variabili': 22, 'constraint': 23, 'secondi': 0.025}
PIAZZAMENTI: {1: (0, 0), 2: (0, 1), 3: (0, 2)}
FINDING HARD: [Finding(code='max_site_changes', message='Numero di cambi di sede superiore al limite fissato',
  severity=<Severity.HARD: 'hard'>, resources=(1,), activities=(),
  quantities={'day': 0, 'changes': 1, 'max_changes': 0}, weeks=(0, 1, 2, 3))]
```

Il difetto e la sua sparizione sono confermati **esattamente** come nel rapporto
dell'implementatore. Builder ripristinato bit-per-bit dopo la mutazione.

**Oltre la riproduzione — la nuova formulazione coincide col checker?** Il brief
chiedeva di stabilire se resti uno scarto. Confronto **esaustivo** fra la
semantica del checker e quella del builder su una giornata di `S` fasce,
alfabeto `{vuoto, A, B, C, senza-sede}` (script in scratchpad, non nel repo):

```
--- capienza 1 per fascia  S=2  configurazioni=25
    under-count (builder < checker, PERICOLOSO): 0
    over-count  (builder > checker, conservativo): 0
--- capienza 1 per fascia  S=3  configurazioni=125
    under-count: 0    over-count: 0
--- capienza 1 per fascia  S=4  configurazioni=625
    under-count: 0    over-count: 0
--- capienza 2 per fascia  S=2  configurazioni=144
    under-count: 37   esempio peggiore: ([(), ('A', 'B')], checker 1, builder 0)
    over-count:   2   esempio peggiore: ([('A','B'), ('B','C')], checker 2, builder 3)
--- capienza 2 per fascia  S=3  configurazioni=1728
    under-count: 368  esempio peggiore: ([('A','B'), ('A',), ('B','A')], checker 4, builder 2)
    over-count:  210  esempio peggiore: ([('A',), ('A','B'), ('B','C')], checker 2, builder 4)
```

Lo stesso confronto per `SiteTransitionBuilder` (violazione booleana invece che
conteggio, `needed` 1/2/3, `S` 3/4):

```
capienza 1 needed=1..3 S=3,4: checker viola ma builder NO = 0 | builder viola ma checker NO = 0
capienza 2 needed=1   S=3: checker viola ma builder NO = 176 [(), (), ('A','B')] | builder viola ma checker NO = 0
capienza 2 needed=1   S=4: checker viola ma builder NO = 1184 | builder viola ma checker NO = 0
capienza 2 needed=2,3 S=3,4: idem, sempre solo nella direzione «builder NO»
```

**Risultato.** A capienza 1 per fascia — cioè ovunque la capienza cumulativa non
entri in gioco — la traduzione **non è conservativa, è esatta**: zero scarto in
entrambe le direzioni, per entrambi i builder. È un risultato migliore di quello
dichiarato dal piano («più stretto, mai più largo») e va scritto nel docstring
al posto dell'attuale formula prudente. A capienza ≥ 2 lo scarto esiste in
**entrambe** le direzioni, ed è l'oggetto dell'Important 1 qui sotto.

### Correzione 2 — il clamp c'è, ed è un clamp

Riprodotte **entrambe** le prove RED del rapporto, verbatim.

Mutazione «clamp rimosso» (`sum(cambi) <= per_giorno` grezzo):

```
FAILED tests/test_solver_sites.py::test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca
E       AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 242, 'constraint': 222, ...}
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
1 failed, 4 passed
```

Mutazione «clamp → salto» (`continue`/`pass` quando le congelate sforano):

```
FAILED tests/test_solver_sites.py::test_adr018_clamp_impedisce_alla_libera_di_aggiungere_un_cambio
E       AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 548, 'constraint': 551, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
1 failed, 4 passed
```

**Il test che distingue clamp da salto morde davvero.** La correzione che
l'implementatore descrive (costringere la libera sul giorno 0 con
`ResourceUnavailability`, trasformando la domanda in INFEASIBLE-contro-FEASIBLE)
è quella giusta: senza di essa CP-SAT trovava un'altra giornata da solo e
l'asserzione non discriminava nulla.

Verificato anche **quali** dei cinque test mirati mordono, spegnendo del tutto
`MaxSiteChangesBuilder.post`:

```
FAILED test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo
FAILED test_adr018_clamp_impedisce_alla_libera_di_aggiungere_un_cambio
2 failed, 3 passed
```

e spegnendo `SiteTransitionBuilder.build`, cinque volte di fila:

```
FAILED tests/test_solver_sites.py::test_site_transition_impone_le_fasce_libere   (×5, mai verde)
```

`test_max_site_changes_limita_i_cambi` non morde — l'implementatore lo dichiara
apertamente nel proprio docstring e lo appaia a quello che morde. Corretto.

### Correzione 3 — verificata strutturalmente

Nessun `test_sedi_sul_banco`; i dieci casi delle due famiglie esistono in
`test_famiglia`:

```
tests/test_solver_witness.py::test_famiglia[max_site_changes-1..5]
tests/test_solver_witness.py::test_famiglia[structural:site_transition-1..5]
```

I due derivatori restituiscono `0`/`1` con docstring che dichiara la vacuità,
nella forma degli altri undici.

### Correzione 4 — il commit del controller `31ff9de`

La correzione è **giusta** e non introduce altro. `random.Random(f"sedi-{seed}")`
è un flusso indipendente: nessun altro derivatore consuma da lì, e
`_make_activities` riceve `seed` come parametro con default `0` (innocuo: è
sempre chiamata da `build_witness` che lo passa).

Verificata l'aritmetica, che è il controllo che conta:

| | test | passed | skipped |
|---|---|---|---|
| baseline pre-Task 9 (dichiarata) | 284 | 282 | 2 |
| dopo `31ff9de` (misurata da me) | 299 | 290 | 9 |

Delta test = **15** = 5 (`test_solver_sites.py`) + 10 (due famiglie × cinque
seed). Delta passed +8, delta skipped +7, somma 15. I sette skip nuovi
appartengono **tutti** alle due famiglie nuove (`max_site_changes-3,-4,-5` e
`structural:site_transition-1,-2,-3,-5`); i due preesistenti sono
`arrival_departure-2` e `arrival_departure-4`, esattamente la baseline. Quindi
**nessun test preesistente ha cambiato stato**, incluso il richiamo di
`run_family` dentro `tests/test_solver_time_counting.py`, che con il flusso
condiviso aveva guadagnato uno skip e ora non ne ha nessuno. La misura del
controller è confermata.

---

## 2. Le due scoperte collaterali: verdetto

### (a) Due sedi diverse sulla **stessa** fascia — **REALE, e più grave di come è riportata**

L'implementatore dice: raggiungibile con `simultaneous_capacity > 1`, il builder
sotto-conta. **Confermato, e il caso è peggiore su tre punti che il rapporto non
copre.**

**Sonda 1 — rompe davvero il criterio di riuscita, non è solo «inesprimibile».**
Classe a `simultaneous_capacity = 2`, griglia 1 giorno × 1 fascia, due attività
di docenti diversi con sedi A e B, `per_day = 0`:

```
[A capienza=2] STATUS: OPTIMAL {1: (0, 0), 2: (0, 0)}
[A capienza=2] occupation: []
[A capienza=2] max_site_changes: [Finding(code='max_site_changes', ..., severity=HARD,
   resources=(1,), quantities={'day': 0, 'changes': 1, 'max_changes': 0}, weeks=(0,1,2,3))]
```

**Caso di controllo** (stessa istanza, `simultaneous_capacity = 1`):

```
[A capienza=1] STATUS: INFEASIBLE {}
```

Il solver risponde `OPTIMAL`, `check_schedule` sulla soluzione applicata produce
un finding `HARD` **nuovo**, zero finding di occupazione. È l'oracolo
differenziale rotto, non una limitazione teorica.

**Sonda 2 — lo stesso buco è anche in `SiteTransitionBuilder`, che il rapporto
dichiara sano.** E per una via molto più realistica: un'**aula** con
`simultaneous_capacity = 2` — che è il `Numero di aule` / colonna `Qtà` di EDT,
una feature documentata in `docs/edt/aule.md`, non un caso di laboratorio.
Griglia 1×1, due attività di classi diverse nella stessa aula, sedi diverse,
`site_transition_slots = 1`:

```
[A2 capienza=2] STATUS: OPTIMAL {1: (0, 0), 2: (0, 0)}
[A2 capienza=2] occupation: []
[A2 capienza=2] site_transition: [Finding(code='site_transition', ..., severity=HARD,
   resources=(3,), activities=(1, 2), quantities={'day': 0, 'gap_slots': -1, 'needed_slots': 1})]
```

**Caso di controllo** (`simultaneous_capacity = 1`): `INFEASIBLE`.

Il confronto esaustivo della sezione 1 lo conferma su tutte le configurazioni:
`checker viola ma builder NO = 1184` su 20736 a `S=4, needed=1`, e **mai**
l'inverso.

**Sonda 3 — la direzione opposta esiste e batte il clamp ADR-018.** Nello stesso
regime il builder a volte **sovra-conta**, e il clamp (`max(cap, debito)`) è
calcolato con la semantica del *checker*: quando il builder ne conta di più, il
modello diventa infattibile per colpa di un passato **legale**. Quattro
congelate su classe a capienza 2, `[A,B]` alla fascia 0 e `[B,C]` alla fascia 1
(checker: 2 cambi; builder: 3 coppie forzate), `per_day = 2`, più una libera:

```
[A3 sonda (checker 2, builder 3)]    STATUS: INFEASIBLE   max_site_changes sul passato: []
[A3 controllo (checker 1, builder 1)] STATUS: OPTIMAL     max_site_changes sul passato: []
```

Il controllo è la stessa istanza con `[A,A]` / `[B,B]` (dove i due conteggi
coincidono): `OPTIMAL`. Quindi non è il clamp a essere scritto male — è il
disallineamento di conteggio a scavalcarlo.

**Quanto pesa, e cosa raccomando.** Pesa: è l'unico modo noto di far uscire dal
solver un finding `HARD` nuovo, ed è raggiungibile con una feature reale (aule a
`Qtà > 1`). Ma **non si ripara nel builder**, e questa è la parte che va portata
al controller:

> `domain/analysis/state.py:135` definisce `self.occupancy = defaultdict(list)`,
> e `_site_sequence` la scorre **in ordine di lista**. Con due attività di sede
> diversa sulla stessa fascia, il conteggio del checker dipende dall'ordine di
> inserimento: `[A,B]` seguito da `[A]` dà 2 cambi, `[B,A]` seguito da `[A]` ne
> dà 1. Cioè **sotto capienza cumulativa la semantica di `max_site_changes` non
> è definita**: dipende da un artefatto di implementazione del checker, che è
> l'autorità. Inseguirla nel builder significherebbe replicare l'artefatto.

Raccomandazione in due pezzi, da decidere nella spec:

1. **`structural:site_transition`**: qui il checker **è** ben definito (due sedi
   diverse sulla stessa fascia violano sempre, qualunque l'ordine). Il buco si
   chiude con una clausola sola, `s == t`, dentro `SiteTransitionBuilder`:
   `AddBoolOr([site_occupied(key,day,s,sa).Not(), site_occupied(key,day,s,sb).Not()])`
   per ogni coppia di sedi distinte. Costo: una clausola per
   (chiave, giorno, fascia, coppia di sedi), lo stesso ordine di grandezza già
   speso. Esatto, non conservativo.
2. **`T.MAX_SITE_CHANGES`**: prima va reso ben definito il **checker** (per
   esempio ordinando la sequenza intra-fascia, o dichiarando che sotto capienza
   > 1 le sedi diverse simultanee valgono un cambio e basta). Finché non lo è,
   qualunque traduzione è un tiro a indovinare. Nel frattempo il docstring
   dovrebbe dire che il builder è esatto **solo** per chiavi a capienza 1 — è
   ciò che il confronto esaustivo dimostra.

### (b) La guardia `any_free` di `SiteTransitionBuilder` — **REALE, ma non è un difetto del Task 9**

**Sonda.** Due **congelate** di sede diversa a fasce adiacenti sulla stessa
classe (conflitto interamente nel passato), `site_transition_slots = 1`, e una
terza attività libera:

```
[B libera_sulla_chiave=True]  STATUS: INFEASIBLE {'attivita': 3, 'libere': 1, 'variabili': 152, 'constraint': 227}
[B libera_sulla_chiave=False] STATUS: OPTIMAL    {'attivita': 3, 'libere': 1, 'variabili': 152, 'constraint': 223}
```

**Caso di controllo**: la libera spostata su un'altra classe e un altro docente
(nessuna libera sulla chiave) — la guardia scatta correttamente e il modello è
`OPTIMAL`. L'implementatore ha ragione: `by_cell` contiene ogni attività il cui
**dominio** tocca la cella, e per una libera il dominio è l'intera griglia,
quindi `any_free` è vera ovunque appena esiste **una** libera sulla chiave. Il
vincolo viene postato e il modello è infattibile per colpa del passato.

**Ma non è specifico di questo builder, e non nasce col Task 9.** Contro-sonda
sullo stesso schema con `structural:occupation` (builder preesistente, non
toccato dal Task 9): due congelate sulla stessa cella a capienza 1, più una
libera sulla chiave:

```
[B2 occupation] STATUS: INFEASIBLE {'attivita': 3, 'libere': 1, 'variabili': 32, 'constraint': 5}
```

Identico. Lo stesso idioma sta in `OccupationBuilder.build`
(`if not any(aid in ctx.free for aid, _ in here): continue`) e in
`ResourceBuilder.build` (`if not any(aid in ctx.free for aid in touching)`).
Cioè: è **esattamente** la domanda aperta già registrata in CLAUDE.md — «come si
comporta un builder quando un constraint mescola attività congelate già in
violazione e attività libere?» — e ADR-018 la risolve solo per i tetti
separabili, non per le strutturali.

**Verdetto**: reale e verificata, ma **Minor per il Task 9** (nessuna
regressione: il Task 9 aggiunge una seconda istanza di un difetto sistemico già
dichiarato aperto). Va risolta nella spec ADR-018 dei builder strutturali, non
qui. `SiteTransitionBuilder` ha la particolarità di essere l'unico caso in cui
la guardia è *sbagliata di principio* e non solo *insufficiente*: verifica la
raggiungibilità del dominio là dove servirebbe la clausola residua, e la
clausola in questione (`AddBoolOr` su due letterali derivati) non ha una forma
residua ovvia — se entrambi i letterali sono costanti a 1, il vincolo va
semplicemente non postato.

---

## 3. ⚠ Il punto principale: la vacuità di `structural:site_transition`

### Diagnosi

La causa dichiarata dal controller (Ruling 32) è corretta ma incompleta.

1. **Il minimo su molte coppie casuali è quasi sempre zero.** Confermato. Ma la
   causa profonda è **strutturale, non statistica**: `site_transition_slots` è
   un'impostazione **d'istituto**, globale. Il testimone deve rispettarla
   ovunque (`run_family` step 1 lo verifica), quindi il `needed` derivabile è
   *necessariamente* il minimo su tutte le coppie. Nessuna riformulazione che si
   limiti a **osservare** il testimone può fare meglio del minimo: derivare su
   una sola coppia scelta — la prima alternativa che il brief elencava — fa
   fallire lo step 1 su tutte le altre coppie. **Quella strada è chiusa, ed è
   una risposta con dimostrazione, non un'opinione.**
2. **Ridurre la densità delle sedi non aiuta** (seconda alternativa del brief):
   meno coppie significa più spesso *zero* coppie, e zero coppie è vacuo lo
   stesso. Misurato sotto.
3. **Derivare un `needed` positivo e poi verificare, scartando** (terza
   alternativa) coincide con la formula attuale: il minimo *è* il massimo
   `needed` che il testimone rispetta.

Resta una sola via che funzioni: **il derivatore deve costruire lo scenario, non
subirlo** — riparare il testimone (togliere la sede a chi crea le coppie troppo
vicine) finché il minimo superstite arriva a 1.

### Misura del potere vincolante reale

Il conteggio della vacuità che il rapporto porta non è la domanda giusta: un
seed non vacuo può essere ugualmente inerte. Misura fatta come si deve — per
ogni seed, `run_family` con il builder **reso no-op**, e si guarda se il caso
**morde** (fallisce). Un caso che passa col builder spento non testava niente.

**`structural:site_transition`, quindici seed:**

| derivatore | MORDE | SKIP (vacuo) | verde ma inerte | testimone rotto |
|---|---|---|---|---|
| `piano` (in albero) | **1** (seed 4) | 13 | 1 (seed 13) | **1** (seed 15) |
| `esatto` (distanza sulle fasce coperte) | 1 | 13 | 1 | 0 |
| `riparato` (50% sedi + riparazione a `needed=1`) | 7 | 6 | 2 | 0 |
| `denso` (sede a tutte + riparazione a `needed=1`) | **12** | 3 | 0 | 0 |

Con `mutato=False` (builder integro) **nessun** candidato produce fallimenti:
sono tutti verdi o skip. Sui soli cinque seed del banco: `piano` 1 morde /
4 skip, `denso` 3 mordono / 2 skip.

**`T.MAX_SITE_CHANGES`, quindici seed** — misura che nessuno aveva fatto, e il
risultato è il peggiore del giro:

| derivatore | MORDE | SKIP | verde ma inerte |
|---|---|---|---|
| `piano` (in albero) | **0** | 10 | 5 |
| `migliore` (docente con più attività con sede, invece che a caso) | 3 | 1 | 11 |
| `denso` (sede a tutte + docente migliore) | 1 | 0 | 14 |
| `segregato` (sedi assegnate **per giornata** al docente più carico → `per_day = per_week = 0`) | **12** | 0 | 3 |

Sui cinque seed del banco: `piano` **0/5** (i due non vacui, seed 1 e 2, passano
col builder spento), `segregato` 4/5. Ripetuta la misura dei due vincitori per
il non determinismo di CP-SAT: `segregato` 12 poi 11, `denso` 12 poi 12 —
oscillazione di un caso, l'ordine di grandezza tiene.

### Raccomandazione

**Adottare per entrambe le famiglie il principio «il derivatore costruisce lo
scenario».** In concreto, in `tests/solver_harness.py`:

- **`_derive_site_transition`**: (i) calcolare la distanza sulle **fasce
  coperte** come fa il checker, non sulle fasce d'inizio (vedi Important 2);
  (ii) assegnare una sede a tutte le attività da un flusso locale; (iii)
  togliere la sede, greedy, alle attività che formano coppie a distanza 0
  finché non ne restano; (iv) `needed` = minimo superstite, `return 0` se non
  sopravvive nessuna coppia. **Da 1/15 a 12/15 di potere reale**, zero falsi
  fallimenti, e il landmine dell'Important 2 sparisce per costruzione.
- **`_derive_max_site_changes`**: scegliere il docente con più attività e
  assegnargli le sedi **per giornata** (tutte le attività dello stesso giorno
  alla stessa sede, giorni alternati fra le due sedi), lasciando senza sede le
  altre attività. Nel testimone i cambi per giornata sono zero, quindi il tetto
  derivato è `per_day = per_week = 0` e qualunque soluzione che gli mescoli due
  sedi in una giornata viola. **Da 0/15 a 12/15**, mai vacuo, nessun
  `INFEASIBLE` osservato.

Costo: trascurabile. Tempo del candidato raccomandato sui cinque seed del banco,
`run_family` completa compresa la risoluzione:

```
TEMPO seed=1 PASS 0.21s   TEMPO seed=2 SKIP 0.05s   TEMPO seed=3 SKIP 0.05s
TEMPO seed=4 PASS 0.29s   TEMPO seed=5 PASS 0.41s
```

Nessuno dei due tocca `_make_activities`: il flusso `sedi-{seed}` separato dal
controller resta com'è, e **nessun altro derivatore vede un testimone diverso**
— ogni `run_family` costruisce il proprio testimone e il derivatore lo modifica
dopo. È la ragione per cui questa strada è preferibile a rendere `_try_place`
consapevole delle sedi, che invece sposterebbe di nuovo il testimone di tutti.

**Nota di onestà**: «il derivatore costruisce lo scenario» è un cambio di
convenzione rispetto agli undici derivatori esistenti, che osservano e basta. È
giustificato dal fatto che le sedi sono l'unico attributo del testimone che
`_make_activities` assegna **a caso e senza vincolo**, quindi l'unico su cui
l'osservazione pura non produce mai una configurazione interessante. Se il
controller preferisce non aprire questa strada, l'alternativa onesta è
dichiarare le due famiglie **coperte dai soli test mirati** e togliere i dieci
casi dal banco, invece di tenerli come dieci verdi che non dimostrano nulla.

---

## 4. Osservazioni classificate

### Important 1 — il buco della fascia condivisa è in **entrambi** i builder e rompe l'oracolo

Vedi § 2(a) per sonde e casi di controllo. Riassunto: `simultaneous_capacity > 1`
(feature reale: `Qtà` dell'aula) fa uscire dal solver una soluzione `OPTIMAL`
che `check_schedule` boccia con un `HARD` nuovo, sia su `max_site_changes` sia
su `site_transition`. Il rapporto dell'implementatore documenta solo il primo e
solo come «inesprimibile», non come rottura del criterio di riuscita.
Raccomandazione operativa in § 2(a): la clausola `s == t` chiude
`site_transition` in modo esatto; `max_site_changes` va prima reso ben definito
**nel checker**, perché oggi il suo conteggio dipende dall'ordine di una lista.

### Important 2 — `_derive_site_transition` ignora `duration_slots` e può rompere il proprio testimone

Il derivatore misura la distanza come `abs(slot2 - slot) - 1` fra le fasce
**d'inizio**; il checker la misura fra fasce **occupate**, e un'attività di
durata 2 occupa anche la fascia successiva. Quindi il derivatore può dichiarare
un `needed` che il testimone stesso viola.

**Sonda** — `run_family("structural:site_transition", 15)`, codice in albero,
nessuna mutazione:

```
E   AssertionError: il testimone stesso viola structural:site_transition (seed 15):
    [('site_transition', (1,), (1, 5), (('day', 2), ('gap_slots', 0), ('needed_slots', 1)))]
```

Diagnosi stampata dalla stessa sonda:

```
potere: 1  needed derivato: 1
FINDING: ... quantities={'day': 2, 'gap_slots': 0, 'needed_slots': 1}
   attivita 1 durata 2 sede 1 collocazione (2, 1)
   attivita 5 durata 1 sede 2 collocazione (2, 3)
```

L'attività 1 copre le fasce 1 e 2; il derivatore calcola `3 − 1 − 1 = 1` e
conclude che `needed = 1` è sicuro, il checker vede la sequenza `…sede1@2,
sede2@3…` con `gap_slots = 0`.

**Caso di controllo**: i seed 1–5, che il banco esercita oggi, non lo fanno
scattare (tutti vacui tranne il 4, dove non ci sono attività lunghe nelle
coppie). È un **landmine**, non un fallimento attuale: scatta appena si allarga
il range dei seed — cosa che l'implementatore stesso ha fatto per misurare
(seed 6–10), e che la review ha fatto (1–15). Va corretto anche se si scarta la
raccomandazione del § 3: è un difetto indipendente.

⚠ **`_derive_max_site_changes` non ha lo stesso difetto**, e vale la pena dire
perché: costruisce anche lui la sequenza sulle sole fasce d'inizio, ma il
**conteggio dei cambi è invariante alle ripetizioni** della stessa sede (un
`A,A,B` e un `A,B` danno entrambi 1), mentre la **distanza** non lo è. È
esattamente l'asimmetria che rende il primo derivatore sbagliato e il secondo
no.

### Minor 1 — la guardia `any_free` di `SiteTransitionBuilder`

Vedi § 2(b). Reale, verificata, ma sistemica e preesistente: `OccupationBuilder`
si comporta in modo identico sulla stessa sonda. Non è una regressione del
Task 9. Da chiudere nella spec ADR-018 delle strutturali.

### Minor 2 — `SiteTransitionBuilder` posta il vincolo anche dove nessuna attività di quella sede può stare

Misurato sul Fermi: il numero di constraint è **identico** con metà delle
attività con sede e con tutte (vedi § 5, righe `quota=0.5` e `quota=1.0`:
9736/4008 in entrambi i casi). Il builder cicla su tutte le chiavi × giorni ×
coppie vicine × coppie di sedi senza guardare se una attività di sede `sa` possa
davvero occupare `(key, day, s)`; quando non può, `site_occupied` è un
`Add(var == 0)` e la clausola è vera per costruzione. Un filtro a costo zero
(saltare la coppia se `site_occupied` è già noto costante a zero, informazione
che `ctx.by_cell` ha) taglierebbe la maggior parte delle 2926 clausole aggiunte.
Non è urgente a due sedi, lo diventa a quattro (§ 5).

### Minor 3 — `_frozen_site_changes` e il checker possono ordinare diversamente la stessa fascia

`_frozen_site_changes` scorre `ctx.by_cell[(key, day, slot)]` (ordine di
`index_cells`), il checker scorre `state.occupancy[(key, day, slot)]` (ordine di
`ScheduleState.build`). Con una sola attività per fascia i due ordini sono
irrilevanti; con più di una il conteggio cambia. È lo stesso regime
dell'Important 1 e si chiude con esso — lo segnalo separatamente solo perché
tocca il **clamp**, cioè ADR-018, non l'oracolo.

### Minor 4 — il docstring del modulo è più prudente della verità

`time_sites.py` dichiara «più stretta, mai più larga (spec §4.3)». Il confronto
esaustivo della § 1 mostra che a capienza 1 la traduzione è **esatta** in
entrambi i builder. Vale la pena scriverlo: «esatta per chiavi a capienza 1;
sotto-conta a capienza > 1 (vedi Important 1)» è un'affermazione più forte e più
utile di quella attuale, e dice anche dove **non** vale.

---

## 5. Il costo del modello

La misura dell'implementatore (sul seed 5 del banco) è plausibile ma poco utile
al Task 17. L'ho rifatta **sul Fermi intero**, che è ciò che il Task 17 dovrà
misurare. Baseline: la stessa 8140/1082 registrata in CLAUDE.md.

| configurazione | variabili | constraint | × baseline |
|---|---|---|---|
| Fermi, nessuna sede (baseline) | 8140 | 1082 | 1,0 |
| 2 sedi, 50% attività, `site_transition_slots = 0` | 8140 | 1082 | 1,0 |
| 2 sedi, 50% attività, `slots = 1` | 9736 | 4008 | **3,7** |
| 2 sedi, **100%** attività, `slots = 1` | 9736 | 4008 | 3,7 |
| 3 sedi, 100%, `slots = 1` | 10534 | 7466 | 6,9 |
| 4 sedi, 100%, `slots = 1` | 11332 | 12254 | **11,3** |
| 2 sedi, `slots = 0`, `MAX_SITE_CHANGES` sui 18 docenti | 11920 | 4970 | 4,6 |
| tutto acceso (2 sedi, `slots = 1`, 18 righe) | 12520 | 6900 | 6,4 |

Risoluzione del caso «tutto acceso» sul Fermi intero:

```
COSTO fermi completo con sedi: OPTIMAL {'attivita': 284, 'libere': 284,
  'variabili': 12520, 'constraint': 6900, 'secondi': 0.953}
```

**Giudizio: accettabile, con un avvertimento da mettere per iscritto adesso.**
Il ×3,7 sul conteggio dei constraint è reale ma il tempo resta sotto il secondo
sul Fermi intero, cioè nello stesso ordine di grandezza dello spike (~0,55 s con
cinque vincoli). Il numero da tenere d'occhio non è il ×3,7 a due sedi ma la
**crescita nel numero di sedi**: 4008 → 7466 → 12254 passando da 2 a 3 a 4.
Il Fermi ha una sede sola nei dati reali, quindi il Task 17 non lo vedrà; una
scuola con tre plessi sì. La Minor 2 sopra è la mitigazione, e costa poco.

⚠ L'estrapolazione dell'implementatore («cresce come il quadrato del numero di
sedi») è confermata come ordine di grandezza ma è **pessimistica**: normalizzando
per `n(n−1)` si ottiene 2004 / 1244 / 1021, cioè la deduplicazione `posted`
smorza. Resta comunque superlineare.

---

## 6. Esito della suite, verbatim

Cinque esecuzioni consecutive della suite intera (`venv/bin/pytest -q`), dopo
aver rimosso ogni sonda e ripristinato ogni file mutato:

```
290 passed, 9 skipped in 25.93s
290 passed, 9 skipped in 24.11s
290 passed, 9 skipped in 24.81s
290 passed, 9 skipped in 25.56s
290 passed, 9 skipped in 25.92s
```

Nessuna intermittenza, cinque run su cinque. Gli skip, verbatim
(`venv/bin/pytest -q -rs`):

```
SKIPPED arrival_departure: derivazione vacua per il seed 2
SKIPPED arrival_departure: derivazione vacua per il seed 4
SKIPPED max_site_changes: derivazione vacua per il seed 3
SKIPPED max_site_changes: derivazione vacua per il seed 4
SKIPPED max_site_changes: derivazione vacua per il seed 5
SKIPPED structural:site_transition: derivazione vacua per il seed 1
SKIPPED structural:site_transition: derivazione vacua per il seed 2
SKIPPED structural:site_transition: derivazione vacua per il seed 3
SKIPPED structural:site_transition: derivazione vacua per il seed 5
```

La suite non è rossa e non è rimpicciolita (284 → 299 test raccolti).
`git status` pulito a fine review.

---

## 7. Verdetto

**Chiudibile.** Il Task 9 fa quello che il brief chiedeva, e lo fa bene: le
quattro correzioni sono applicate, il difetto della Correzione 1 è stato
riprodotto prima di essere corretto (e la mia riproduzione indipendente
concorda), i due test ADR-018 mordono davvero, e il commit del controller è
giusto. Il codice del builder è, a capienza 1, **esattamente** il checker — un
risultato migliore di quello che il piano prometteva.

Prima di considerare chiusa la famiglia servono però tre cose, nessuna delle
quali è un rifacimento:

1. **Important 2** — correggere `_derive_site_transition` (distanza sulle fasce
   coperte). È un difetto autonomo e il costo è di tre righe.
2. **§ 3** — sostituire i due derivatori con le versioni «costruttive» misurate,
   oppure dichiarare esplicitamente le due famiglie fuori dal banco a testimone.
   Lo stato attuale — dieci casi di banco che valgono 1 e 0 mordenti su 15 seed
   — è la terza forma dello stesso difetto già corretto due volte su questo
   piano (Ruling 16/24 e Ruling 31): un verde che non dimostra niente.
3. **Important 1** — decidere: chiudere `site_transition` con la clausola
   `s == t` (esatta e a costo trascurabile), e mettere per iscritto che
   `T.MAX_SITE_CHANGES` non ha semantica definita su chiavi a capienza
   cumulativa finché il **checker** non la definisce. Questa terza va nella spec
   del modello completo, accanto alla domanda aperta di ADR-018 sulle
   strutturali (Minor 1), non in un giro di correzione del Task 9.
