# Task 6 — Report

## Cosa ho implementato

1. **`domain/solver/builders/base.py`** (nuovo) — `ResourceBuilder`, la classe
   base condivisa dai builder «una risorsa, riga per riga». Porta nella classe
   base il ciclo su `ctx.time_rows` filtrato per `TYPE`, il ciclo sulle firme
   di settimana (`ctx.signatures`), il calcolo di `touching` (le attività
   attive su quella chiave in quella firma), lo skip quando nessuna è libera
   (`any(aid in ctx.free for aid in touching)` — «un fatto, non una
   decisione»), e la deduplicazione per firme con lo stesso insieme di
   attività attive (`posted`). L'hook `post(self, ctx, model, row, rep)` è
   astratto (`NotImplementedError`). Codice identico a quanto specificato nel
   brief, verbatim.

2. **`domain/solver/residual.py`** — aggiunta `frozen_occupies(ctx, key, day,
   slots, rep=None) -> bool`: vero se un'attività **congelata** (non in
   `ctx.free`) occupa quella chiave in una di quelle fasce, rispettando la
   firma quando data. Codice identico al brief.

3. **`domain/solver/builders/time_presence.py`** — `MaxGapBuilder` riscritto
   sullo scheletro: eredita `ResourceBuilder`, `TYPE = T.MAX_GAP_HOURS`, e
   conserva solo il corpo del vincolo come `post()`. **Più il guardiano
   ADR-018** che il brief non copriva (vedi sotto): `_frozen_gap_minutes(ctx,
   key, rep)`, che calcola il buco settimanale (in minuti) indotto dalle
   **sole** attività congelate su quella chiave e firma — usando le posizioni
   fisse note a build time (`ctx.cells[aid]` per le congelate), non
   `vocab.covered`/`vocab.occupied` (che mescolano libere e congelate). Se
   quel numero da solo supera già `max_gap_minutes`, `post()` ritorna senza
   postare nulla per quella firma — con un commento che spiega perché. Il
   docstring di modulo è stato esteso con una sezione dedicata a questa
   estensione di ADR-018.

4. **`domain/solver/builders/time_counting.py`** (nuovo) — `MaxHoursBuilder`
   (`T.MAX_HOURS`) e `MaxHalfDaysBuilder` (`T.MAX_HALF_DAYS`), entrambi su
   `ResourceBuilder`. Codice identico al brief (vedi sezione «Come ho derivato
   le tre traduzioni» sotto per la lettura dei checker corrispondenti).

5. **`domain/solver/builders/__init__.py`** — importa `time_counting` per
   registrare i due nuovi builder.

6. **`tests/solver_harness.py`** — due nuovi derivatori, `_derive_max_hours`
   (chiave `RT.MAX_HOURS`, causali `{max_hours_day, max_hours_morning,
   max_hours_afternoon}`) e `_derive_max_half_days` (chiave
   `RT.MAX_HALF_DAYS`, causali `{max_half_days, only_half_day}`). **Ho dovuto
   correggere una lacuna del brief**: il codice mostrato nello Step 7 non ha
   un `return` esplicito in nessuno dei due derivatori, il che li avrebbe resi
   sempre vacui secondo la convenzione documentata sopra `deriver()` (la
   funzione deve restituire il "potere vincolante", un intero; `None` è
   falsy, quindi `run_family` avrebbe fatto sempre `pytest.skip` — le due
   famiglie `_sul_banco` non avrebbero mai eseguito il passo 2/3, e lo Step 8
   del brief ("PASS 12 test", "225 passed") sarebbe stato falso: i test
   sarebbero comparsi come `skipped`, non `passed`). Ho aggiunto:
   - `_derive_max_hours`: `return 1` incondizionato — ogni classe della
     fixture ha sempre almeno un'attività attiva in almeno una firma
     (`_make_activities` crea `max(2, capienza // 2)` attività per classe),
     quindi il picco di `day_minutes` è sempre positivo: mai vacuo.
   - `_derive_max_half_days`: `return 1 if peggiore > 0 else 0` — il docente
     scelto a caso fra 4 può, con piccola probabilità, non comparire in
     nessuna attività del testimone; in quel caso il vincolo creato non tocca
     mai una cella e `ResourceBuilder` non lo posta mai (skip per "nessuna
     firma con letterali liberi che toccano la chiave"), quindi è
     genuinamente vacuo — coerente con la convenzione di `_derive_unavailability`.

7. **`tests/test_solver_time_counting.py`** (nuovo) — i quattro test del
   brief (`test_max_hours_sul_banco` × 5 seed, `test_max_half_days_sul_banco`
   × 5 seed, `test_max_hours_morde`,
   `test_adr018_una_congelata_gia_in_violazione_non_blocca_il_solver`), **più
   un quinto test che ho scritto io**,
   `test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver`, per
   verificare esplicitamente il guardiano ADR-018 su `MaxGapBuilder` (non
   coperto da nessun test nel brief, dato che il brief tratta l'aggiunta
   dell'ADR-018 solo sul `MAX_HOURS` residuo lineare). 13 test totali nel
   file.

## File modificati/creati

- `domain/solver/builders/base.py` (nuovo)
- `domain/solver/builders/time_counting.py` (nuovo)
- `domain/solver/builders/time_presence.py` (modificato)
- `domain/solver/builders/__init__.py` (modificato)
- `domain/solver/residual.py` (modificato)
- `tests/solver_harness.py` (modificato)
- `tests/test_solver_time_counting.py` (nuovo)
- `tests/test_solver_registry.py` (modificato — vedi sotto, non nella lista del brief ma necessario)
- `tests/test_solver_residual.py` (modificato — copertura diretta di `frozen_occupies`, non nella lista del brief ma coerente con lo stile esistente)

### Una rottura non prevista dal brief, e come l'ho risolta

`tests/test_solver_registry.py` conteneva `test_i_cinque_builder_dello_spike`,
che fissa con un'uguaglianza esatta l'insieme `BUILDERS` ai cinque dello
spike. Aggiungendo `MAX_HOURS` e `MAX_HALF_DAYS` quel test rompe
necessariamente (`AssertionError: Extra items in the left set:
ResourceTimeConstraint.Type.MAX_HOURS, ResourceTimeConstraint.Type.MAX_HALF_DAYS`).
Non è nella lista `Modify` del brief, ma il vincolo globale #2 ("nessun task
può lasciare la suite rossa") lo richiede. Ho rinominato il test in
`test_i_builder_tradotti_finora` e aggiornato l'insieme atteso a sette chiavi,
con un commento che dice esplicitamente che l'insieme cresce task dopo task e
non è più "i cinque dello spike".

## Come ho derivato le tre traduzioni leggendo il checker

Letto `domain/analysis/checkers/time_constraints.py` (non a memoria).

**MAX_HOURS** — `MaxHoursChecker.violations` (righe 59–72):
```python
def violations(self, state, row, days):
    sm = state.grid.slot_minutes
    for day, slots in days.items():
        morning, afternoon = _halves(state, slots)
        checks = [("max_hours_day", "day_minutes", len(slots)),
                  ("max_hours_morning", "morning_minutes", len(morning)),
                  ("max_hours_afternoon", "afternoon_minutes", len(afternoon))]
        for code, key, n_slots in checks:
            cap = row.params.get(key)
            if cap is not None and n_slots * sm > cap:
                yield _finding(...)
```
Tre controlli **indipendenti per giornata** (non un budget settimanale come
il D.T.B.): `day_minutes`, `morning_minutes`, `afternoon_minutes`, ciascuno
un conteggio di fasce distinte (`len(slots)`) moltiplicato per `slot_minutes`
e confrontato **giorno per giorno**. Questo giustifica il ciclo `for day in
range(...)` con tre `spans` indipendenti in `MaxHoursBuilder.post`, e l'uso di
`residual_cap` — un vincolo lineare per giornata, non aggregato sulla
settimana — cosa che invece **non** vale per `MaxGapBuilder` (budget
settimanale) e neanche del tutto per `MaxHalfDaysBuilder` (vedi sotto).

**MAX_HALF_DAYS** — `MaxHalfDaysChecker.violations` (righe 137–151):
```python
def violations(self, state, row, days):
    worked, both = 0, []
    for day, slots in days.items():
        morning, afternoon = _halves(state, slots)
        worked += bool(morning) + bool(afternoon)
        if morning and afternoon:
            both.append(day)
    cap = row.params.get("max_half_days")
    if cap is not None and worked > cap:
        yield _finding(state, "max_half_days", row, half_days=worked, max_half_days=cap)
    if row.params.get("only_half_day_per_day"):
        for day in both:
            yield _finding(state, "only_half_day", row, day=day)
```
Due controlli distinti: (a) `worked` è la somma **su tutta la settimana** di
`bool(mattina)+bool(pomeriggio)` per giorno — **questo sì** è un budget
settimanale, non giornaliero, e giustifica sommare `half_active` su **tutte**
le mezze giornate della griglia in `MaxHalfDaysBuilder.post` (non
`residual_cap` puro: `half_active` è una variabile derivata, non un letterale
di attività, quindi serve `frozen_occupies` per la regola di forzatura); (b)
`only_half_day_per_day` è un vincolo **per giorno** separato (`AddAtMostOne`
fra le due `half_active` dello stesso giorno), coerente col fatto che il
checker itera `both` (i singoli giorni in violazione), non un totale.
`state.grid.slot_minutes` non compare in questo checker: conferma che qui non
si contano minuti, solo presenze booleane — coerente col non usare
`slot_minutes` in `MaxHalfDaysBuilder`.

**MAX_GAP_HOURS** (per il guardiano ADR-018, riletto per verificare
l'estensione) — `MaxGapChecker.violations` (righe 187–199):
```python
def violations(self, state, row, days):
    sm = state.grid.slot_minutes
    total = 0
    for day, slots in days.items():
        for half in _halves(state, slots):
            if len(half) >= 2:
                total += (half[-1] - half[0] + 1 - len(half)) * sm
    cap = row.params["max_gap_minutes"]
    if total > cap:
        yield _finding(...)
```
Confermato: `total` si accumula su **tutte** le mezze giornate della
settimana e si confronta **una volta sola** con `cap` — è il budget
settimanale che il changelog del 2026-08-24 descrive. Il calcolo
`(half[-1] - half[0] + 1 - len(half))` è esattamente la formula che ho
riusato in `_frozen_gap_minutes`, applicata alle sole fasce occupate da
congelate. Questo mi ha confermato che il guardiano ADR-018 deve sommare
**su tutta la settimana** (non fascia per fascia) prima di confrontare col
tetto, come richiesto esplicitamente dal mio brief supplementare.

## TDD — RED e GREEN

### RED

Comando:
```
venv/bin/pytest tests/test_solver_time_counting.py -q
```
Output (rilevante, alla lettera):
```
        soluzione = solve(env["schedule"], time_limit=30)
        assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
>       assert soluzione.placements[libera.id][0] != 0   # non il giorno gia' pieno
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert 0 != 0

tests/test_solver_time_counting.py:65: AssertionError
_______ test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver _______
    ...
    soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
E       AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 148, 'constraint': 126, ...}
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
E        +  where 'INFEASIBLE' = Solution(status='INFEASIBLE', placements={}, stats={'attivita': 3, 'libere': 1, 'variabili': 148, 'constraint': 126, 'secondi': 0.012}).status

tests/test_solver_time_counting.py:98: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_time_counting.py::test_max_hours_sul_banco[1] - Asse...
FAILED tests/test_solver_time_counting.py::test_max_hours_sul_banco[2] - Asse...
FAILED tests/test_solver_time_counting.py::test_max_hours_sul_banco[3] - Asse...
FAILED tests/test_solver_time_counting.py::test_max_hours_sul_banco[4] - Asse...
FAILED tests/test_solver_time_counting.py::test_max_hours_sul_banco[5] - Asse...
FAILED tests/test_solver_time_counting.py::test_max_half_days_sul_banco[1] - ...
FAILED tests/test_solver_time_counting.py::test_max_half_days_sul_banco[2] - ...
FAILED tests/test_solver_time_counting.py::test_max_half_days_sul_banco[3] - ...
FAILED tests/test_solver_time_counting.py::test_max_half_days_sul_banco[4] - ...
FAILED tests/test_solver_time_counting.py::test_max_half_days_sul_banco[5] - ...
FAILED tests/test_solver_time_counting.py::test_max_hours_morde - assert 3 <= 2
FAILED tests/test_solver_time_counting.py::test_adr018_una_congelata_gia_in_violazione_non_blocca_il_solver
FAILED tests/test_solver_time_counting.py::test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver
13 failed in 0.77s
```
Fallimento atteso: nessun builder per `MAX_HOURS`/`MAX_HALF_DAYS` esisteva
ancora (`_sul_banco` falliscono con `nessun derivatore per ...` prima che
scrivessi i derivatori, poi con INFEASIBLE/soluzione sporca una volta
aggiunti i derivatori ma non i builder), `test_max_hours_morde` fallisce
perché nessun vincolo limita le tre attività a due ore/giorno (finiscono
tutte sullo stesso giorno), ed entrambi i test ADR-018 falliscono perché
senza builder specifico non c'è nessun residuo/guardiano a proteggere le
libere dal passato sporco.

### GREEN

Comando:
```
venv/bin/pytest tests/test_solver_time_counting.py -q
```
Output:
```
.............                                                            [100%]
13 passed in 2.87s
```

Comando (suite intera):
```
venv/bin/pytest -q
```
Output:
```
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 88%]
...........................                                              [100%]
243 passed in 18.81s
```
Nota sul conteggio: 243, non i 225 attesi dal brief (213+12). La differenza
si spiega interamente:
- +1 rispetto ai 12 attesi nel file nuovo: ho aggiunto
  `test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver` (13 nel
  file, non 12).
- +10 in `tests/test_solver_witness.py::test_famiglia`, che parametrizza su
  `sorted(DERIVERS, key=str) × [1,2,3,4,5]`: con due derivatori in più (7
  invece di 5 chiavi), 2×5=10 combinazioni in più. Non è nella lista del
  brief ma è una conseguenza diretta e corretta di aver registrato i due
  nuovi derivatori nel registro condiviso.
- +4 in `tests/test_solver_residual.py`: la copertura diretta di
  `frozen_occupies` che ho aggiunto io.
- La baseline reale letta con `venv/bin/pytest -q` prima di qualunque
  modifica era **216 passed** (non 213 come scritto nel brief — verificato
  con un run pulito prima di iniziare). 216 + 13 (nuovo file) + 10 (witness) +
  4 (residual) = 243, esattamente il numero letto.

## Verifica che i builder mordono

**`MaxHoursBuilder`** — disabilitato temporaneamente `post()` (return
immediato) e rilanciato:
```
venv/bin/pytest tests/test_solver_time_counting.py -q -k "max_hours"
```
Output (rilevante):
```
>       assert max(per_giorno.values()) <= 2
E       assert 3 <= 2
E        +  where 3 = max(dict_values([3]))
...
3 failed, 3 passed, 7 deselected in 1.80s
```
(`test_max_hours_sul_banco[1]`, `[2]`, e `test_max_hours_morde` falliscono —
le tre attività finiscono tutte sullo stesso giorno). Ripristinato e
riverificato verde.

**`MaxHalfDaysBuilder`** — disabilitato temporaneamente `post()`:
```
venv/bin/pytest tests/test_solver_time_counting.py -q -k "max_half_days"
```
Output (rilevante):
```
E       AssertionError: max_half_days accetta un piazzamento che il checker boccia (seed 5): [('max_half_days', (5,), (), (('half_days', 6), ('max_half_days', 4)))]
...
1 failed, 4 passed, 8 deselected in 1.65s
```
(seed 5 produce una soluzione con 6 mezze giornate lavorate contro un tetto
di 4 — esattamente il finding che il checker deve sollevare). Ripristinato e
riverificato verde.

**Guardiano ADR-018 su `MaxGapBuilder`** — disattivato temporaneamente con
`if False and _frozen_gap_minutes(...)`:
```
venv/bin/pytest tests/test_solver_time_counting.py::test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver -q
```
Output (rilevante):
```
>       assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
E       AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 148, 'constraint': 126, ...}
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
1 failed in 0.65s
```
Conferma che senza il guardiano il modello ricade esattamente nel difetto che
ADR-018 vieta: una violazione preesistente nelle sole congelate rende
INFEASIBLE il modello anche con una libera disponibile altrove. Ripristinato
e riverificato verde con la suite intera (243 passed).

## Autorevisione

- **Completezza**: implementati `ResourceBuilder`, `frozen_occupies`,
  `MaxHoursBuilder`, `MaxHalfDaysBuilder`, i due derivatori, il guardiano
  ADR-018 su `MaxGapBuilder`, e ho verificato (senza fidarmi) il falso
  positivo noto di `nuove()` — non l'ho usato in questo task (nessun test qui
  passa da `violazioni()`/`nuove()` di `test_solver_oracle.py`), quindi
  quell'avvertimento non si applicava direttamente al mio lavoro.
- **Qualità**: nomi coerenti con lo stile esistente (`_frozen_gap_minutes`
  segue lo stile di `_presence_minutes`/`_halves` nel checker). Docstring in
  italiano, identificatori in inglese.
- **Disciplina (YAGNI)**: non ho aggiunto un guardiano ADR-018 anche al ramo
  `only_half_day_per_day` di `MaxHalfDaysBuilder` (`AddAtMostOne` su due
  `half_active` derivate) — il brief lo lascia esplicitamente senza
  guardiano, il testimone non lo esercita mai (dichiarato "non si deriva"),
  e le mie istruzioni supplementari menzionano solo `MaxGapBuilder`. Ne
  scrivo sotto come dubbio aperto, non l'ho corretto di mia iniziativa per
  restare nel perimetro del task.
- **Test**: tutti verificano comportamento vero (non solo "non lancia
  eccezioni") — ho verificato il morso con disattivazioni temporanee e
  ripristini, riportati sopra con l'output alla lettera.
- **Codice pulito**: nessun residuo di debug lasciato nei file finali
  (verificato rileggendo `time_presence.py` e `time_counting.py` dopo i
  ripristini, e con la suite verde).

## Dubbi

1. **`MaxHalfDaysBuilder.only_half_day_per_day` non ha un guardiano ADR-018.**
   Se le sole attività congelate di un giorno occupano sia mattina sia
   pomeriggio (violazione preesistente), `AddAtMostOne` fra le due
   `half_active` derivate — che sarebbero entrambe forzate a 1 dalle
   congelate — renderebbe il modello INFEASIBLE per colpa del passato, lo
   stesso difetto che ho corretto su `MaxGapBuilder`. Il brief mostra questo
   ramo senza guardiano e le mie istruzioni supplementari menzionano solo
   `MaxGapBuilder` esplicitamente; il banco di prova non lo esercita mai
   (`only_half_day_per_day` "non si deriva" per dichiarazione esplicita del
   brief). Non l'ho corretto per restare nel perimetro assegnato, ma lo
   segnalo perché è lo stesso pattern di bug, non ancora chiuso in questo
   builder.
2. Il numero di test riportato dal brief (225 = 213+12) non coincide con
   quanto osservato (243). Ho verificato che la differenza è interamente
   spiegabile (baseline reale 216 non 213, +1 test mio, +10 dal banco di
   prova parametrizzato su DERIVERS, +4 di copertura diretta di
   `frozen_occupies`) — non credo sia un problema, ma lo segnalo perché il
   brief lo dichiarava diversamente.

---

## Rapporto di correzione — giro 1 di 5

Il revisore ha confermato le tre traduzioni fedeli, il guardiano D.T.B. al
livello giusto (settimana) e dimostrato necessario, i due `return` sui
derivatori corretti, e il test del registro non allentato. Restavano due
Important, entrambi sulla stessa regola (ADR-018), più un requisito nuovo del
controller.

### Important 1 — guardiano ADR-018 mancante su `only_half_day_per_day`

Il mio stesso dubbio 1 (segnalato ma non corretto nel giro precedente) è
stato confermato **fondato e dimostrabile per costruzione**: due congelate
dello stesso docente, una in mattina e una in pomeriggio dello stesso giorno,
forzano entrambe le `half_active` derivate a 1 (via `AddExactlyOne` sul
singoletto → `occupied` a 1 → `AddMaxEquality` a 1), e
`AddAtMostOne([1, 1])` è insoddisfacibile — esattamente il difetto che
ADR-018 vieta, nello stesso file (concettualmente) in cui era già stato
corretto sul D.T.B.

**Correzione** in `domain/solver/builders/time_counting.py`,
`MaxHalfDaysBuilder.post`, ramo `only_half_day_per_day`: salta
`AddAtMostOne` per un giorno solo quando **entrambe** le metà sono già
occupate da congelate (`frozen_occupies(ctx, key, day, mattina, rep) and
frozen_occupies(ctx, key, day, pomeriggio, rep)`); con una sola metà
congelata il vincolo si posta comunque, e degrada correttamente a «l'altra
metà deve restare a 0».

**Test nuovo**, come richiesto (il ramo non era provato in nessuna
direzione — l'affermazione del brief che fosse coperto da
`test_max_hours_morde` era falsa, quel test riguarda `MAX_HOURS`):
`tests/test_solver_time_counting.py::test_adr018_only_half_day_gia_sforato_dalle_congelate_non_blocca_il_solver`.
Due congelate LOCKED_IN_PLACE dello stesso docente, day=0 slot=0 (mattina) e
day=0 slot=4 (pomeriggio, morning_end_slot=4 in `mini_school`), più una
terza attività libera dello stesso docente; `ResourceTimeConstraint` con
`only_half_day_per_day=True` e nessun `max_half_days` (per isolare il ramo).
Verifica che `solve()` resti FEASIBLE/OPTIMAL.

**RED verificato** disattivando temporaneamente il guardiano
(`if False and (...)`) e rilanciando solo il nuovo test:
```
venv/bin/pytest tests/test_solver_time_counting.py::test_adr018_only_half_day_gia_sforato_dalle_congelate_non_blocca_il_solver -q
```
Output (rilevante, alla lettera):
```
        soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
E       AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 72, 'constraint': 50, ...}
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
E        +  where 'INFEASIBLE' = Solution(status='INFEASIBLE', placements={}, stats={'attivita': 3, 'libere': 1, 'variabili': 72, 'constraint': 50, 'secondi': 0.018}).status

tests/test_solver_time_counting.py:126: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_time_counting.py::test_adr018_only_half_day_gia_sforato_dalle_congelate_non_blocca_il_solver
1 failed in 0.67s
```
Ripristinato il guardiano subito dopo.

### Important 2 — il guardiano D.T.B. spegneva invece di clampare

Colpa dichiarata dal controller: le istruzioni supplementari originali
dicevano testualmente «non si posta», e avevo implementato esattamente
quello. Il revisore ha mostrato che spegnere l'intero vincolo per la firma è
sbagliato: il D.T.B. è un budget **settimanale** che include giorni mai
toccati dalle congelate, dove le attività libere restano perfettamente in
grado di aprire buchi (o di richiuderne uno delle congelate) — quindi «è un
fatto, non una decisione» non vale, e il debito non è irrecuperabile.

**Correzione** in `domain/solver/builders/time_presence.py`,
`MaxGapBuilder.post`: il tetto effettivamente postato è
`max(row.params["max_gap_minutes"], _frozen_gap_minutes(ctx, key, rep))`
invece di un `return` anticipato — l'analogo esatto di
`max(0, cap - consumo)` di `residual_cap`, qui scritto come `max(cap,
consumo)` perché tetto e consumo vivono sulla stessa scala (minuti di buco),
non sottratti l'uno dall'altro. Il vincolo resta postato su **tutti** i
giorni della firma. Aggiornato anche il docstring di modulo, che descriveva
esplicitamente (e ora scorrettamente) lo spegnimento.

Nessun test nuovo richiesto dal revisore per questo punto (nessun banco di
prova esistente instrada le sole congelate oltre al tetto su più di un
giorno). Ho comunque aggiornato il docstring del test esistente
(`test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver`) per
descrivere correttamente il clamp invece dello spegnimento, e l'ho
rilanciato — insieme a tutto `test_solver_max_gap.py`, che non ho toccato ma
che esercita lo stesso `MaxGapBuilder.post` — per verificare che restasse
verde con la nuova implementazione:
```
venv/bin/pytest tests/test_solver_time_counting.py tests/test_solver_max_gap.py -q
```
Output:
```
...................                                                      [100%]
19 passed in 3.11s
```
(14 in `test_solver_time_counting.py` — le 4 del brief + i due test ADR-018
aggiunti di mia iniziativa nel giro precedente + il nuovo test Important 1
di questo giro — più 5, invariati, in `test_solver_max_gap.py`.)

### Requisito del controller — rete di sicurezza su `ResourceBuilder.TYPE`

Aggiunto `assert self.TYPE is not None, type(self).__name__` in testa a
`ResourceBuilder.build` (`domain/solver/builders/base.py`): una sottoclasse
che eredita `build()` supera sempre
`test_ogni_builder_implementa_almeno_un_hook` per ereditarietà, quindi un
`TYPE` dimenticato la renderebbe silenziosamente vacua senza che nessun test
se ne accorga.

**Non ho legato `TYPE` alla chiave di `@register`** come suggerito
opzionalmente dal revisore: l'unico modo che ho trovato per farlo senza
duplicazione richiede che il decoratore `register()` in
`domain/solver/registry.py` assegni `cls.TYPE` (o un attributo equivalente)
al momento della registrazione — cioè modificare `registry.py`, esplicitamente
escluso dalle istruzioni del controller («se richiede modifiche a
registry.py, non farlo e dimmelo»). Lo segnalo qui come richiesto: **serve
una decisione del controller** se si vuole comunque chiudere questo punto
Minor, perché tocca il file condiviso fra `domain/analysis` e
`domain/solver`.

### Comandi lanciati e output — verifica finale

Test mirati sul codice emendato:
```
venv/bin/pytest tests/test_solver_time_counting.py -q
```
```
..............                                                            [100%]
14 passed in 2.91s
```

```
venv/bin/pytest tests/test_solver_time_counting.py tests/test_solver_max_gap.py tests/test_solver_registry.py tests/test_solver_residual.py -q
```
```
..................................                                       [100%]
34 passed in 3.13s
```
(tutti e quattro i file toccati direttamente o indirettamente da questo giro
di correzione: 14 + 5 + 6 + 9 = 34, torna.)

Suite intera, una volta prima di committare:
```
venv/bin/pytest -q
```
```
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 88%]
............................                                             [100%]
244 passed in 18.61s
```
243 (fine giro precedente) + 1 (il nuovo test Important 1) = 244, torna.

Nessun fallimento intermittente osservato: ogni comando è stato lanciato una
sola volta, tutti verdi al primo colpo. Non ho quindi nulla da segnalare
sotto l'avvertenza CP-SAT non deterministico per questo giro.

### File modificati in questo giro

- `domain/solver/builders/base.py` — assert `TYPE is not None`.
- `domain/solver/builders/time_counting.py` — guardiano ADR-018 su
  `only_half_day_per_day`.
- `domain/solver/builders/time_presence.py` — guardiano D.T.B. da
  spegnimento a clamp, docstring di modulo aggiornato.
- `tests/test_solver_time_counting.py` — nuovo test Important 1, docstring
  del test D.T.B. corretto per descrivere il clamp.

Commit: `28c90ef` — fix(solver): correzioni Important 1 e 2 della review Task 6.
