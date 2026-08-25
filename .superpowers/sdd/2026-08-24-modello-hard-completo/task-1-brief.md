### Task 1: Il vocabolario, prima metà — occupazione, copertura, giornate

**Files:**
- Create: `domain/solver/vocabulary.py`
- Modify: `domain/solver/context.py` (rimuove `occupied` e `_occupied`)
- Modify: `domain/solver/model.py` (costruisce `ctx.vocab`)
- Modify: `domain/solver/builders/time_constraints.py` (usa `covered`)
- Test: `tests/test_solver_vocabulary.py`

**Interfaces:**
- Consumes: `SolverContext` (`grid`, `states`, `signatures`, `by_cell`, `x`,
  `cells`, `activities`, `tokens`, `free`), già esistente.
- Produces:
  - `Vocabulary(ctx, model)` con `ctx.vocab` assegnato in `build_model`
  - `vocab.halves() -> list[range]` — `[mattina, pomeriggio]`, la seconda può
    essere vuota
  - `vocab.occupied(key, day, slot, signature=None) -> BoolVar`
  - `vocab.covered(key, day, span, signature=None) -> dict[int, BoolVar]`
  - `vocab.day_active(key, day, signature=None) -> BoolVar`
  - `vocab.half_active(key, day, half, signature=None) -> BoolVar` — `half` è
    `0` (mattina) o `1` (pomeriggio)

⚠ `vocab.occupied` ha la **stessa semantica** di `SolverContext.occupied`, ma
**non** prende più `model`: il vocabolario lo tiene. Ogni chiamante va
aggiornato.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_vocabulary.py
"""Le primitive derivate condivise. Il test che conta e' quello su `covered`:
il parametro `span` distingue il D.T.B. (mezza giornata) da MAX_PRESENCE
(giornata intera), ed e' proprio la differenza che due copie separate del
codice avrebbero perso."""
import pytest
from ortools.sat.python import cp_model

from domain.solver.context import SolverContext
from domain.solver.vocabulary import Vocabulary
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _vocab(env):
    ctx = SolverContext.build(env["schedule"])
    model = cp_model.CpModel()
    for aid in sorted(ctx.activities):
        for (day, slot) in sorted(ctx.cells[aid]):
            ctx.x[(aid, day, slot)] = model.NewBoolVar(f"x_{aid}_{day}_{slot}")
        model.AddExactlyOne([ctx.x[(aid, d, s)] for (d, s) in sorted(ctx.cells[aid])])
    ctx.index_cells()
    return ctx, model, Vocabulary(ctx, model)


def test_halves_pomeriggio_puo_essere_vuoto():
    env = mini_school()
    env["grid"].morning_end_slot = env["grid"].slots_per_day
    env["grid"].save()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    _, _, vocab = _vocab(env)
    mattina, pomeriggio = vocab.halves()
    assert len(list(mattina)) == env["grid"].slots_per_day
    assert list(pomeriggio) == []


def test_half_active_su_meta_vuota_non_esplode():
    """AddMaxEquality con lista vuota e' invalido: la primitiva deve fissare
    la variabile a zero invece di costruire un vincolo malformato."""
    env = mini_school()
    env["grid"].morning_end_slot = env["grid"].slots_per_day
    env["grid"].save()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    _, model, vocab = _vocab(env)
    var = vocab.half_active(env["klass"].pk, 0, 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(var) == 0


def test_covered_span_mezza_giornata_contro_giornata_intera():
    """Due attivita' della stessa classe alle fasce 0 e 5, con la linea di
    meta' giornata a 4. Sulla giornata intera le fasce 1..4 sono 'coperte'
    (stanno fra la prima e l'ultima occupata); sulla sola mattina no, perche'
    li' l'ultima occupata e' la fascia 0."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 5)] == 1)
    key = env["klass"].pk
    giornata = vocab.covered(key, 0, range(0, 6))
    mattina = vocab.covered(key, 0, range(0, 4))
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert [solver.Value(giornata[s]) for s in range(6)] == [1, 1, 1, 1, 1, 1]
    assert [solver.Value(mattina[s]) for s in range(4)] == [1, 0, 0, 0]


def test_day_active_e_memoizzazione():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 2, 1)] == 1)
    key = env["klass"].pk
    attivo, di_nuovo = vocab.day_active(key, 2), vocab.day_active(key, 2)
    assert attivo is di_nuovo          # memoizzata: una variabile, non due
    vuoto = vocab.day_active(key, 3)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(attivo) == 1
    assert solver.Value(vuoto) == 0
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.solver.vocabulary'`

- [ ] **Step 3: Scrivere `domain/solver/vocabulary.py`**

```python
"""Le variabili derivate condivise dai builder: una primitiva per concetto,
costruita una volta sola e memoizzata sulla chiave completa — firma di
settimana inclusa.

Non e' un modulo di comodita'. Piu' builder hanno bisogno delle stesse
costruzioni non banali (il trittico prima/dopo/coperta serve al D.T.B. e a
MAX_PRESENCE; l'occorrenza di una materia in un secchio serve a sei vincoli di
materia). Riscriverle in ogni builder significa replicare in N posti ogni
difetto — e in questo progetto una di queste costruzioni e' gia' stata
sbagliata una volta."""


class Vocabulary:
    def __init__(self, ctx, model):
        self.ctx = ctx
        self.model = model
        self._cache = {}

    def _memo(self, kind, key, make):
        cell = (kind, key)
        if cell not in self._cache:
            self._cache[cell] = make()
        return self._cache[cell]

    def _max_or_zero(self, var, lits):
        """AddMaxEquality con lista vuota e' invalido. Una meta' giornata puo'
        essere vuota (morning_end_slot == slots_per_day), quindi il caso non e'
        teorico: capita in due test esistenti."""
        if lits:
            self.model.AddMaxEquality(var, lits)
        else:
            self.model.Add(var == 0)
        return var

    # --- griglia ---------------------------------------------------------

    def halves(self):
        """[mattina, pomeriggio]. La seconda puo' essere vuota."""
        g = self.ctx.grid
        return [range(0, g.morning_end_slot),
                range(g.morning_end_slot, g.slots_per_day)]

    def half_of(self, slot):
        return 0 if slot < self.ctx.grid.morning_end_slot else 1

    # --- occupazione -----------------------------------------------------

    def occupied(self, key, day, slot, signature=None):
        """La chiave e' occupata in quella cella.

        `signature`, se dato, e' il rappresentante di una firma di settimana:
        il letterale conta solo le attivita' attive in quella firma, come
        farebbe ScheduleState.build(schedule, week=rep) per il checker."""
        def make():
            var = self.model.NewBoolVar(f"occ_{key}_{day}_{slot}_{signature}")
            entries = self.ctx.by_cell.get((key, day, slot), ())
            if signature is not None:
                active = self.ctx.states[signature].activities
                entries = [(aid, lit) for aid, lit in entries if aid in active]
            return self._max_or_zero(var, [lit for _, lit in entries])
        return self._memo("occ", (signature, key, day, slot), make)

    def covered(self, key, day, span, signature=None):
        """{fascia: letterale} — la fascia sta fra la prima e l'ultima
        occupata **dentro `span`**.

        ⚠ `span` non e' un dettaglio: il D.T.B. lo vuole sulla mezza giornata
        (non conta mai buchi a cavallo del pranzo), MAX_PRESENCE sulla giornata
        intera (`_presence_minutes` non passa da `_halves`). Sono due cose
        diverse che si somigliano: qui la differenza e' un argomento visibile
        alla chiamata."""
        span = tuple(span)
        def make():
            occ = {s: self.occupied(key, day, s, signature) for s in span}
            out = {}
            for s in span:
                tag = f"{key}_{signature}_{day}_{span[0] if span else 'x'}_{s}"
                before = self.model.NewBoolVar(f"before_{tag}")
                self._max_or_zero(before, [occ[i] for i in span if i <= s])
                after = self.model.NewBoolVar(f"after_{tag}")
                self._max_or_zero(after, [occ[j] for j in span if j >= s])
                cov = self.model.NewBoolVar(f"covered_{tag}")
                self.model.AddMinEquality(cov, [before, after])
                out[s] = cov
            return out
        return self._memo("covered", (signature, key, day, span), make)

    # --- presenza per giornata e mezza giornata --------------------------

    def day_active(self, key, day, signature=None):
        def make():
            var = self.model.NewBoolVar(f"dayact_{key}_{signature}_{day}")
            lits = [self.occupied(key, day, s, signature)
                    for s in range(self.ctx.grid.slots_per_day)]
            return self._max_or_zero(var, lits)
        return self._memo("day_active", (signature, key, day), make)

    def half_active(self, key, day, half, signature=None):
        """`half`: 0 mattina, 1 pomeriggio."""
        def make():
            var = self.model.NewBoolVar(f"halfact_{key}_{signature}_{day}_{half}")
            lits = [self.occupied(key, day, s, signature)
                    for s in self.halves()[half]]
            return self._max_or_zero(var, lits)
        return self._memo("half_active", (signature, key, day, half), make)
```

- [ ] **Step 4: Rimuovere `occupied` da `SolverContext`**

In `domain/solver/context.py`: cancellare il metodo `occupied` e il campo
`_occupied: dict = field(default_factory=dict)`. Aggiungere invece:

```python
    vocab: object = None      # Vocabulary, assegnato da build_model
```

- [ ] **Step 5: Costruire il vocabolario in `build_model`**

In `domain/solver/model.py`, subito **dopo** `ctx.index_cells()` e **prima**
del ciclo `builder.build(...)`:

```python
    ctx.index_cells()
    ctx.vocab = Vocabulary(ctx, model)
    for builder in builders:
        builder.build(ctx, model)
```

più l'import `from domain.solver.vocabulary import Vocabulary`.

- [ ] **Step 6: Riscrivere `MaxGapBuilder` sul vocabolario**

In `domain/solver/builders/time_constraints.py`, sostituire il corpo del
doppio ciclo su giorni e mezze giornate con:

```python
                terms = []
                for day in range(grid.days_per_cycle):
                    for half in ctx.vocab.halves():
                        if not len(half):
                            continue
                        cov = ctx.vocab.covered(key, day, half, signature=rep)
                        for s in half:
                            terms.append(
                                cov[s] - ctx.vocab.occupied(key, day, s, signature=rep))
```

Il resto del builder — il ciclo sulle firme, il `posted` di deduplicazione, il
`model.Add(grid.slot_minutes * sum(terms) <= ...)` — resta identico. Le
variabili `before`/`after`/`covered` costruite a mano spariscono: le costruisce
`covered`.

- [ ] **Step 7: Eseguire i test nuovi e la suite intera**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v`
Expected: PASS (4 test)

Run: `venv/bin/pytest -q`
Expected: **177 passed** (173 + 4). Nessun test esistente modificato: questa
ondata non cambia il comportamento, solo dove vivono le variabili.

- [ ] **Step 8: Commit**

```bash
git add domain/solver/vocabulary.py domain/solver/context.py domain/solver/model.py domain/solver/builders/time_constraints.py tests/test_solver_vocabulary.py
git commit -m "$(cat <<'EOF'
refactor(solver): il vocabolario delle variabili derivate, prima meta'

occupied() si sposta dal contesto al vocabolario; covered() esce da
MaxGapBuilder e prende un parametro span, perche' MAX_PRESENCE lo vuole
sulla giornata intera dove il D.T.B. lo vuole sulla mezza. Aggiunte
day_active e half_active.

Comportamento invariato: i 173 test verdi restano verdi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

