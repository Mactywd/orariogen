# Task 8 — `MAX_PRESENCE` — brief

Implementi il **Task 8** del piano
`docs/superpowers/plans/2026-08-24-modello-hard-completo.md` (righe 1917–2098).
Leggi quella sezione per intero prima di cominciare: il codice degli Step è
completo e va seguito, **salvo le tre correzioni dichiarate sotto**, che sono
decisioni già prese dal controller e non sono in discussione.

Lavora in `/home/mattia/coding/scuola/orariogen/.claude/worktrees/modello-hard-completo`
(worktree git sul branch `worktree-modello-hard-completo`). Il venv è
`venv/bin/python` e `venv/bin/pytest`. Non uscire dal worktree.

## Contesto

`orariogen` è un generatore di orari scolastici. `domain/analysis/` contiene i
**checker** — predicati con causali nominate, che sono l'autorità su cosa
significhi ogni vincolo. `domain/solver/` contiene la traduzione CP-SAT degli
stessi vincoli. Il criterio di riuscita è un **oracolo differenziale**: una
soluzione del solver, riscritta nei `Placement` e riletta da `check_schedule`,
non deve produrre alcun finding `HARD` **nuovo** rispetto allo stato di
partenza.

Sette task sono già chiusi. Le astrazioni che devi usare esistono già:

- `domain/solver/vocabulary.py` — le primitive derivate. Per te contano
  `covered(key, day, span, signature=None)` (il letterale «questa fascia sta
  fra la prima e l'ultima occupata **dentro `span`**») e
  `day_active(key, day, signature=None)`.
- `domain/solver/residual.py` — ADR-018. Per te conta
  `frozen_occupies(ctx, key, day, slots, rep=None)`.
- `domain/solver/builders/base.py` — `ResourceBuilder`, che fa già il ciclo
  sulle firme di settimana e la deduplicazione: tu implementi solo
  `post(self, ctx, model, row, rep)` e dichiari `TYPE`.
- `domain/solver/builders/time_presence.py` — il file in cui vai, dove vive già
  `MaxGapBuilder`. **Leggilo tutto**: il suo docstring di modulo spiega la
  differenza fra presenza e buchi, ed è il precedente diretto della correzione
  ADR-018 che devi fare anche tu.

## ⚠ La trappola centrale del task: lo `span`

`MaxPresenceChecker` (`domain/analysis/checkers/time_constraints.py`) usa
`_presence_minutes`, che calcola `(slots[-1] - slots[0] + 1) * slot_minutes`
sui slot di **tutto il giorno** e **non passa mai da `_halves`**. Il D.T.B.
(`MAX_GAP_HOURS`) fa l'opposto: lavora per mezza giornata e non conta mai buchi
a cavallo del pranzo.

Usare la mezza giornata qui produrrebbe un vincolo **più largo** del checker.
Lo `span` che passi a `covered` è `range(ctx.grid.slots_per_day)`.

**Leggi il checker** prima di tradurre — non fidarti di questo brief né del
piano. È un vincolo globale del piano: ogni traduzione va derivata leggendo il
checker, non ricordandolo. Su questo piano tre difetti veri sono nati
esattamente dal saltare quel passaggio.

## Le tre correzioni al piano

### 1. ⚠ ADR-018: **clampa, non saltare** (Ruling 23)

Il codice del piano, sul ramo `max_minutes`, fa `continue` sul giorno in cui le
sole congelate hanno già sforato il tetto, col commento «le libere non possono
ridurre una presenza, quindi il vincolo è perso comunque».

La premessa è vera — la presenza è monotona non decrescente, aggiungere
attività a un giorno può solo allargarla — ma **la conclusione è sbagliata**, e
il `continue` va sostituito.

Saltare il vincolo lascia le libere **allargare** quella giornata. Congelate
alle fasce 0-2 (presenza 180 minuti) con tetto 120: saltando il vincolo una
libera può andare alla fascia 5 e portare la presenza a 360. E il finding
`max_presence` porta `minutes=presence` fra le `quantities`, che entrano in
`Finding.key` (`domain/analysis/findings.py`): **una violazione peggiorata è
una violazione nuova** per l'oracolo differenziale. Quindi il `continue` non è
solo più largo del necessario — rompe il criterio di riuscita.

La forma corretta è il **clamp**, identica a quella che `MaxGapBuilder` usa già
in quel file dopo la review del Task 6:

```
cap_effettivo = max(cap, presenza_indotta_dalle_sole_congelate)
```

dove la presenza indotta dalle congelate si calcola a build time dalle celle
fisse (`ctx.by_cell`, filtrando `aid not in ctx.free` e, se `rep` non è `None`,
`aid in ctx.states[rep].activities` — vedi `_frozen_gap_minutes` nello stesso
file, che fa esattamente questo per i buchi). Nel caso pulito
`presenza_congelate <= cap` e il clamp non cambia niente; nel caso sporco il
modello non è mai infattibile per colpa del passato, ma le libere restano
vincolate a non peggiorare la giornata.

Il commento nel codice deve spiegare **perché** il clamp e non il salto — cioè
l'argomento sulle `quantities` qui sopra — non limitarsi a dire cosa fa.

Il test del piano `test_adr018_presenza_gia_sforata_dalle_congelate_non_blocca`
va tenuto (con le congelate alle fasce 0 e 5 il clamp e il salto coincidono,
perché 360 è già il massimo della griglia), ma **aggiungine uno** che li
distingue: congelate alle fasce 0-2, tetto 120, una libera — il solver deve
restare risolvibile **e** la libera non deve finire oltre la fascia 2 di quel
giorno. Col `continue` quel test è rosso; col clamp è verde. Verificalo
davvero, rimettendo il `continue` per un attimo, e incolla l'output rosso nel
report.

### 2. ⚠ Niente `test_max_presence_sul_banco` (Ruling 16)

Il piano lo prevede, ma **non va scritto**: `tests/test_solver_witness.py`
contiene già `test_famiglia`, parametrizzato su `sorted(DERIVERS) × [1..5]`.
Appena registri il derivatore, i cinque casi per seed della famiglia
`MAX_PRESENCE` esistono automaticamente. Scriverli anche nel tuo file sarebbe
un duplicato esatto. I tre task precedenti hanno seguito questa regola, e i
loro file di test lo dicono in testa al modulo: fai lo stesso.

### 3. ⚠ Il derivatore deve dichiarare il proprio potere vincolante (Ruling 24)

Il derivatore del piano non ha `return` e non ha guardia di vacuità. Va
allineato agli altri nove di `tests/solver_harness.py`: **leggi quelli**
(`_derive_min_distribution`, `_derive_arrival_departure`,
`_derive_free_guaranteed` sono i più vicini) e segui la loro convenzione —
`return 0` quando il vincolo derivato non vieta nulla, `return 1` altrimenti,
con una docstring che dice **quando** è vacuo e perché.

Per `MAX_PRESENCE` il vincolo è vacuo quando `picco` copre già la giornata
intera **e** `giorni` copre già `days_per_cycle`: in quel caso qualunque orario
lo soddisfa, e un builder rotto non potrebbe farlo fallire.

## Cosa NON è una violazione (Ruling 25)

Il ramo `days` scrive `max(0, max_days - consumo)` a mano invece di usare
`residual_cap`. **Va bene così**: `residual_cap` lavora su termini
`(peso, id_attività, letterale)` per attività, mentre qui i termini sono
**variabili derivate** (`day_active`), il caso esplicitamente previsto dalla
docstring di `frozen_occupies`. I Task 6 e 7 fanno già così. Non "correggerlo".

## Vincoli globali del piano

1. I test si lanciano con `venv/bin/pytest`.
2. La suite non deve **mai** diventare rossa né **rimpicciolire**. La baseline
   attuale è **269 passed, 2 skipped** — verificala tu prima di cominciare, e
   riporta il numero finale nel report (il numero atteso scritto nel piano,
   250, è stantìo: il piano è stato scritto prima dei Task 6 e 7).
3. Commenti e docstring in **italiano**, identificatori in **inglese** (i nomi
   di variabile locale in italiano sono la convenzione già stabilita in questi
   file dal Task 6: seguila).
4. `domain/analysis/` non deve **mai** importare `ortools`.
5. Nessun builder reinventa una primitiva del vocabolario né calcola a mano un
   residuo (con l'eccezione della Ruling 25 sopra).
6. Ogni traduzione va derivata **leggendo il checker**.
7. `AddMaxEquality`/`AddMinEquality` con una lista vuota non è valido.
8. Le chiavi del registro non cambiano mai.
9. **Un solo commit** per il task, con il trailer
   `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## ⚠ CP-SAT qui è non deterministico

`domain/solver/model.py` non fissa né `random_seed` né `num_search_workers`. Se
un test fallisce a intermittenza, **non è rumore: è un builder troppo lasco**.
È una Ruling già presa su questo piano, dopo che un'intermittenza scambiata per
rumore si è rivelata un difetto vero. Se sospetti intermittenza, rilancia il
file mirato e `tests/test_solver_witness.py` almeno cinque volte.

## Metodo

Segui gli Step del piano nell'ordine: prima i test che falliscono, poi la
verifica che falliscano **per la ragione giusta**, poi il builder, poi il
derivatore, poi la suite intera, poi il commit.

Per ogni test che scrivi, **fallo fallire deliberatamente** (disabilitando il
builder o rimettendo il difetto) e verifica che il fallimento sia quello
atteso. Un test che passerebbe anche col builder assente non dimostra niente:
se ne scrivi uno così — e per ADR-018 è a volte inevitabile — dillo nel report
e appaialo a una controprova che invece morde.

## Cosa consegnare

Un rapporto in `.superpowers/sdd/2026-08-24-modello-hard-completo/task-8-report.md`
con: cosa hai implementato; le deviazioni dal piano e il loro perché; le prove
RED incollate **verbatim** (non parafrasate: incolla l'output di pytest); la
riga di riepilogo finale della suite, verbatim; e i dubbi che ti restano.
Riporta l'essenziale anche nella risposta finale.
