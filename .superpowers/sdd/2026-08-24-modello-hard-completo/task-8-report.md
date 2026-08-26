# Task 8 — MAX_PRESENCE — report

## Cosa ho implementato

`MaxPresenceBuilder` (`T.MAX_PRESENCE`) in `domain/solver/builders/time_presence.py`,
in coda a `MaxGapBuilder` nello stesso file. Eredita `ResourceBuilder` (ciclo
sulle firme + deduplicazione gia' nella classe base) e implementa solo `post`.

Due rami, letti da `MaxPresenceChecker` (`domain/analysis/checkers/time_constraints.py`,
righe 76–90):

- **`max_minutes`** — per ogni giorno, `covered(key, day, giornata, signature=rep)`
  con `giornata = range(ctx.grid.slots_per_day)` (⚠ **non** `v.halves()`: e' la
  trappola centrale del task, vedi sotto), e
  `model.Add(slot_minutes * sum(cov) <= cap_effettivo)`.
- **`days`** — variabili derivate `day_active` per i giorni non gia' consumati
  dalle congelate, `model.Add(sum(terms) <= max(0, max_days - consumo))`
  (Ruling 25: non passa da `residual_cap`, che lavora su termini per attivita',
  non su variabili derivate — vedi sotto).

Un derivatore, `_derive_max_presence`, aggiunto in `tests/solver_harness.py`
dopo `_derive_free_guaranteed`.

`tests/test_solver_registry.py::test_i_builder_tradotti_finora` aggiornato:
`ResourceTimeConstraint.Type.MAX_PRESENCE` aggiunto all'insieme atteso (non
era nella lista dei file da toccare nel brief, ma e' una conseguenza
necessaria di registrare l'undicesimo builder — lo stesso aggiornamento fatto
nel Task 7 per il decimo).

File di test mirati: `tests/test_solver_max_presence.py` (nuovo), cinque test.
**Non** ho scritto `test_max_presence_sul_banco` (correzione 2 del brief,
Ruling 16): lo copre gia' `test_famiglia` in `tests/test_solver_witness.py`,
parametrizzato su `sorted(DERIVERS) × [1..5]` — i cinque seed della famiglia
esistono in automatico appena il derivatore e' registrato.

## Come ho derivato la traduzione leggendo il checker

`MaxPresenceChecker.violations` (righe 80–90):

```python
def violations(self, state, row, days):
    cap = row.params.get("max_minutes")
    for day, slots in days.items():
        presence = _presence_minutes(state, slots)
        if cap is not None and presence > cap:
            yield _finding(state, "max_presence", row,
                           day=day, minutes=presence, max_minutes=cap)
    max_days = row.params.get("days")
    if max_days is not None and len(days) > max_days:
        yield _finding(state, "max_presence_days", row,
                       days=len(days), max_days=max_days)
```

e `_presence_minutes` (riga 35–36):

```python
def _presence_minutes(state, slots):
    return (slots[-1] - slots[0] + 1) * state.grid.slot_minutes
```

**La trappola.** `_presence_minutes` non passa mai da `_halves` — a differenza
di `MaxGapChecker` (riga 191, `for half in _halves(state, slots)`). Il D.T.B.
lavora per mezza giornata e non conta mai buchi a cavallo del pranzo;
`MAX_PRESENCE` misura `ultima - prima + 1` su **tutta la giornata**. Passare
`v.halves()` invece di `range(grid.slots_per_day)` a `v.covered` avrebbe
prodotto un vincolo **piu' largo** del checker: due presenze corte a cavallo
del pranzo (es. fasce 3 e 4, una per meta') passerebbero come due giornate da
un'ora, mentre il checker le fonde in una presenza sola che le include
entrambe. L'ho dimostrato per davvero, non solo argomentato — vedi "Prove RED"
sotto.

## Le tre correzioni al piano

**1. ADR-018: clamp, non salto (Ruling 23).** Implementato come nel brief:
`cap_effettivo = max(cap, _frozen_presence_minutes(ctx, key, day, rep))`, dove
`_frozen_presence_minutes` (nuova funzione, stesso schema di
`_frozen_gap_minutes` gia' nel file) calcola la presenza indotta dalle sole
attivita' congelate su quel giorno, da `ctx.by_cell` filtrato su `aid not in
ctx.free` e `aid in ctx.states[rep].activities`. Il vincolo resta postato su
**tutti** i giorni, mai saltato — a differenza del `continue` del piano
originale.

**2. Niente `test_max_presence_sul_banco` (Ruling 16).** Vedi sopra.

**3. Il derivatore dichiara il proprio potere vincolante (Ruling 24).**
`_derive_max_presence` restituisce `0` in due casi: quando il docente scelto
a caso non compare in nessuna firma (`giorni == 0`, stessa convenzione di
`_derive_max_half_days`) e quando **entrambi** i rami del checker diventano
banalmente veri per costruzione — `picco >= slots_per_day * slot_minutes` e
`giorni >= days_per_cycle` insieme, cioe' nessuna presenza puo' mai superare
la giornata e nessun conteggio di giorni puo' mai superare il ciclo. In
entrambi i casi un builder rotto non potrebbe far fallire il testimone. Nei
cinque seed provati (1–5) nessuno dei due casi e' scattato (0 skip aggiuntivi
in `test_famiglia` per `MAX_PRESENCE`), ma il guardrail resta corretto per
costruzione, sulla stessa logica difensiva gia' usata da `_derive_max_half_days`.

## Ruling 25 — il ramo `days` non passa da `residual_cap` (confermato, non "corretto")

Come da correzione del brief: `residual_cap` lavora su termini `(peso,
id_attivita', letterale)` per attivita', mentre qui i termini sono variabili
**derivate** (`day_active`) — il caso esplicitamente previsto dalla docstring
di `frozen_occupies`. Il consumo delle congelate si sottrae a mano dal tetto
(`max(0, max_days - consumo)`), come gia' fanno i Task 6 e 7. Non l'ho toccato.

## Prove RED

**Step 2 del piano** — file di test scritto prima del builder, eseguito
contro il registro senza `MaxPresenceBuilder`:

```
$ venv/bin/pytest tests/test_solver_max_presence.py -q
..F..                                                                    [100%]
=================================== FAILURES ===================================
______ test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata _______
...
    giorno, fascia = soluzione.placements[libera.id]
    if giorno == 0:
>       assert fascia <= 2
E       assert 3 <= 2

tests/test_solver_max_presence.py:101: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_max_presence.py::test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata
1 failed, 4 passed in 0.70s
```

Solo un test su cinque fallisce a builder assente: `ResourceTimeConstraint`
righe di tipo non registrato in `BUILDERS` sono semplicemente ignorate da
`ResourceBuilder.build` (nessun errore, nessun vincolo postato), e senza
alcun vincolo CP-SAT su questo modello piccolo tende a compattare le attivita'
per costruzione della ricerca — quattro dei miei cinque test passano "per
fortuna", non perche' dimostrano qualcosa. **Questo e' esattamente il caso che
il brief anticipa** ("per ADR-018 e' a volte inevitabile"): li ho appaiati a
controprove che mordono davvero, con mutazioni deliberate del builder gia'
corretto. Tre mutazioni, ciascuna verificata RED e poi ripristinata
(`git diff` confermato pulito dopo ogni ripristino):

**(a) Lo `span`** — sostituito `range(grid.slots_per_day)` con `v.halves()`
nel ramo `max_minutes` (span per mezza giornata invece che sulla giornata
intera):

```
$ venv/bin/pytest tests/test_solver_max_presence.py::test_la_presenza_include_i_buchi_e_attraversa_il_pranzo -q
F                                                                        [100%]
=================================== FAILURES ===================================
___________ test_la_presenza_include_i_buchi_e_attraversa_il_pranzo ____________
...
    for _day, fasce in per_giorno.items():
>       assert (max(fasce) - min(fasce) + 1) * 60 <= 120
E       assert (((5 - 0) + 1) * 60) <= 120
E        +  where 5 = max([0, 5])
E        +  and   0 = min([0, 5])

tests/test_solver_max_presence.py:41: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_max_presence.py::test_la_presenza_include_i_buchi_e_attraversa_il_pranzo
1 failed in 0.62s
```

Esattamente il meccanismo descritto dal docstring: con lo span sbagliato le
due attivita' finiscono alle fasce 0 e 5 (due "presenze" da un'ora ciascuna
per meta' giornata, che passano il vincolo dimezzato), ma la giornata intera
misura sei ore — il checker le boccerebbe.

**(b) ADR-018, `continue` invece di clamp** — reintrodotto il difetto del
piano originale (`if presenza_congelate > cap: continue`, tetto invariato
altrove):

```
$ venv/bin/pytest tests/test_solver_max_presence.py::test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata -q
...
    giorno, fascia = soluzione.placements[libera.id]
    if giorno == 0:
>       assert fascia <= 2
E       assert 3 <= 2

tests/test_solver_max_presence.py:101: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_max_presence.py::test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata
1 failed in 0.62s
```

Col `continue` il vincolo del giorno 0 sparisce del tutto (le congelate a
0-1-2 hanno gia' sforato i 120' dichiarati), e la libera puo' finire alla
fascia 3 (o oltre), peggiorando la presenza da 180' a un valore maggiore —
esattamente l'argomento sulle `quantities`/`Finding.key` del brief.

**(c) Il ramo `days` disabilitato** (`if False and max_days is not None:`):

Il mio primo tentativo di test per questo ramo (asserzione debole "al piu' N
giorni") **non mordeva**: verificato disabilitando il ramo, il test passava
comunque (CP-SAT compatta di default su questa fixture piccola). L'ho scartato
e riscritto con un argomento di capienza — docente indisponibile ovunque
tranne una fascia per ciascuno di tre giorni, tre attivita' che quindi
**richiedono** tre giorni distinti, tetto a due giorni → deve essere
INFEASIBLE:

```
$ venv/bin/pytest tests/test_solver_max_presence.py::test_max_presence_giorni_morde -q
...
    soluzione = solve(env["schedule"], time_limit=30)
>   assert soluzione.status == "INFEASIBLE", soluzione.stats
E   AssertionError: {'attivita': 3, 'libere': 3, 'variabili': 9, 'constraint': 9, ...}
E   assert 'OPTIMAL' == 'INFEASIBLE'

tests/test_solver_max_presence.py:132: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_max_presence.py::test_max_presence_giorni_morde - As...
1 failed in 0.63s
```

Dopo ogni mutazione ho ripristinato il file da una copia integra
(`diff` confermato vuoto) prima di procedere alla successiva.

## GREEN

```
$ venv/bin/pytest tests/test_solver_max_presence.py -q
.....                                                                    [100%]
5 passed in 0.67s
```

```
$ venv/bin/pytest tests/test_solver_witness.py -v -k max_presence
tests/test_solver_witness.py::test_famiglia[max_presence-1] PASSED
tests/test_solver_witness.py::test_famiglia[max_presence-2] PASSED
tests/test_solver_witness.py::test_famiglia[max_presence-3] PASSED
tests/test_solver_witness.py::test_famiglia[max_presence-4] PASSED
tests/test_solver_witness.py::test_famiglia[max_presence-5] PASSED
======================= 5 passed, 52 deselected in 1.67s =======================
```
(nessuno dei cinque seed ha attivato la vacuita' del derivatore; i 2 skip
della baseline sono su altre famiglie, invariati.)

## Suite intera

Baseline verificata prima di iniziare: **269 passed, 2 skipped**.

```
$ venv/bin/pytest -q
........................................................................ [ 25%]
........................................................................ [ 51%]
..................................................................s.s... [ 76%]
.................................................................        [100%]
279 passed, 2 skipped in 22.86s
```

Delta = +10 (5 test mirati nuovi + 5 casi parametrizzati nuovi da
`test_famiglia` per `max_presence`). Nessuna riduzione, nessun rosso. Rilanciato
`tests/test_solver_max_presence.py` + `tests/test_solver_witness.py` +
`tests/test_solver_registry.py` cinque volte di seguito per escludere
intermittenza CP-SAT (nota del brief): stabile a **66 passed, 2 skipped** in
tutte e cinque le esecuzioni.

## Deviazioni dal brief

1. **`tests/test_solver_registry.py` aggiornato**, non elencato fra i file del
   brief ma necessario: `test_i_builder_tradotti_finora` fissa esplicitamente
   l'insieme delle chiavi registrate, e registrare `MaxPresenceBuilder` senza
   aggiornarlo lo avrebbe rotto. Stessa cosa gia' fatta nel Task 7 per il
   decimo builder.
2. **Test `days` riscritto rispetto al piano**: l'asserzione originale ("al
   piu' N giorni" su un'istanza senza indisponibilita') non morde su questa
   fixture, perche' CP-SAT compatta di default anche senza vincolo. Sostituita
   con uno scenario a capienza forzata (INFEASIBLE atteso), verificato che
   morde davvero — vedi "Prove RED (c)" sopra.
3. **`test_adr018_presenza_gia_sforata_dalle_congelate_non_blocca`** (il test
   del piano con congelate a 0 e 5) e' rimasto, ma **non distingue** clamp da
   salto — con le fasce estreme della griglia i due comportamenti coincidono
   (360' e' gia' il massimo raggiungibile). L'ho tenuto come richiesto dal
   brief e appaiato a
   `test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata`, che e'
   la vera controprova (congelate a 0-1-2, tetto 120): quella distingue i due
   comportamenti e morde, come dimostrato sopra.

## Dubbi

Nessuno bloccante. Un'osservazione minore: `_frozen_presence_minutes` e
`_frozen_gap_minutes` condividono lo schema (celle fisse filtrate su
`ctx.free`/`ctx.states[rep].activities`) ma non condividono codice — la
differenza (giornata intera vs. per-mezza-giornata, e per-giorno vs.
aggregato-settimana) mi e' parsa sufficiente a non giustificare
un'estrazione, ma se il modello completo aggiunge un terzo vincolo con lo
stesso schema varrebbe la pena fattorizzarlo.
