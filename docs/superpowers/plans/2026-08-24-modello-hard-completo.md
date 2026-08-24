# Il modello hard completo — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tradurre in CP-SAT i ventuno vincoli restanti del registro, sopra un
vocabolario di variabili derivate condiviso e la regola ADR-018 sull'input
sporco, con un generatore a testimone come criterio di riuscita.

**Architecture:** un modulo `vocabulary.py` costruisce **una volta sola** ogni
variabile derivata di cui più builder hanno bisogno (occupazione, copertura
fra prima e ultima fascia, giornata/mezza giornata attiva, occorrenza di
materia in un secchio, posizione, sede). Un modulo `residual.py` spezza ogni
espressione lineare in «parte costante delle attività congelate + parte
libera», e clampa a zero i tetti residui negativi (ADR-018). I builder non
costruiscono variabili condivise e non calcolano residui a mano: leggono il
vocabolario e chiamano l'helper. Il banco di prova genera **prima** un orario
valido, **poi** le righe di vincolo che quell'orario soddisfa, e infine chiede
al solver di ritrovarne uno: l'orario iniziale è un testimone che rende
impossibile a un builder passare i test essendo vacuo.

**Tech Stack:** Python 3, Django (solo ORM e `manage.py`), OR-Tools CP-SAT
(`ortools.sat.python.cp_model`), pytest + `pytest-django`. Nessuna nuova
dipendenza.

**Spec:** [docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md](../specs/2026-08-24-modello-hard-completo-design.md)

## Global Constraints

Valgono per **ogni** task. Non vengono ripetute nei singoli task.

1. **I test si eseguono con `venv/bin/pytest`.** Non `pytest` nudo: il venv del
   checkout principale è l'unico che ha `ortools` e `pytest-django`.
2. **La suite parte da 173 test verdi.** Nessun task può lasciarla rossa, e
   nessun task può *ridurre* il numero di test.
3. **Terminologia in italiano nei commenti e nei docstring; identificatori in
   inglese.** È la convenzione del repository (`CLAUDE.md`).
4. **`domain/analysis/` non deve mai importare `ortools`.** La diagnostica
   dev'essere usabile senza il solver. Il verso opposto è lecito:
   `domain/solver/` importa liberamente da `domain/analysis/`.
5. **Nessun builder crea una variabile che il vocabolario già offre**, e
   nessun builder calcola un residuo a mano invece di chiamare
   `residual_cap` / `residual_floor`. Entrambe sono ragioni sufficienti per
   respingere un task in review.
6. **Ogni traduzione si deriva leggendo il checker corrispondente**, in
   `domain/analysis/checkers/`, non ricordandone la semantica. I tre difetti
   dello spike sono tutti nati da un piano che ragionava a memoria.
7. **`AddMaxEquality` e `AddMinEquality` con una lista vuota sono invalidi.**
   La mezza giornata pomeridiana **è vuota** su griglie dove
   `morning_end_slot == slots_per_day` (accade già in due test esistenti). Ogni
   costruzione che aggrega su un intervallo deve passare da `_max_or_zero`.
8. **Le chiavi del registro non cambiano mai.** Sono il contratto fra
   `domain/analysis` e `domain/solver` («una riga di dato, due facce»).
9. **Commit per task**, messaggio in italiano, con il trailer
   `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Ondata 1 — Fondamenta

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

### Task 2: Il vocabolario, seconda metà — materia, posizione, sede

**Files:**
- Modify: `domain/solver/vocabulary.py`
- Test: `tests/test_solver_vocabulary.py` (aggiunge test)

**Interfaces:**
- Consumes: `Vocabulary` del Task 1.
- Produces:
  - `vocab.subject_bucket(keys, subject_id, kind, bucket, signature=None) -> BoolVar`
    — `keys` è un `frozenset` di chiavi di occupazione (l'espansione
    dell'unità, già precalcolata in `ctx.subject_rows`); `kind` è `"day"` o
    `"half"`; `bucket` è il giorno, oppure `giorno * 2 + meta`.
  - `vocab.bucket_of(kind, day, slot) -> int`
  - `vocab.pos(aid) -> IntVar` — `giorno * slots_per_day + fascia di inizio`
  - `vocab.site_occupied(key, day, slot, site_id, signature=None) -> BoolVar`

⚠ La spec §2.2 elenca `site_at` come «la sede occupata in quella cella». La
forma concreta è `site_occupied`, **un booleano per sede** invece di un intero.
I due consumatori (`MAX_SITE_CHANGES`, `structural:site_transition`)
confrontano sedi fra loro e non hanno mai bisogno del valore numerico; un
booleano si compone direttamente con gli altri letterali senza canalizzazioni
aggiuntive.

⚠ **Un'attività si attribuisce al secchio della sua fascia di partenza**, non
di tutte le fasce che occupa. È scritto in testa a
`domain/analysis/checkers/subject_constraints.py` e vale per tutti e tredici i
vincoli di materia. Un'attività di 2 fasce che inizia alle 3 con
`morning_end_slot = 4` sta **in mattinata**, per intero.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# in coda a tests/test_solver_vocabulary.py

def test_subject_bucket_usa_la_fascia_di_partenza():
    """Un'attivita' di due fasce che inizia alle 3, con la linea di meta'
    giornata a 4, appartiene alla MATTINA per intero: i vincoli di materia
    attribuiscono l'attivita' al secchio della fascia di partenza."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=2)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 3)] == 1)
    keys = frozenset({env["klass"].pk})
    mattina = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 0)
    pomeriggio = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(mattina) == 1
    assert solver.Value(pomeriggio) == 0


def test_subject_bucket_ignora_le_altre_materie_e_le_altre_unita():
    env = mini_school()
    from domain.models import SchoolClass, Subject
    altra_materia = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    altra_classe = SchoolClass.objects.create(
        name="1B", study_plan=env["plan"], year=1)
    a = make_activity(altra_materia, teachers=[env["teacher"]], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[altra_classe])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 0)] == 1)
    giorno = vocab.subject_bucket(
        frozenset({env["klass"].pk}), env["subject"].pk, "day", 0)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(giorno) == 0


def test_pos_canalizza_giorno_e_fascia():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 2, 3)] == 1)
    p = vocab.pos(a.id)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(p) == 2 * env["grid"].slots_per_day + 3


def test_site_occupied_distingue_le_sedi():
    env = mini_school()
    from domain.models import Site
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=centrale)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    key = env["klass"].pk
    qui = vocab.site_occupied(key, 0, 0, centrale.pk)
    altrove = vocab.site_occupied(key, 0, 0, succursale.pk)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(qui) == 1
    assert solver.Value(altrove) == 0
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v -k "subject_bucket or pos or site_occupied"`
Expected: FAIL con `AttributeError: 'Vocabulary' object has no attribute 'subject_bucket'`

- [ ] **Step 3: Aggiungere le primitive a `domain/solver/vocabulary.py`**

```python
    # --- materia in un secchio -------------------------------------------

    def bucket_of(self, kind, day, slot):
        """Il secchio di una collocazione. ⚠ Si usa la fascia di **partenza**
        dell'attivita', non tutte quelle che occupa: e' la regola dichiarata
        in testa a domain/analysis/checkers/subject_constraints.py."""
        return day if kind == "day" else day * 2 + self.half_of(slot)

    def subject_bucket(self, keys, subject_id, kind, bucket, signature=None):
        """La materia `subject_id` occorre in quel secchio, sull'unita' `keys`.
        `keys` e' l'espansione dell'unita' della riga di vincolo, gia'
        precalcolata in ctx.subject_rows."""
        keys = frozenset(keys)
        def make():
            var = self.model.NewBoolVar(
                f"subj_{subject_id}_{kind}_{bucket}_{signature}_{id(keys)}")
            active = (None if signature is None
                      else self.ctx.states[signature].activities)
            lits = []
            for aid, act in self.ctx.activities.items():
                if act.subject_id != subject_id:
                    continue
                if not (self.ctx.tokens[aid] & keys):
                    continue
                if active is not None and aid not in active:
                    continue
                for (day, slot) in self.ctx.cells[aid]:
                    if self.bucket_of(kind, day, slot) == bucket:
                        lits.append(self.ctx.x[(aid, day, slot)])
            return self._max_or_zero(var, lits)
        return self._memo("subj", (signature, keys, subject_id, kind, bucket), make)

    def subject_activities(self, keys, subject_id, signature=None):
        """Gli id delle attivita' di quella materia su quell'unita'. Serve ai
        builder per la regola dell'implicazione di ADR-018 (`any_free`) e per
        sapere staticamente se una materia e' assente."""
        keys = frozenset(keys)
        active = (None if signature is None
                  else self.ctx.states[signature].activities)
        return sorted(
            aid for aid, act in self.ctx.activities.items()
            if act.subject_id == subject_id
            and self.ctx.tokens[aid] & keys
            and (active is None or aid in active))

    # --- posizione e sede -------------------------------------------------

    def pos(self, aid):
        """giorno * slots_per_day + fascia di inizio, canalizzato da x."""
        def make():
            cells = sorted(self.ctx.cells[aid])
            width = self.ctx.grid.slots_per_day
            if not cells:
                # dominio vuoto: build_model ha gia' reso il modello
                # infattibile in modo esplicito, qui basta non rompere
                return self.model.NewIntVar(0, 0, f"pos_{aid}")
            values = [day * width + slot for (day, slot) in cells]
            var = self.model.NewIntVar(min(values), max(values), f"pos_{aid}")
            self.model.Add(var == sum(
                (day * width + slot) * self.ctx.x[(aid, day, slot)]
                for (day, slot) in cells))
            return var
        return self._memo("pos", aid, make)

    def site_occupied(self, key, day, slot, site_id, signature=None):
        """Un'attivita' di sede `site_id` occupa quella cella."""
        def make():
            var = self.model.NewBoolVar(
                f"site_{site_id}_{key}_{day}_{slot}_{signature}")
            active = (None if signature is None
                      else self.ctx.states[signature].activities)
            lits = [lit for aid, lit in self.ctx.by_cell.get((key, day, slot), ())
                    if self.ctx.activities[aid].site_id == site_id
                    and (active is None or aid in active)]
            return self._max_or_zero(var, lits)
        return self._memo("site", (signature, key, day, slot, site_id), make)
```

⚠ Nel nome della variabile di `subject_bucket` compare `id(keys)`: serve solo
a rendere il nome leggibile e univoco nel dump del modello, **non** fa parte
della chiave di memoizzazione, che è il `frozenset` stesso.

- [ ] **Step 4: Eseguire i test nuovi e la suite intera**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v`
Expected: PASS (8 test)

Run: `venv/bin/pytest -q`
Expected: **181 passed**

- [ ] **Step 5: Commit**

```bash
git add domain/solver/vocabulary.py tests/test_solver_vocabulary.py
git commit -m "$(cat <<'EOF'
feat(solver): il vocabolario, seconda meta'

subject_bucket (con la regola della fascia di partenza), subject_activities,
pos e site_occupied. Nessun builder le usa ancora: le ondate 3-6 le
consumano.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: ADR-018 — l'helper del residuo e l'oracolo differenziale

**Files:**
- Create: `domain/solver/residual.py`
- Modify: `tests/test_solver_oracle.py` (l'oracolo diventa differenziale)
- Test: `tests/test_solver_residual.py`

**Interfaces:**
- Consumes: `SolverContext.free` (l'insieme degli id muovibili).
- Produces:
  - `split(ctx, terms) -> (list[(peso, letterale)], int)` — `terms` è un
    iterabile di `(peso, id_attività, letterale)`
  - `residual_cap(ctx, terms, cap) -> (list[(peso, letterale)], int)`
  - `residual_floor(ctx, terms, floor) -> (list[(peso, letterale)], int)`
  - `any_free(ctx, activity_ids) -> bool`
  - in `tests/test_solver_oracle.py`: `violazioni(schedule) -> set` (era una
    lista) e `nuove(schedule, prima) -> set`

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_residual.py
"""ADR-018: i letterali delle attivita' congelate sono costanti note a build
time, quindi ogni espressione lineare si spezza in «parte costante + parte
libera». Sui tetti il residuo puo' essere negativo e va clampato a zero; sui
minimi garantiti no."""
import pytest

from domain.solver.residual import any_free, residual_cap, residual_floor, split

pytestmark = pytest.mark.django_db


class _Ctx:
    def __init__(self, free):
        self.free = set(free)


def test_split_separa_libere_e_congelate():
    ctx = _Ctx({1, 2})
    termini = [(60, 1, "x1"), (60, 2, "x2"), (60, 3, "x3"), (30, 4, "x4")]
    liberi, congelate = split(ctx, termini)
    assert liberi == [(60, "x1"), (60, "x2")]
    assert congelate == 90


def test_residual_cap_sottrae_il_consumo_delle_congelate():
    ctx = _Ctx({1})
    liberi, tetto = residual_cap(ctx, [(60, 1, "x1"), (60, 2, "x2")], 180)
    assert liberi == [(60, "x1")]
    assert tetto == 120


def test_residual_cap_clampa_a_zero_invece_di_andare_negativo():
    """Il caso di ADR-018: le congelate hanno gia' sforato. Il vincolo resta
    postabile e le libere non possono aggiungere nulla, ma il modello non
    diventa infattibile per colpa di una violazione preesistente."""
    ctx = _Ctx({1})
    liberi, tetto = residual_cap(ctx, [(60, 1, "x1"), (300, 2, "x2")], 180)
    assert liberi == [(60, "x1")]
    assert tetto == 0


def test_residual_floor_non_clampa():
    """Su un minimo garantito il residuo negativo e' corretto e va lasciato
    passare: significa che le congelate gia' bastano e il vincolo e' vacuo.
    Clamparlo a zero non cambierebbe nulla qui, ma clamparlo *dal basso* a un
    valore positivo imporrebbe alle libere un dovere gia' assolto."""
    ctx = _Ctx({1})
    liberi, soglia = residual_floor(ctx, [(1, 1, "x1"), (1, 2, "x2"), (1, 3, "x3")], 2)
    assert liberi == [(1, "x1")]
    assert soglia == 0
    _, soglia_vacua = residual_floor(ctx, [(1, 2, "x2"), (1, 3, "x3")], 1)
    assert soglia_vacua == -1


def test_any_free_e_la_regola_dell_implicazione():
    ctx = _Ctx({7})
    assert any_free(ctx, [7, 8]) is True
    assert any_free(ctx, [8, 9]) is False
    assert any_free(ctx, []) is False
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_residual.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.solver.residual'`

- [ ] **Step 3: Scrivere `domain/solver/residual.py`**

```python
"""ADR-018 — l'input sporco non blocca il solver.

Un'attivita' congelata ha ctx.cells[aid] di cardinalita' uno e riceve comunque
AddExactlyOne: il suo letterale vale 1, ed e' noto al momento della
costruzione. Quindi ogni espressione lineare del modello si spezza
**esattamente** in «parte costante + parte libera», e da li' discendono due
casi soli.

Sui **tetti**: `costante + libere <= tetto` equivale a
`libere <= tetto - costante`, e quel residuo puo' essere negativo — e' il caso
in cui le congelate sono gia' in violazione. ADR-018 impone di clamparlo a
zero invece di lasciare il modello infattibile per colpa del passato.

Sui **minimi garantiti**: `costante + libere >= soglia` equivale a
`libere >= soglia - costante`, che non e' mai infattibile per colpa del
passato — se le congelate gia' bastano, il requisito e' vacuo. Nessun clamp."""


def split(ctx, terms):
    """terms: iterabile di (peso, id attivita', letterale).
    → (termini liberi come (peso, letterale), consumo delle congelate)."""
    free, frozen = [], 0
    for weight, aid, lit in terms:
        if aid in ctx.free:
            free.append((weight, lit))
        else:
            frozen += weight
    return free, frozen


def residual_cap(ctx, terms, cap):
    """Per un vincolo «<= cap». Il tetto residuo e' clampato a zero."""
    free, frozen = split(ctx, terms)
    return free, max(0, cap - frozen)


def residual_floor(ctx, terms, floor):
    """Per un vincolo «>= floor». Nessun clamp: una soglia residua <= 0
    significa che le congelate gia' bastano, ed e' corretto che il vincolo
    risulti vacuo."""
    free, frozen = split(ctx, terms)
    return free, floor - frozen


def any_free(ctx, activity_ids):
    """La regola dell'implicazione: un vincolo i cui letterali vengono tutti da
    attivita' congelate non si posta — e' un fatto, non una decisione."""
    return any(aid in ctx.free for aid in activity_ids)
```

- [ ] **Step 4: Rendere differenziale l'oracolo dei test**

In `tests/test_solver_oracle.py`, sostituire `violazioni` con:

```python
def violazioni(schedule, codici=CODICI):
    """L'insieme delle chiavi dei finding HARD nelle famiglie modellate.
    Un insieme, non una lista: il criterio di riuscita e' il **contenimento**
    (ADR-018), non l'uguaglianza."""
    return {f.key for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici}


def nuove(schedule, prima, codici=CODICI):
    """I finding HARD comparsi **dopo** il solve. Il solver puo' anche
    riparare una violazione preesistente spostando un'attivita' libera: quello
    e' un successo, non una discrepanza, ed e' per questo che il criterio e'
    il contenimento e non l'uguaglianza."""
    return violazioni(schedule, codici) - prima
```

Poi sostituire ovunque `assert violazioni(...) == []` con
`assert violazioni(...) == set()`. Sono sei occorrenze, tutte su istanze che
partono pulite, quindi il valore atteso non cambia — cambia solo il tipo.

⚠ Non aggiungere ancora un test che parte da un input sporco: nessun builder
usa `residual_cap` finché non arriva l'ondata 3. Il primo test end-to-end di
ADR-018 nasce nel Task 6.

- [ ] **Step 5: Eseguire tutto**

Run: `venv/bin/pytest tests/test_solver_residual.py -v`
Expected: PASS (5 test)

Run: `venv/bin/pytest -q`
Expected: **186 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/residual.py tests/test_solver_residual.py tests/test_solver_oracle.py
git commit -m "$(cat <<'EOF'
feat(solver): ADR-018, il residuo e l'oracolo differenziale

residual_cap clampa a zero il tetto residuo, residual_floor non clampa
perche' su un minimo garantito il passato non puo' rendere infattibile
nulla. L'oracolo dei test passa da lista a insieme: il criterio e' il
contenimento dei finding, non l'uguaglianza, perche' il solver puo' anche
riparare una violazione preesistente.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Lo spostamento dei due builder nei file del proprio pattern

**Files:**
- Create: `domain/solver/builders/time_presence.py` (accoglie `MaxGapBuilder`)
- Create: `domain/solver/builders/subject_buckets.py` (accoglie `SameDayBuilder`)
- Delete: `domain/solver/builders/time_constraints.py`
- Delete: `domain/solver/builders/subject_constraints.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/test_solver_max_gap.py`, `tests/test_solver_same_day.py` (solo
  gli import, se importano il modulo invece del registro)

**Interfaces:**
- Consumes: niente di nuovo.
- Produces: `MaxGapBuilder` importabile da
  `domain.solver.builders.time_presence`; `SameDayBuilder` da
  `domain.solver.builders.subject_buckets`. **Le chiavi del registro non
  cambiano** (`T.MAX_GAP_HOURS`, `T.SAME_DAY_INCOMPATIBLE`).

- [ ] **Step 1: Verificare da dove i test importano**

Run: `grep -rn "time_constraints\|subject_constraints" tests/ domain/solver/`

Se i test raggiungono i builder solo attraverso `all_builders()` o `solve()`,
non c'è nulla da modificare nei test: è lo scenario atteso.

- [ ] **Step 2: Spostare i file**

```bash
git mv domain/solver/builders/time_constraints.py domain/solver/builders/time_presence.py
git mv domain/solver/builders/subject_constraints.py domain/solver/builders/subject_buckets.py
```

- [ ] **Step 3: Aggiornare i docstring di modulo**

In `time_presence.py`, premettere al docstring esistente:

```python
"""Presenza e buchi: i vincoli che ragionano sulla **prima e sull'ultima**
fascia occupata, e non sul semplice conteggio. Entrambi passano da
`vocab.covered`, con `span` diverso — mezza giornata per il D.T.B., giornata
intera per MAX_PRESENCE.
"""
```

In `subject_buckets.py`:

```python
"""I vincoli di materia che si esprimono come cardinalita' su un **secchio**
(giornata o mezza giornata). L'attivita' si attribuisce al secchio della sua
fascia di **partenza**.
"""
```

- [ ] **Step 4: Verificare che `builders/__init__.py` importi i moduli nuovi**

`all_builders()` fa `from domain.solver import builders` per forzare la
registrazione. Controllare `domain/solver/builders/__init__.py` e sostituire i
due nomi vecchi con quelli nuovi.

- [ ] **Step 5: Eseguire la suite**

Run: `venv/bin/pytest -q`
Expected: **186 passed** — identico al Task 3. Uno spostamento che cambia il
numero di test verdi non è uno spostamento.

- [ ] **Step 6: Commit**

```bash
git add -A domain/solver/builders tests/
git commit -m "$(cat <<'EOF'
refactor(solver): i builder nel file del proprio pattern

time_constraints.py -> time_presence.py, subject_constraints.py ->
subject_buckets.py. Le chiavi del registro non cambiano. Prepara le ondate
3-6, dove quei file accolgono altri undici builder.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 2 — Il banco di prova

### Task 5: Il generatore a testimone

**Files:**
- Create: `tests/solver_harness.py`
- Create: `tests/test_solver_witness.py`

**Interfaces:**
- Consumes: `domain.solver.model.solve/apply`, `domain.analysis.conformity`,
  `domain.analysis.state.activity_tokens`, `domain.solver.registry.BUILDERS`.
- Produces:
  - `build_witness(seed, **opts) -> Witness` con
    `Witness(schedule, env, placement, tokens, weeks_of)`
  - `deriver(key, codes)` — decoratore che registra un derivatore in `DERIVERS`
  - `DERIVERS: dict[key, Deriver]`, `Deriver(fn, codes)`
  - `run_family(key, seed)` — il test completo di una famiglia
- **Ogni task successivo aggiunge il proprio derivatore a questo modulo.** Il
  test di copertura (`test_ogni_builder_ha_un_derivatore`) fallisce se un
  builder viene registrato senza.

**Perché questo task viene prima dei builder.** L'ondata 2 non ha quasi nulla
da testare nel momento in cui la si scrive, il che è scomodo. È voluto: chi
scrive il test dopo aver scritto il builder tende a scrivere il test che il
builder passa. Vedi §7 della spec.

- [ ] **Step 1: Scrivere `tests/solver_harness.py`**

```python
"""Il generatore a testimone.

Per ogni famiglia: si genera **prima** un orario valido a caso, **poi** le
righe di vincolo che quell'orario soddisfa, e solo allora si chiede al solver
di trovarne uno da zero.

L'orario di partenza e' un testimone: prova che una soluzione esiste. Quindi
un INFEASIBLE e' un fallimento duro, e una soluzione qualsiasi dev'essere
pulita. Le due direzioni sono coperte da un test solo — e soprattutto un
builder vacuo (che postasse `1 == 0`, o che non postasse nulla) non puo'
passare: nel primo caso non trova il testimone, nel secondo lascia passare un
orario che il checker boccia.

Le maschere di settimana sono randomizzate insieme al resto, cosi' ogni
famiglia esercita piu' di una firma fin dal primo test. E' deliberato: il
difetto del D.T.B. del 2026-08-24 e' passato proprio perche' ogni banco di
prova aveva un'unica firma."""

import datetime as dt
import random
from collections import defaultdict
from dataclasses import dataclass, field

from domain import weeks
from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.analysis.state import activity_tokens
from domain.models import (
    Activity, Discipline, Period, Placement, Schedule, SchoolClass, SchoolYear,
    StudyPlan, Subject, Teacher, TimeGrid, Service,
)
from domain.solver.model import apply, solve

N_WEEKS = 3
# le maschere disponibili: garantiscono almeno due firme di settimana distinte
MASKS = [weeks.full_mask(N_WEEKS), weeks.single_week(0),
         weeks.single_week(1) | weeks.single_week(2)]


@dataclass
class Witness:
    schedule: object
    env: dict
    placement: dict            # id attivita' → (giorno, fascia)
    tokens: dict               # id attivita' → frozenset di chiavi
    weeks_of: dict             # id attivita' → tuple di settimane attive
    activities: list
    rng: random.Random
    signatures: list = field(default_factory=list)

    def resource_days(self, key, week):
        """giorno → fasce occupate, per una chiave, in una settimana."""
        out = defaultdict(set)
        for aid, (day, slot) in self.placement.items():
            if key not in self.tokens[aid] or week not in self.weeks_of[aid]:
                continue
            for s in range(slot, slot + self.act(aid).duration_slots):
                out[day].add(s)
        return {d: sorted(s) for d, s in sorted(out.items())}

    def act(self, aid):
        return next(a for a in self.activities if a.id == aid)


def _school(rng):
    grid = TimeGrid.objects.create(
        days_per_cycle=rng.choice([3, 4, 5]),
        slots_per_day=rng.choice([4, 6]),
        slot_minutes=60,
        morning_end_slot=rng.choice([2, 3, 4]),
    )
    grid.morning_end_slot = min(grid.morning_end_slot, grid.slots_per_day)
    grid.save()
    monday = dt.date(2026, 9, 14)
    year = SchoolYear.objects.create(
        start_date=monday, end_date=monday + dt.timedelta(days=7 * N_WEEKS - 1),
        first_week_monday=monday)
    period = Period.objects.create(
        school_year=year, name="P1",
        start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subjects = [
        Subject.objects.create(code=c, name=c.title(), discipline=disc)
        for c in ("ITA", "MAT", "STO")
    ]
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    classes = [SchoolClass.objects.create(name=n, study_plan=plan, year=1)
               for n in ("1A", "1B")]
    teachers = [Teacher.objects.create(name=f"Doc {i}", last_name=f"D{i}",
                                       first_name=str(i))
                for i in range(4)]
    return {"grid": grid, "year": year, "period": period, "schedule": schedule,
            "discipline": disc, "subjects": subjects, "plan": plan,
            "classes": classes, "teachers": teachers}


def _make_activities(rng, env):
    """Per ogni classe, attivita' fino al 50% della capienza della griglia:
    il margine serve a rendere il piazzamento casuale quasi sempre possibile
    al primo tentativo."""
    grid = env["grid"]
    capienza = grid.days_per_cycle * grid.slots_per_day
    out = []
    for klass in env["classes"]:
        for _ in range(max(2, capienza // 2)):
            subject = rng.choice(env["subjects"])
            act = Activity.objects.create(
                subject=subject, duration_slots=1, duration_minutes=60,
                week_mask=rng.choice(MASKS))
            act.teachers.add(rng.choice(env["teachers"]))
            act.classes.add(klass)
            service, _ = Service.objects.get_or_create(
                study_plan=klass.study_plan, subject=subject,
                defaults={"class_minutes": 0})
            service.class_minutes += 60
            service.save()
            out.append(act)
    return out


def _try_place(rng, activities, tokens, weeks_of, grid):
    """Un orario valido a caso: nessuna chiave occupata due volte nella stessa
    cella **nella stessa settimana**. Due attivita' di settimane disgiunte
    possono condividere la cella — e' esattamente la proprieta' che il modello
    deve rispettare, quindi il testimone deve poterla esibire."""
    busy, out = set(), {}
    ordine = list(activities)
    rng.shuffle(ordine)
    for act in ordine:
        celle = [(d, s) for d in range(grid.days_per_cycle)
                 for s in range(grid.slots_per_day - act.duration_slots + 1)]
        rng.shuffle(celle)
        for (day, slot) in celle:
            fasce = range(slot, slot + act.duration_slots)
            occupa = [(w, k, day, t) for w in weeks_of[act.id]
                      for k in tokens[act.id] for t in fasce]
            if any(cell in busy for cell in occupa):
                continue
            busy.update(occupa)
            out[act.id] = (day, slot)
            break
        else:
            return None
    return out


def build_witness(seed, tentativi=20):
    rng = random.Random(seed)
    env = _school(rng)
    activities = _make_activities(rng, env)
    tokens = {a.id: activity_tokens(a)[0] for a in activities}
    weeks_of = {a.id: tuple(w for w in range(N_WEEKS)
                            if weeks.week_in_mask(a.week_mask, w))
                for a in activities}
    for _ in range(tentativi):
        placement = _try_place(rng, activities, tokens, weeks_of, env["grid"])
        if placement is not None:
            break
    else:
        raise AssertionError(
            f"nessun orario valido dopo {tentativi} tentativi (seed {seed}): "
            "la fixture e' troppo densa, non il solver troppo debole")
    for aid, (day, slot) in placement.items():
        Placement.objects.create(schedule=env["schedule"], activity_id=aid,
                                 day=day, start_slot=slot)
    w = Witness(schedule=env["schedule"], env=env, placement=placement,
                tokens=tokens, weeks_of=weeks_of, activities=activities, rng=rng)
    w.signatures = week_signatures(env["schedule"])
    return w


# --- il registro dei derivatori -----------------------------------------

@dataclass(frozen=True)
class Deriver:
    fn: object
    codes: frozenset


DERIVERS = {}


def deriver(key, codes):
    """Registra il derivatore di una famiglia. `codes` sono le causali che
    quella famiglia puo' emettere: sono cio' che il test controlla."""
    def wrap(fn):
        DERIVERS[key] = Deriver(fn, frozenset(codes))
        return fn
    return wrap


def _hard(schedule, codes):
    return {f.key for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codes}


def run_family(key, seed):
    """Il test completo di una famiglia. Fallisce in tre modi distinti, e
    ciascuno dice una cosa diversa."""
    assert key in DERIVERS, f"nessun derivatore per {key}"
    d = DERIVERS[key]
    w = build_witness(seed)
    d.fn(w)

    # 1. il testimone dev'essere valido: se non lo e', e' il derivatore a
    #    essere sbagliato, non il builder
    prima = _hard(w.schedule, d.codes)
    assert prima == set(), (
        f"il testimone stesso viola {key} (seed {seed}): {sorted(prima)}")

    # 2. c'era un testimone, quindi INFEASIBLE e' un fallimento duro:
    #    il builder e' piu' stretto di quanto la spec consenta
    Placement.objects.filter(schedule=w.schedule).delete()
    soluzione = solve(w.schedule, time_limit=60)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), (
        f"{key} INFEASIBLE con un testimone disponibile (seed {seed}): "
        f"{soluzione.stats}")

    # 3. e qualunque soluzione restituisca dev'essere pulita
    apply(soluzione, w.schedule)
    dopo = _hard(w.schedule, d.codes)
    assert dopo == set(), (
        f"{key} accetta un piazzamento che il checker boccia (seed {seed}): "
        f"{sorted(dopo)}")
    return w
```

- [ ] **Step 2: Scrivere i cinque derivatori delle famiglie già tradotte**

In coda a `tests/solver_harness.py`:

```python
from domain.models import ResourceTimeConstraint, ResourceUnavailability, SubjectConstraint

RT = ResourceTimeConstraint.Type
ST = SubjectConstraint.Type


@deriver("structural:grid", {"slot_out_of_grid", "break_straddled", "holiday"})
def _derive_grid(w):
    """Nessuna riga da creare: il testimone rispetta la griglia per
    costruzione, perche' _try_place genera solo celle ammissibili. Il
    derivatore esiste comunque, perche' il test di copertura non ammette
    famiglie senza banco di prova."""


@deriver("structural:occupation", {"resource_occupied", "resource_occupied_locked",
                                   "resource_peak"})
def _derive_occupation(w):
    """Idem: _try_place non produce doppie occupazioni. Il valore del test sta
    tutto nel punto 2 di run_family — il solver deve **ritrovare** un orario
    senza conflitti, e con piu' firme di settimana in gioco."""


@deriver("structural:unavailability", {"unavailability"})
def _derive_unavailability(w):
    """Dichiara indisponibili alcune celle che il testimone **non** usa, su un
    docente scelto a caso. Ricorrenti (senza data), cosi' non alterano le
    firme."""
    docente = w.rng.choice(w.env["teachers"])
    grid = w.env["grid"]
    usate = {(day, s) for aid, (day, slot) in w.placement.items()
             if docente.pk in w.tokens[aid]
             for s in range(slot, slot + w.act(aid).duration_slots)}
    libere = [(d, s) for d in range(grid.days_per_cycle)
              for s in range(grid.slots_per_day) if (d, s) not in usate]
    for (day, slot) in w.rng.sample(libere, min(3, len(libere))):
        ResourceUnavailability.objects.create(
            resource=docente, day=day, slot=slot, level="hard")


@deriver(RT.MAX_GAP_HOURS, {"max_gap"})
def _derive_max_gap(w):
    """Il budget settimanale osservato nel testimone, per la firma peggiore.
    Con l'uguaglianza il vincolo e' soddisfatto e stretto: se il builder
    contasse i buchi anche solo di un minuto in piu', sforerebbe."""
    grid = w.env["grid"]
    klass = w.rng.choice(w.env["classes"])
    peggiore = 0
    for rep, _ in w.signatures:
        totale = 0
        for _day, fasce in w.resource_days(klass.pk, rep).items():
            for meta in ([f for f in fasce if f < grid.morning_end_slot],
                         [f for f in fasce if f >= grid.morning_end_slot]):
                if len(meta) >= 2:
                    totale += (meta[-1] - meta[0] + 1 - len(meta)) * grid.slot_minutes
        peggiore = max(peggiore, totale)
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MAX_GAP_HOURS,
        params={"max_gap_minutes": peggiore})


@deriver(ST.SAME_DAY_INCOMPATIBLE, {"subject_same_day"})
def _derive_same_day(w):
    """Sceglie una coppia (classe, materia) che nel testimone non compare mai
    due volte nello stesso giorno. Se non ce n'e' nessuna il derivatore non
    crea righe: meglio un test vacuo per un seed che un testimone invalido."""
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            per_giorno = defaultdict(int)
            for aid, (day, _slot) in w.placement.items():
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk:
                    per_giorno[day] += 1
            if per_giorno and max(per_giorno.values()) == 1:
                SubjectConstraint.objects.create(
                    subject_a=subject, subject_b=subject, school_class=klass,
                    type=ST.SAME_DAY_INCOMPATIBLE)
                return
```

- [ ] **Step 3: Scrivere il test di copertura e i test per seed**

```python
# tests/test_solver_witness.py
"""Il banco di prova. Il test di copertura e' quello che tiene: registrare un
builder senza il suo derivatore diventa impossibile, invece di dipendere dalla
diligenza di chi lo scrive."""
import pytest

from domain.solver import builders  # noqa: F401 — forza la registrazione
from domain.solver.registry import BUILDERS
from tests.solver_harness import DERIVERS, build_witness, run_family

pytestmark = pytest.mark.django_db

SEEDS = [1, 2, 3, 4, 5]


def test_ogni_builder_ha_un_derivatore():
    mancanti = sorted(str(k) for k in BUILDERS if k not in DERIVERS)
    assert mancanti == [], (
        "questi builder non hanno un banco di prova: " + ", ".join(mancanti))


def test_il_testimone_ha_piu_di_una_firma_di_settimana():
    """Se questa proprieta' si perdesse, ogni test del banco tornerebbe cieco
    sulla dimensione «settimane» — che e' esattamente il modo in cui il
    difetto del D.T.B. e' passato inosservato."""
    w = build_witness(seed=1)
    assert len(w.signatures) >= 2


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("key", sorted(DERIVERS, key=str))
def test_famiglia(key, seed):
    run_family(key, seed)
```

- [ ] **Step 4: Eseguire**

Run: `venv/bin/pytest tests/test_solver_witness.py -q`
Expected: PASS. 2 test più 5 famiglie × 5 seed = **27 test**.

Se una famiglia fallisce al punto 1 («il testimone stesso viola»), il difetto
è nel derivatore. Se fallisce al punto 2 o 3, è nel builder. La distinzione è
nel messaggio di assert apposta.

Run: `venv/bin/pytest -q`
Expected: **213 passed** (186 + 27)

- [ ] **Step 5: Commit**

```bash
git add tests/solver_harness.py tests/test_solver_witness.py
git commit -m "$(cat <<'EOF'
test(solver): il generatore a testimone

Genera prima un orario valido, poi i vincoli che esso soddisfa, poi chiede
al solver di ritrovarne uno. Il testimone rende impossibile a un builder
vacuo di passare: senza, un builder che postasse 1 == 0 supererebbe per
sempre qualunque test che si accontenti di "se c'e' una soluzione allora
e' pulita".

Le maschere di settimana sono una dimensione del generatore, non un test
dedicato: e' da li' che e' passato il difetto del D.T.B.

Il test di copertura enumera BUILDERS e boccia ogni chiave senza
derivatore.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 3 — I sette vincoli orari

### Task 6: Lo scheletro per firma, e i due tetti di conteggio

**Files:**
- Create: `domain/solver/builders/base.py`
- Create: `domain/solver/builders/time_counting.py`
- Modify: `domain/solver/builders/time_presence.py` (`MaxGapBuilder` sullo scheletro)
- Modify: `domain/solver/residual.py` (aggiunge `frozen_occupies`)
- Modify: `tests/solver_harness.py` (due derivatori)
- Test: `tests/test_solver_time_counting.py`

**Interfaces:**
- Consumes: `ctx.vocab` (Task 1), `residual_cap` (Task 3), `run_family` (Task 5).
- Produces:
  - `ResourceBuilder` — classe base con il ciclo sulle firme e la
    deduplicazione, con l'hook `post(self, ctx, model, row, rep)`
  - `frozen_occupies(ctx, key, day, slots, rep=None) -> bool` in `residual.py`
  - `MaxHoursBuilder` (`T.MAX_HOURS`), `MaxHalfDaysBuilder` (`T.MAX_HALF_DAYS`)

**⚠ La scoperta che questo task incorpora.** `residual_cap` funziona sulle
somme di letterali di attività, ma `MAX_HALF_DAYS` somma **variabili derivate**
(`half_active`), dove il contributo delle congelate non è separabile come
costante. La regola si estende così: **una variabile derivata che una attività
congelata forza a 1 è essa stessa una costante**, e va nel consumo invece che
nella somma; se nessuna congelata la tocca, dipende solo da letterali liberi e
resta un termine. `frozen_occupies` è il predicato che distingue i due casi.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_time_counting.py
"""MAX_HOURS e MAX_HALF_DAYS: puro conteggio. E il primo test end-to-end di
ADR-018 su input sporco — una congelata che ha gia' sforato il tetto non deve
rendere il modello infattibile."""
import pytest

from domain.models import Activity, Placement, ResourceTimeConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_max_hours_sul_banco(seed):
    run_family(T.MAX_HOURS, seed)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_max_half_days_sul_banco(seed):
    run_family(T.MAX_HALF_DAYS, seed)


def test_max_hours_morde():
    """Tre attivita' della stessa classe, tetto giornaliero a due ore: il
    solver deve distribuirle su piu' di un giorno."""
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_HOURS, params={"day_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    per_giorno = {}
    for (day, _slot) in soluzione.placements.values():
        per_giorno[day] = per_giorno.get(day, 0) + 1
    assert max(per_giorno.values()) <= 2


def test_adr018_una_congelata_gia_in_violazione_non_blocca_il_solver():
    """Il caso di ADR-018, end-to-end. Due attivita' congelate sono gia'
    piazzate lo stesso giorno e sforano da sole il tetto di un'ora. Una terza,
    libera, deve comunque poter essere piazzata: il tetto residuo e' zero per
    quel giorno, non negativo, quindi il modello resta fattibile e la libera
    va altrove."""
    env = mini_school()
    congelate = [
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for _ in range(2)
    ]
    for i, act in enumerate(congelate):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=i)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_HOURS, params={"day_minutes": 60})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id][0] != 0   # non il giorno gia' pieno
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_time_counting.py -q`
Expected: FAIL — `test_max_hours_morde` fallisce sull'assert finale (nessun
builder vincola ancora) e i test `_sul_banco` con `nessun derivatore per ...`.

- [ ] **Step 3: Estrarre lo scheletro in `domain/solver/builders/base.py`**

```python
"""Lo scheletro condiviso dai builder che vincolano **una risorsa** riga per
riga: il ciclo sulle firme di settimana e la deduplicazione.

Le firme non sono un dettaglio da ricordarsi: un vincolo che aggrega su una
risorsa lungo la settimana **deve** essere postato per firma, con i letterali
filtrati alle sole attivita' attive in quella firma. Trattare tutto come
co-attivo puo' vincolare *di meno*, non di piu' — e' il difetto trovato sul
D.T.B. il 2026-08-24. Qui la regola e' nella classe base, cosi' nessun builder
deve ricordarsene."""

from domain.solver.registry import Builder


class ResourceBuilder(Builder):
    TYPE = None

    def build(self, ctx, model):
        for row in ctx.time_rows:
            if row.type != self.TYPE:
                continue
            posted = set()
            for rep, _ in ctx.signatures:
                active = ctx.states[rep].activities
                touching = frozenset(
                    aid
                    for day in range(ctx.grid.days_per_cycle)
                    for slot in range(ctx.grid.slots_per_day)
                    for aid, _ in ctx.by_cell.get((row.resource_id, day, slot), ())
                    if aid in active
                )
                if not any(aid in ctx.free for aid in touching):
                    continue   # un fatto, non una decisione
                if touching in posted:
                    continue   # firma diversa, stesse attivita' attive
                posted.add(touching)
                self.post(ctx, model, row, rep)

    def post(self, ctx, model, row, rep):
        raise NotImplementedError
```

- [ ] **Step 4: Riscrivere `MaxGapBuilder` sullo scheletro**

In `time_presence.py`, `MaxGapBuilder` eredita da `ResourceBuilder`, dichiara
`TYPE = T.MAX_GAP_HOURS`, e conserva **solo** il corpo, come `post`:

```python
@register(T.MAX_GAP_HOURS)
class MaxGapBuilder(ResourceBuilder):
    TYPE = T.MAX_GAP_HOURS

    def post(self, ctx, model, row, rep):
        grid, v = ctx.grid, ctx.vocab
        terms = []
        for day in range(grid.days_per_cycle):
            for half in v.halves():
                if not len(half):
                    continue
                cov = v.covered(row.resource_id, day, half, signature=rep)
                for s in half:
                    terms.append(cov[s] - v.occupied(row.resource_id, day, s,
                                                     signature=rep))
        if terms:
            model.Add(grid.slot_minutes * sum(terms)
                      <= row.params["max_gap_minutes"])
```

Il docstring del modulo, con l'avvertenza sulle firme, **resta**: spiega
*perché* lo scheletro fa quello che fa.

- [ ] **Step 5: Aggiungere `frozen_occupies` a `domain/solver/residual.py`**

```python
def frozen_occupies(ctx, key, day, slots, rep=None):
    """Un'attivita' **congelata** occupa quella chiave in una di quelle fasce?

    Serve alle cardinalita' su **variabili derivate** (day_active,
    half_active), dove il contributo delle congelate non e' separabile come
    termine: se una congelata forza la variabile a 1, quella variabile e' una
    costante e va nel consumo; se nessuna la tocca, dipende solo da letterali
    liberi e resta un termine della somma."""
    active = None if rep is None else ctx.states[rep].activities
    for slot in slots:
        for aid, _lit in ctx.by_cell.get((key, day, slot), ()):
            if aid not in ctx.free and (active is None or aid in active):
                return True
    return False
```

- [ ] **Step 6: Scrivere `domain/solver/builders/time_counting.py`**

```python
"""I vincoli orari che sono puro **conteggio**: quante fasce in un giorno,
quante mezze giornate nella settimana. Nessuno di questi guarda *quali* fasce:
la prima e l'ultima sono affare di time_presence.py."""

from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import register
from domain.solver.residual import frozen_occupies, residual_cap

T = ResourceTimeConstraint.Type


@register(T.MAX_HOURS)
class MaxHoursBuilder(ResourceBuilder):
    """MaxHoursChecker conta `len(slots)` per giornata, mattina e pomeriggio,
    dove `slots` sono le fasce **distinte** occupate.

    ⚠ Qui si somma un termine per ogni voce di by_cell, cioe' per ogni
    (attivita', fascia). Coincide con il conteggio delle fasce distinte finche'
    due attivita' non occupano la stessa cella sulla stessa chiave — che
    OccupationBuilder vieta. Nel caso residuo (capacita' simultanea > 1) la
    somma e' **piu' grande** del conteggio del checker, quindi il vincolo e'
    piu' stretto: direzione sicura."""
    TYPE = T.MAX_HOURS

    def post(self, ctx, model, row, rep):
        sm, v = ctx.grid.slot_minutes, ctx.vocab
        active = ctx.states[rep].activities
        for day in range(ctx.grid.days_per_cycle):
            spans = (("day_minutes", range(ctx.grid.slots_per_day)),
                     ("morning_minutes", v.halves()[0]),
                     ("afternoon_minutes", v.halves()[1]))
            for param, span in spans:
                cap = row.params.get(param)
                if cap is None or not len(span):
                    continue
                terms = [(sm, aid, lit)
                         for slot in span
                         for aid, lit in ctx.by_cell.get(
                             (row.resource_id, day, slot), ())
                         if aid in active]
                liberi, residuo = residual_cap(ctx, terms, cap)
                if liberi:
                    model.Add(sum(w * lit for w, lit in liberi) <= residuo)


@register(T.MAX_HALF_DAYS)
class MaxHalfDaysBuilder(ResourceBuilder):
    """MaxHalfDaysChecker somma bool(mattina) + bool(pomeriggio) sui giorni con
    attivita'. Un giorno vuoto contribuisce 0 in entrambi i sensi, quindi
    sommare half_active su **tutte** le mezze giornate e' esatto.

    ⚠ half_active e' una variabile derivata: il residuo di ADR-018 si applica
    per **forzatura**, non per sottrazione di termini. Vedi frozen_occupies."""
    TYPE = T.MAX_HALF_DAYS

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        cap = row.params.get("max_half_days")
        if cap is not None:
            terms, consumo = [], 0
            for day in range(ctx.grid.days_per_cycle):
                for half, span in enumerate(v.halves()):
                    if not len(span):
                        continue
                    if frozen_occupies(ctx, key, day, span, rep):
                        consumo += 1
                    else:
                        terms.append(v.half_active(key, day, half, signature=rep))
            if terms:
                model.Add(sum(terms) <= max(0, cap - consumo))
        if row.params.get("only_half_day_per_day"):
            mattina, pomeriggio = v.halves()
            if len(mattina) and len(pomeriggio):
                for day in range(ctx.grid.days_per_cycle):
                    model.AddAtMostOne([
                        v.half_active(key, day, 0, signature=rep),
                        v.half_active(key, day, 1, signature=rep)])
```

- [ ] **Step 7: Registrare il modulo e aggiungere i due derivatori**

In `domain/solver/builders/__init__.py`, importare `time_counting`.

In coda a `tests/solver_harness.py`:

```python
@deriver(RT.MAX_HOURS, {"max_hours_day", "max_hours_morning", "max_hours_afternoon"})
def _derive_max_hours(w):
    """I tetti osservati nel testimone, per la firma peggiore. Con
    l'uguaglianza il vincolo e' soddisfatto e stretto."""
    grid = w.env["grid"]
    klass = w.rng.choice(w.env["classes"])
    picchi = {"day_minutes": 0, "morning_minutes": 0, "afternoon_minutes": 0}
    for rep, _ in w.signatures:
        for _day, fasce in w.resource_days(klass.pk, rep).items():
            mattina = [f for f in fasce if f < grid.morning_end_slot]
            sera = [f for f in fasce if f >= grid.morning_end_slot]
            picchi["day_minutes"] = max(picchi["day_minutes"], len(fasce))
            picchi["morning_minutes"] = max(picchi["morning_minutes"], len(mattina))
            picchi["afternoon_minutes"] = max(picchi["afternoon_minutes"], len(sera))
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MAX_HOURS,
        params={k: v * grid.slot_minutes for k, v in picchi.items()})


@deriver(RT.MAX_HALF_DAYS, {"max_half_days", "only_half_day"})
def _derive_max_half_days(w):
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    peggiore = 0
    for rep, _ in w.signatures:
        lavorate = 0
        for _day, fasce in w.resource_days(docente.pk, rep).items():
            lavorate += any(f < grid.morning_end_slot for f in fasce)
            lavorate += any(f >= grid.morning_end_slot for f in fasce)
        peggiore = max(peggiore, lavorate)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_HALF_DAYS,
        params={"max_half_days": peggiore})
```

⚠ `only_half_day_per_day` **non** si deriva: il testimone quasi mai lo
soddisfa, e forzarlo renderebbe il derivatore un generatore di istanze
degeneri. È coperto dal test mirato `test_max_hours_morde`, e la sua causale
resta nell'insieme `codes` perché il banco deve accorgersi se il builder la
facesse scattare per sbaglio.

- [ ] **Step 8: Eseguire**

Run: `venv/bin/pytest tests/test_solver_time_counting.py -q`
Expected: PASS (12 test)

Run: `venv/bin/pytest -q`
Expected: **225 passed** (213 + 12)

- [ ] **Step 9: Commit**

```bash
git add domain/solver/builders/base.py domain/solver/builders/time_counting.py domain/solver/builders/time_presence.py domain/solver/builders/__init__.py domain/solver/residual.py tests/solver_harness.py tests/test_solver_time_counting.py
git commit -m "$(cat <<'EOF'
feat(solver): MAX_HOURS e MAX_HALF_DAYS, e lo scheletro per firma

ResourceBuilder porta nella classe base il ciclo sulle firme di settimana e
la deduplicazione, cosi' nessun builder deve ricordarsi che un vincolo
aggregato va postato per firma: e' il difetto del D.T.B., reso strutturale
invece che ricordato.

frozen_occupies estende ADR-018 alle cardinalita' su variabili derivate,
dove il contributo delle congelate non e' un termine sottraibile ma una
forzatura.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: I tre minimi garantiti

**Files:**
- Modify: `domain/solver/builders/time_counting.py`
- Modify: `tests/solver_harness.py` (tre derivatori)
- Test: `tests/test_solver_time_minimums.py`

**Interfaces:**
- Consumes: `ResourceBuilder`, `ctx.vocab`.
- Produces: `MinDistributionBuilder` (`T.MIN_DISTRIBUTION`),
  `ArrivalDepartureBuilder` (`T.ARRIVAL_DEPARTURE`), `FreeGuaranteedBuilder`
  (`T.FREE_GUARANTEED`).

**⚠ Nessuno dei tre usa `residual_cap`, ed è corretto.** Sono minimi
garantiti: le attività congelate contribuiscono *a favore* dentro le variabili
derivate, e una soglia già soddisfatta dal passato rende il vincolo vacuo, mai
infattibile (spec §3.1). Chiamare `residual_cap` qui sarebbe un difetto.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_time_minimums.py
"""I tre vincoli orari che chiedono un minimo invece di imporre un tetto. Il
test che conta e' quello su FREE_GUARANTEED: il checker conta le mezze
giornate libere **solo sui giorni che hanno attivita'**, e un builder che le
contasse su tutti i giorni accetterebbe orari che il checker boccia."""
import pytest

from domain.models import ResourceTimeConstraint
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family
from tests.test_solver_oracle import violazioni

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tipo", [T.MIN_DISTRIBUTION, T.ARRIVAL_DEPARTURE,
                                  T.FREE_GUARANTEED])
def test_minimi_sul_banco(tipo, seed):
    run_family(tipo, seed)


def test_min_distribution_morde():
    """Quattro ore, distribuite su almeno tre giorni."""
    env = mini_school()
    for _ in range(4):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert len({day for (day, _s) in soluzione.placements.values()}) >= 3


def test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti():
    """La trappola, dritta. Griglia 5x6 con meta' giornata a 4; una sola
    attivita', quindi quattro giorni su cinque sono **completamente** vuoti.

    Il checker conta le mezze giornate libere solo sui giorni con attivita':
    con una sola attivita' ce n'e' esattamente **una** (l'altra meta' del
    giorno in cui si lavora). Un builder che sommasse su tutti i giorni ne
    conterebbe nove, e dichiarerebbe soddisfatto un vincolo che il checker
    boccia. Chiediamo tre mezze giornate libere: dev'essere INFEASIBLE."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_free_guaranteed_soddisfacibile_resta_soddisfacibile():
    """Il complemento del test sopra: con una sola mezza giornata richiesta la
    stessa istanza dev'essere fattibile, e pulita per il checker."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"free_guaranteed"}) == set()
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_time_minimums.py -q`
Expected: FAIL — `nessun derivatore` sui test parametrizzati, e i due test
mirati falliscono perché nessun vincolo è ancora postato.

- [ ] **Step 3: Aggiungere i tre builder a `time_counting.py`**

```python
@register(T.MIN_DISTRIBUTION)
class MinDistributionBuilder(ResourceBuilder):
    """MinDistributionChecker conta i giorni in cui la risorsa lavora almeno
    `min_minutes_per_day`, e ne vuole almeno `min_days`."""
    TYPE = T.MIN_DISTRIBUTION

    def post(self, ctx, model, row, rep):
        sm, v, key = ctx.grid.slot_minutes, ctx.vocab, row.resource_id
        soglia = row.params["min_minutes_per_day"]
        qualificati = []
        for day in range(ctx.grid.days_per_cycle):
            occ = [v.occupied(key, day, s, signature=rep)
                   for s in range(ctx.grid.slots_per_day)]
            q = model.NewBoolVar(f"qualifies_{key}_{rep}_{day}")
            model.Add(sm * sum(occ) >= soglia).OnlyEnforceIf(q)
            model.Add(sm * sum(occ) < soglia).OnlyEnforceIf(q.Not())
            qualificati.append(q)
        model.Add(sum(qualificati) >= row.params["min_days"])


@register(T.ARRIVAL_DEPARTURE)
class ArrivalDepartureBuilder(ResourceBuilder):
    """⚠ Non servono variabili di prima/ultima fascia.

    «La prima fascia e' >= not_before» equivale a «nessuna occupazione prima di
    not_before»; «l'ultima e' < not_after» a «nessuna occupazione da not_after
    in poi». E il giorno vuoto risulta conforme gratis, che e' esattamente cio'
    che ArrivalDepartureChecker fa con il suo `compliant += 1`."""
    TYPE = T.ARRIVAL_DEPARTURE

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        proibite = [s for s in range(ctx.grid.slots_per_day)
                    if (not_before is not None and s < not_before)
                    or (not_after is not None and s >= not_after)]
        conformi = []
        for day in range(ctx.grid.days_per_cycle):
            viola = model.NewBoolVar(f"ad_viola_{key}_{rep}_{day}")
            lits = [v.occupied(key, day, s, signature=rep) for s in proibite]
            if lits:
                model.AddMaxEquality(viola, lits)
            else:
                model.Add(viola == 0)
            conforme = model.NewBoolVar(f"ad_ok_{key}_{rep}_{day}")
            model.Add(conforme + viola == 1)
            conformi.append(conforme)
        model.Add(sum(conformi) >= row.params["days"])


@register(T.FREE_GUARANTEED)
class FreeGuaranteedBuilder(ResourceBuilder):
    """⚠ La trappola di questa famiglia, e la ragione per cui il termine
    `giorno_attivo` compare nella congiunzione.

    FreeGuaranteedChecker itera `for day, slots in days.items()`, e `days`
    contiene **solo i giorni con attivita'**: un giorno completamente vuoto
    contribuisce **zero** mezze giornate libere, non due. Sommare
    `not half_active` su tutte le mezze giornate ne conterebbe di piu',
    renderebbe `>= soglia` piu' facile, e farebbe accettare orari che il
    checker boccia — la direzione sbagliata."""
    TYPE = T.FREE_GUARANTEED

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        giorni_liberi, mezze_libere = [], []
        for day in range(ctx.grid.days_per_cycle):
            attivo = v.day_active(key, day, signature=rep)
            libero = model.NewBoolVar(f"freeday_{key}_{rep}_{day}")
            model.Add(libero + attivo == 1)
            giorni_liberi.append(libero)
            for half, span in enumerate(v.halves()):
                if not len(span):
                    continue
                meta = v.half_active(key, day, half, signature=rep)
                libera = model.NewBoolVar(f"freehalf_{key}_{rep}_{day}_{half}")
                # libera  <->  giorno attivo AND mezza giornata scarica
                model.AddBoolAnd([attivo, meta.Not()]).OnlyEnforceIf(libera)
                model.AddBoolOr([attivo.Not(), meta]).OnlyEnforceIf(libera.Not())
                mezze_libere.append(libera)
        minimo_giorni = row.params.get("free_days", 0)
        if minimo_giorni:
            model.Add(sum(giorni_liberi) >= minimo_giorni)
        minimo_mezze = row.params.get("free_half_days", 0)
        if minimo_mezze and mezze_libere:
            model.Add(sum(mezze_libere) >= minimo_mezze)
```

- [ ] **Step 4: Aggiungere i tre derivatori a `tests/solver_harness.py`**

```python
@deriver(RT.MIN_DISTRIBUTION, {"min_distribution"})
def _derive_min_distribution(w):
    """Chiede i giorni effettivamente lavorati nella firma **peggiore**: e' il
    massimo che il testimone garantisce in tutte le settimane."""
    klass = w.rng.choice(w.env["classes"])
    peggiore = min(len(w.resource_days(klass.pk, rep)) for rep, _ in w.signatures)
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": w.env["grid"].slot_minutes,
                "min_days": peggiore})


@deriver(RT.ARRIVAL_DEPARTURE, {"arrival_departure"})
def _derive_arrival_departure(w):
    """La finestra osservata: la prima fascia usata e l'ultima piu' uno.
    Chiede che **tutti** i giorni siano conformi, e nel testimone lo sono."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    prima, ultima = grid.slots_per_day, 0
    for rep, _ in w.signatures:
        for _day, fasce in w.resource_days(docente.pk, rep).items():
            prima, ultima = min(prima, fasce[0]), max(ultima, fasce[-1])
    if prima > ultima:
        prima, ultima = 0, grid.slots_per_day - 1
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.ARRIVAL_DEPARTURE,
        params={"not_before_slot": prima, "not_after_slot": ultima + 1,
                "days": grid.days_per_cycle})


@deriver(RT.FREE_GUARANTEED, {"free_guaranteed"})
def _derive_free_guaranteed(w):
    """I giorni e le mezze giornate libere osservati nella firma peggiore.
    ⚠ Le mezze giornate si contano **solo sui giorni con attivita'**, come fa
    il checker: derivare altrimenti produrrebbe un testimone che il checker
    stesso boccia, e run_family lo direbbe al punto 1."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    min_giorni, min_mezze = grid.days_per_cycle, grid.days_per_cycle * 2
    for rep, _ in w.signatures:
        giorni = w.resource_days(docente.pk, rep)
        liberi = grid.days_per_cycle - len(giorni)
        mezze = 0
        for _day, fasce in giorni.items():
            mezze += not any(f < grid.morning_end_slot for f in fasce)
            mezze += not any(f >= grid.morning_end_slot for f in fasce)
        min_giorni, min_mezze = min(min_giorni, liberi), min(min_mezze, mezze)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.FREE_GUARANTEED,
        params={"free_days": min_giorni, "free_half_days": min_mezze})
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_time_minimums.py -q`
Expected: PASS (18 test)

Run: `venv/bin/pytest -q`
Expected: **243 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/time_counting.py tests/solver_harness.py tests/test_solver_time_minimums.py
git commit -m "$(cat <<'EOF'
feat(solver): MIN_DISTRIBUTION, ARRIVAL_DEPARTURE, FREE_GUARANTEED

I tre minimi garantiti, che per costruzione non hanno bisogno del residuo
di ADR-018: una soglia gia' soddisfatta dalle congelate e' vacua, mai
infattibile.

FREE_GUARANTEED porta la trappola: il checker conta le mezze giornate
libere solo sui giorni con attivita', quindi un giorno vuoto ne vale zero,
non due. Sommare su tutti i giorni accetterebbe orari illegali. Il test
mirato lo dimostra chiedendo tre mezze giornate su un'istanza che ne ha
una sola.

ARRIVAL_DEPARTURE si semplifica: nessuna variabile di prima/ultima fascia,
solo l'assenza di occupazioni nella zona proibita.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: MAX_PRESENCE

**Files:**
- Modify: `domain/solver/builders/time_presence.py`
- Modify: `tests/solver_harness.py` (un derivatore)
- Test: `tests/test_solver_max_presence.py`

**Interfaces:**
- Consumes: `ResourceBuilder`, `vocab.covered`, `vocab.day_active`,
  `frozen_occupies`.
- Produces: `MaxPresenceBuilder` (`T.MAX_PRESENCE`).

**⚠ `span` è la giornata intera.** `_presence_minutes` calcola
`(slots[-1] - slots[0] + 1) * sm` sui slot di **tutto il giorno** e non passa
mai da `_halves`. Usare la mezza giornata qui produrrebbe un vincolo **più
largo** del checker.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_max_presence.py
"""La presenza non e' il lavoro: include i buchi. E si misura sulla giornata
intera, non per mezza giornata — a differenza del D.T.B."""
import pytest

from domain.models import Activity, Placement, ResourceTimeConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_max_presence_sul_banco(seed):
    run_family(T.MAX_PRESENCE, seed)


def test_la_presenza_include_i_buchi_e_attraversa_il_pranzo():
    """Due attivita' della stessa classe, presenza massima due ore. Su una
    griglia 5x6 con meta' giornata a 4, il solver non puo' metterle alle fasce
    0 e 5 (presenza sei ore) ne' alle fasce 3 e 4 (presenza due ore ma **a
    cavallo del pranzo**, che per la presenza non conta come separazione).

    Se il builder usasse la mezza giornata come span, 3 e 4 risulterebbero due
    presenze da un'ora ciascuna e passerebbero: e' il modo esatto in cui questo
    vincolo si confonde con il D.T.B."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    per_giorno = {}
    for (day, slot) in soluzione.placements.values():
        per_giorno.setdefault(day, []).append(slot)
    for _day, fasce in per_giorno.items():
        assert (max(fasce) - min(fasce) + 1) * 60 <= 120


def test_adr018_presenza_gia_sforata_dalle_congelate_non_blocca():
    """Due congelate alle fasce 0 e 5 dello stesso giorno: presenza sei ore,
    tetto due. Il vincolo per quel giorno non si posta (ADR-018), e
    un'attivita' libera resta piazzabile altrove."""
    env = mini_school()
    for i, slot in enumerate((0, 5)):
        act = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]],
                            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=slot)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert libera.id in soluzione.placements
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_max_presence.py -q`
Expected: FAIL

- [ ] **Step 3: Scrivere il builder in `time_presence.py`**

```python
@register(T.MAX_PRESENCE)
class MaxPresenceBuilder(ResourceBuilder):
    """Presenza != lavoro: la presenza include i buchi, e si misura
    `ultima - prima + 1` **sulla giornata intera**.

    ⚠ Lo `span` e' la giornata, non la mezza giornata. MaxPresenceChecker usa
    `_presence_minutes`, che non passa da `_halves` — a differenza del D.T.B.,
    che i buchi non li conta mai a cavallo del pranzo. Sono due vincoli che si
    somigliano e non sono la stessa cosa."""
    TYPE = T.MAX_PRESENCE

    def post(self, ctx, model, row, rep):
        v, key, sm = ctx.vocab, row.resource_id, ctx.grid.slot_minutes
        giornata = range(ctx.grid.slots_per_day)
        cap = row.params.get("max_minutes")
        if cap is not None:
            for day in range(ctx.grid.days_per_cycle):
                congelate = [s for s in giornata
                             if frozen_occupies(ctx, key, day, [s], rep)]
                if congelate and (congelate[-1] - congelate[0] + 1) * sm > cap:
                    # ADR-018: le sole congelate hanno gia' sforato. Le libere
                    # non possono ridurre una presenza, quindi il vincolo e'
                    # perso comunque: postarlo renderebbe il modello
                    # infattibile per colpa del passato.
                    continue
                cov = v.covered(key, day, giornata, signature=rep)
                model.Add(sm * sum(cov[s] for s in giornata) <= cap)
        max_days = row.params.get("days")
        if max_days is not None:
            terms, consumo = [], 0
            for day in range(ctx.grid.days_per_cycle):
                if frozen_occupies(ctx, key, day, giornata, rep):
                    consumo += 1
                else:
                    terms.append(v.day_active(key, day, signature=rep))
            if terms:
                model.Add(sum(terms) <= max(0, max_days - consumo))
```

più gli import `from domain.solver.builders.base import ResourceBuilder` e
`from domain.solver.residual import frozen_occupies`.

- [ ] **Step 4: Aggiungere il derivatore**

```python
@deriver(RT.MAX_PRESENCE, {"max_presence", "max_presence_days"})
def _derive_max_presence(w):
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    picco, giorni = 0, 0
    for rep, _ in w.signatures:
        per_firma = w.resource_days(docente.pk, rep)
        giorni = max(giorni, len(per_firma))
        for _day, fasce in per_firma.items():
            picco = max(picco, (fasce[-1] - fasce[0] + 1) * grid.slot_minutes)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_PRESENCE,
        params={"max_minutes": picco, "days": giorni})
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_max_presence.py -q`
Expected: PASS (7 test)

Run: `venv/bin/pytest -q`
Expected: **250 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/time_presence.py tests/solver_harness.py tests/test_solver_max_presence.py
git commit -m "$(cat <<'EOF'
feat(solver): MAX_PRESENCE, sullo span della giornata intera

La presenza include i buchi e si misura su tutto il giorno, non per mezza
giornata: e' la differenza con il D.T.B., ed e' il motivo per cui covered()
prende uno span. Il test mirato la esibisce con due attivita' alle fasce 3
e 4, che a cavallo del pranzo passerebbero se lo span fosse sbagliato.

ADR-018 qui non e' una sottrazione: se le sole congelate hanno gia' sforato
la presenza di un giorno, il vincolo di quel giorno non si posta, perche'
nessuna attivita' libera puo' ridurre una presenza.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Le sedi — `MAX_SITE_CHANGES` e `structural:site_transition`

**Files:**
- Create: `domain/solver/builders/time_sites.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/solver_harness.py` (due derivatori, e le sedi nella scuola)
- Test: `tests/test_solver_sites.py`

**Interfaces:**
- Consumes: `vocab.site_occupied`, `vocab.occupied`, `ResourceBuilder`.
- Produces: `MaxSiteChangesBuilder` (`T.MAX_SITE_CHANGES`),
  `SiteTransitionBuilder` (`"structural:site_transition"`).

**Il conservativo numero due** (spec §4.3): `SiteTransitionChecker` vincola le
coppie **consecutive** nella sequenza delle occupazioni con sede nota; il
builder vincola **tutte** le coppie. Per una coppia lontana
`s₂ − s₁ − 1 ≥ needed` è già vero e il vincolo è vacuo, quindi le righe
effettive si aggiungono solo sulle coppie vicine, che includono tutte le
consecutive. Più stretto, mai più largo.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_sites.py
"""Sedi: cambi di sede contati nella giornata, e fasce libere richieste fra
due lezioni su sedi diverse."""
import pytest

from domain.models import InstituteSettings, ResourceTimeConstraint, Site
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("chiave", [T.MAX_SITE_CHANGES, "structural:site_transition"])
def test_sedi_sul_banco(chiave, seed):
    run_family(chiave, seed)


def test_site_transition_impone_le_fasce_libere():
    """Due attivita' della stessa classe su sedi diverse, con due fasce di
    trasferimento richieste: non possono stare a meno di tre fasce di
    distanza nello stesso giorno."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 2})
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=centrale)
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=succursale)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    (ga, sa), (gb, sb) = soluzione.placements[a.id], soluzione.placements[b.id]
    if ga == gb:
        assert abs(sa - sb) - 1 >= 2


def test_max_site_changes_limita_i_cambi():
    """Tre attivita' alternate fra due sedi, un solo cambio al giorno
    consentito: il solver deve raggrupparle per sede."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    for sede in (centrale, succursale, centrale):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=sede)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_sites.py -q`
Expected: FAIL

- [ ] **Step 3: Scrivere `domain/solver/builders/time_sites.py`**

```python
"""Le sedi. Due vincoli che condividono la stessa costruzione: una coppia di
fasce della stessa giornata, occupate da attivita' di **sedi diverse**, con
tutto vuoto in mezzo.

⚠ Entrambi i checker ragionano su coppie **consecutive** nella sequenza delle
occupazioni con sede nota. Qui si vincolano tutte le coppie: e' piu' stretto,
mai piu' largo (spec §4.3), perche' per le coppie lontane il vincolo e' vacuo
e le coppie vicine includono tutte le consecutive."""

from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import Builder, register

T = ResourceTimeConstraint.Type


def _sedi(ctx):
    return sorted({a.site_id for a in ctx.activities.values()
                   if a.site_id is not None})


def _coppie_di_sede(ctx, model, key, day, s, t, sa, sb, rep):
    """I letterali di «fascia s sulla sede sa, fascia t sulla sede sb, e tutto
    vuoto in mezzo». Lista vuota se la costruzione non ha senso."""
    v = ctx.vocab
    lits = [v.site_occupied(key, day, s, sa, signature=rep),
            v.site_occupied(key, day, t, sb, signature=rep)]
    lits += [v.occupied(key, day, m, signature=rep).Not()
             for m in range(s + 1, t)]
    return lits


@register(T.MAX_SITE_CHANGES)
class MaxSiteChangesBuilder(ResourceBuilder):
    TYPE = T.MAX_SITE_CHANGES

    def post(self, ctx, model, row, rep):
        key, sedi = row.resource_id, _sedi(ctx)
        if len(sedi) < 2:
            return
        per_giorno = row.params.get("per_day")
        per_settimana = row.params.get("per_week")
        tutti = []
        for day in range(ctx.grid.days_per_cycle):
            cambi = []
            for s in range(ctx.grid.slots_per_day):
                for t in range(s + 1, ctx.grid.slots_per_day):
                    for sa in sedi:
                        for sb in sedi:
                            if sa == sb:
                                continue
                            lits = _coppie_di_sede(ctx, model, key, day,
                                                   s, t, sa, sb, rep)
                            c = model.NewBoolVar(
                                f"chg_{key}_{rep}_{day}_{s}_{t}_{sa}_{sb}")
                            # la congiunzione implica il cambio; c puo' essere
                            # 1 in piu' solo a danno del solver, e i vincoli
                            # sotto sono tutti «<=»
                            model.AddBoolOr([c] + [l.Not() for l in lits])
                            cambi.append(c)
            if per_giorno is not None and cambi:
                model.Add(sum(cambi) <= per_giorno)
            tutti += cambi
        if per_settimana is not None and tutti:
            model.Add(sum(tutti) <= per_settimana)


@register("structural:site_transition")
class SiteTransitionBuilder(Builder):
    """Fra due lezioni su sedi diverse servono `site_transition_slots` fasce
    libere. Vale su **ogni** chiave di occupazione, non su una riga di
    vincolo: e' strutturale, come l'occupazione."""

    def build(self, ctx, model):
        sedi = _sedi(ctx)
        if len(sedi) < 2:
            return
        needed = ctx.states[ctx.signatures[0][0]].settings.site_transition_slots
        if not needed:
            return
        chiavi = sorted({k for (k, _d, _s) in ctx.by_cell}, key=str)
        posted = set()
        for rep, _ in ctx.signatures:
            active = ctx.states[rep].activities
            for key in chiavi:
                for day in range(ctx.grid.days_per_cycle):
                    for s in range(ctx.grid.slots_per_day):
                        for t in range(s + 1, ctx.grid.slots_per_day):
                            if t - s - 1 >= needed:
                                continue   # gia' abbastanza lontane: vacuo
                            tocca = {
                                aid
                                for m in (s, t)
                                for aid, _ in ctx.by_cell.get((key, day, m), ())
                                if aid in active
                            }
                            if not any(aid in ctx.free for aid in tocca):
                                continue
                            for sa in sedi:
                                for sb in sedi:
                                    if sa == sb:
                                        continue
                                    firma = (key, day, s, t, sa, sb,
                                             frozenset(tocca))
                                    if firma in posted:
                                        continue
                                    posted.add(firma)
                                    model.AddBoolOr([
                                        ctx.vocab.site_occupied(
                                            key, day, s, sa, signature=rep).Not(),
                                        ctx.vocab.site_occupied(
                                            key, day, t, sb, signature=rep).Not(),
                                    ])
```

- [ ] **Step 4: Dare sedi alla scuola del banco, e i due derivatori**

In `tests/solver_harness.py`, dentro `_school`, aggiungere:

```python
    from domain.models import Site
    sites = [Site.objects.create(name=n) for n in ("Centrale", "Succursale")]
```
e includerlo nel dizionario restituito (`"sites": sites`).

In `_make_activities`, dopo `act.classes.add(klass)`:

```python
            if rng.random() < 0.5:
                act.site = rng.choice(env["sites"])
                act.save()
```

I derivatori:

```python
@deriver(RT.MAX_SITE_CHANGES, {"max_site_changes"})
def _derive_max_site_changes(w):
    """I cambi di sede osservati: massimo per giornata e totale settimanale,
    presi sulla firma peggiore."""
    docente = w.rng.choice(w.env["teachers"])
    per_giorno, per_settimana = 0, 0
    for rep, _ in w.signatures:
        settimana = 0
        for day, fasce in w.resource_days(docente.pk, rep).items():
            sequenza = []
            for f in fasce:
                for aid, (d, slot) in w.placement.items():
                    if (d == day and slot == f and docente.pk in w.tokens[aid]
                            and w.act(aid).site_id is not None
                            and rep in w.weeks_of[aid]):
                        sequenza.append(w.act(aid).site_id)
            cambi = sum(x != y for x, y in zip(sequenza, sequenza[1:]))
            per_giorno = max(per_giorno, cambi)
            settimana += cambi
        per_settimana = max(per_settimana, settimana)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_SITE_CHANGES,
        params={"per_day": per_giorno, "per_week": per_settimana})


@deriver("structural:site_transition", {"site_transition"})
def _derive_site_transition(w):
    """Il numero di fasce libere che il testimone garantisce gia' fra due
    lezioni su sedi diverse. Derivato sulle **coppie vicine**, cioe' contro la
    regola piu' stretta del builder e non contro quella del checker: e' cosi'
    che «direzione dimostrata» diventa eseguibile (spec §5.2)."""
    from domain.models import InstituteSettings
    minimo = None
    for rep, _ in w.signatures:
        for aid, (day, slot) in w.placement.items():
            if w.act(aid).site_id is None or rep not in w.weeks_of[aid]:
                continue
            for altro, (day2, slot2) in w.placement.items():
                if altro == aid or day2 != day or rep not in w.weeks_of[altro]:
                    continue
                if w.act(altro).site_id in (None, w.act(aid).site_id):
                    continue
                if not (w.tokens[aid] & w.tokens[altro]):
                    continue
                distanza = abs(slot2 - slot) - 1
                minimo = distanza if minimo is None else min(minimo, distanza)
    settings, _ = InstituteSettings.objects.get_or_create(pk=1)
    settings.site_transition_slots = 0 if minimo is None else max(0, minimo)
    settings.save()
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_sites.py -q`
Expected: PASS (12 test)

Run: `venv/bin/pytest -q`
Expected: **262 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/time_sites.py domain/solver/builders/__init__.py tests/solver_harness.py tests/test_solver_sites.py
git commit -m "$(cat <<'EOF'
feat(solver): MAX_SITE_CHANGES e structural:site_transition

Il secondo conservativo dichiarato: i checker guardano le coppie
consecutive nella sequenza delle occupazioni con sede nota, il builder
guarda tutte le coppie. Per le coppie lontane il vincolo e' vacuo, quindi
la direzione e' verso il piu' stretto.

Il derivatore deriva contro la regola del builder, non contro quella del
checker: cosi' la direzione e' verificata a ogni esecuzione invece che
argomentata una volta in spec.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 4 — I cinque vincoli di materia meccanici

### Task 10: Lo scheletro di materia, `SAME_HALF_DAY` e `TWO_DAYS`

**Files:**
- Modify: `domain/solver/builders/base.py` (aggiunge `SubjectBuilder`)
- Modify: `domain/solver/vocabulary.py` (aggiunge `subject_literals`)
- Modify: `domain/solver/builders/subject_buckets.py`
- Modify: `tests/solver_harness.py` (due derivatori)
- Test: `tests/test_solver_subject_buckets.py`

**Interfaces:**
- Produces:
  - `SubjectBuilder` — scheletro con `post(self, ctx, model, row, keys, rep)`
  - `vocab.subject_literals(keys, subject_id, kind, bucket, signature=None) -> list[(aid, lit)]`
  - `SameHalfDayBuilder` (`T.SAME_HALF_DAY_INCOMPATIBLE`),
    `TwoDaysBuilder` (`T.TWO_DAYS_INCOMPATIBLE`)
  - `SameDayBuilder` riscritto su `SubjectBuilder`

**⚠ Questo task *rimuove* una semplificazione dichiarata.** Il docstring
attuale di `subject_buckets.py` dice che il builder «non distingue le firme di
settimana e tratta tutte le attività come co-attive», con la giustificazione
che è conservativo. Per `SAME_DAY` lo è davvero. Ma `SubjectBuilder` itera per
firma con deduplicazione, quindi la semplificazione non serve più a nessuno:
va **tolta dal docstring** invece di lasciarla lì a suggerire che sia una
strategia da imitare. Sulla firma unica del Fermi il costo è zero, perché la
deduplicazione collassa tutto in un vincolo solo.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_subject_buckets.py
"""I vincoli di materia che sono cardinalita' su un secchio."""
import pytest

from domain.models import SubjectConstraint, Subject
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tipo", [T.SAME_HALF_DAY_INCOMPATIBLE,
                                  T.TWO_DAYS_INCOMPATIBLE])
def test_secchi_sul_banco(tipo, seed):
    run_family(tipo, seed)


def test_same_half_day_separa_le_meta_giornate():
    """Due ore della stessa materia, incompatibili nella mezza giornata: su una
    griglia con meta' giornata a 4 devono finire in mezze giornate diverse, o
    in giorni diversi."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.SAME_HALF_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    meta = {(day, 0 if slot < 4 else 1)
            for (day, slot) in soluzione.placements.values()}
    assert len(meta) == 2


def test_two_days_vieta_i_giorni_consecutivi():
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.TWO_DAYS_INCOMPATIBLE)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    giorno_a = soluzione.placements[a.id][0]
    giorno_b = soluzione.placements[b.id][0]
    assert giorno_b != giorno_a + 1
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_subject_buckets.py -q`
Expected: FAIL

- [ ] **Step 3: Aggiungere `SubjectBuilder` a `base.py`**

```python
class SubjectBuilder(Builder):
    """Lo scheletro dei vincoli sull'asse Relazione: una riga per volta, una
    firma di settimana per volta, con deduplicazione sull'insieme delle
    attivita' coinvolte.

    Iterare per firma qui non e' strettamente necessario per i vincoli che
    vietano (piu' letterali = piu' stretto), ma lo e' per quelli d'ordine, dove
    fondere le settimane puo' spostare la *prima* occorrenza e rendere il
    vincolo piu' largo. Una regola sola per tutta la famiglia costa meno che
    ricordarsi caso per caso quale delle due si applica — ed e' esattamente il
    tipo di distinzione che in questo progetto e' gia' stato sbagliato."""

    TYPE = None

    def build(self, ctx, model):
        for row, keys in ctx.subject_rows:
            if row.type != self.TYPE:
                continue
            posted = set()
            for rep, _ in ctx.signatures:
                v = ctx.vocab
                coinvolte = frozenset(
                    v.subject_activities(keys, row.subject_a_id, signature=rep)
                    + v.subject_activities(keys, row.subject_b_id, signature=rep))
                if not any(aid in ctx.free for aid in coinvolte):
                    continue
                if coinvolte in posted:
                    continue
                posted.add(coinvolte)
                self.post(ctx, model, row, keys, rep)

    def post(self, ctx, model, row, keys, rep):
        raise NotImplementedError
```

- [ ] **Step 4: Estrarre `subject_literals` nel vocabolario**

In `vocabulary.py`, aggiungere il metodo e farlo usare da `subject_bucket`:

```python
    def subject_literals(self, keys, subject_id, kind, bucket, signature=None):
        """[(id attivita', letterale)] delle collocazioni di quella materia in
        quel secchio, sull'unita' `keys`."""
        keys = frozenset(keys)
        active = (None if signature is None
                  else self.ctx.states[signature].activities)
        out = []
        for aid, act in self.ctx.activities.items():
            if act.subject_id != subject_id:
                continue
            if not (self.ctx.tokens[aid] & keys):
                continue
            if active is not None and aid not in active:
                continue
            for (day, slot) in sorted(self.ctx.cells[aid]):
                if self.bucket_of(kind, day, slot) == bucket:
                    out.append((aid, self.ctx.x[(aid, day, slot)]))
        return out
```

e nel corpo di `subject_bucket` sostituire il ciclo con:

```python
            lits = [lit for _, lit in self.subject_literals(
                keys, subject_id, kind, bucket, signature)]
            return self._max_or_zero(var, lits)
```

- [ ] **Step 5: Riscrivere `subject_buckets.py`**

```python
"""I vincoli di materia che si esprimono come cardinalita' su un **secchio**
(giornata o mezza giornata). L'attivita' si attribuisce al secchio della sua
fascia di **partenza**, come nei checker."""

from domain.models import SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register

T = SubjectConstraint.Type


class _BucketIncompatible(SubjectBuilder):
    """Con A = B (il caso dominante nei dati reali di EDT: non due ore della
    stessa materia nello stesso giorno) e' «al piu' un'occorrenza per secchio».
    Con A != B e' «le due materie non coesistono nel secchio»."""

    KIND = None   # "day" | "half"

    def buckets(self, ctx):
        n = ctx.grid.days_per_cycle
        return range(n) if self.KIND == "day" else range(n * 2)

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        for bucket in self.buckets(ctx):
            if row.subject_a_id == row.subject_b_id:
                lits = v.subject_literals(keys, row.subject_a_id, self.KIND,
                                          bucket, signature=rep)
                if len({aid for aid, _ in lits}) > 1:
                    model.Add(sum(lit for _, lit in lits) <= 1)
                continue
            ha = v.subject_bucket(keys, row.subject_a_id, self.KIND, bucket,
                                  signature=rep)
            hb = v.subject_bucket(keys, row.subject_b_id, self.KIND, bucket,
                                  signature=rep)
            model.Add(ha + hb <= 1)


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayBuilder(_BucketIncompatible):
    TYPE, KIND = T.SAME_DAY_INCOMPATIBLE, "day"


@register(T.SAME_HALF_DAY_INCOMPATIBLE)
class SameHalfDayBuilder(_BucketIncompatible):
    TYPE, KIND = T.SAME_HALF_DAY_INCOMPATIBLE, "half"


@register(T.TWO_DAYS_INCOMPATIBLE)
class TwoDaysBuilder(SubjectBuilder):
    """A nel giorno d e B nel giorno d+1 non coesistono.

    ⚠ Il checker richiede `len(set(acts)) > 1` per emettere il finding: serve
    a non segnalare una singola attivita' contro se' stessa. Qui la condizione
    e' automatica, perche' un'attivita' non puo' stare in due giorni."""
    TYPE = T.TWO_DAYS_INCOMPATIBLE

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        for day in range(ctx.grid.days_per_cycle - 1):
            ha = v.subject_bucket(keys, row.subject_a_id, "day", day,
                                  signature=rep)
            hb = v.subject_bucket(keys, row.subject_b_id, "day", day + 1,
                                  signature=rep)
            model.Add(ha + hb <= 1)
```

⚠ Il vecchio metodo statico `_literals` sparisce: lo sostituisce
`vocab.subject_literals`. E il paragrafo «Semplificazione dichiarata» del
vecchio docstring **va rimosso**, non riadattato: non è più vero.

- [ ] **Step 6: I due derivatori**

```python
@deriver(ST.SAME_HALF_DAY_INCOMPATIBLE, {"subject_same_half_day"})
def _derive_same_half_day(w):
    grid = w.env["grid"]
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            per_meta = defaultdict(int)
            for aid, (day, slot) in w.placement.items():
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk:
                    per_meta[(day, slot >= grid.morning_end_slot)] += 1
            if per_meta and max(per_meta.values()) == 1:
                SubjectConstraint.objects.create(
                    subject_a=subject, subject_b=subject, school_class=klass,
                    type=ST.SAME_HALF_DAY_INCOMPATIBLE)
                return


@deriver(ST.TWO_DAYS_INCOMPATIBLE, {"subject_two_days"})
def _derive_two_days(w):
    """Cerca una coppia di materie distinte che nel testimone non compaia mai
    in giorni consecutivi sulla stessa classe."""
    for klass in w.env["classes"]:
        giorni = defaultdict(set)
        for aid, (day, _slot) in w.placement.items():
            if klass.pk in w.tokens[aid]:
                giorni[w.act(aid).subject_id].add(day)
        for a in w.env["subjects"]:
            for b in w.env["subjects"]:
                if a.pk == b.pk:
                    continue
                if not any(d + 1 in giorni[b.pk] for d in giorni[a.pk]):
                    SubjectConstraint.objects.create(
                        subject_a=a, subject_b=b, school_class=klass,
                        type=ST.TWO_DAYS_INCOMPATIBLE)
                    return
```

- [ ] **Step 7: Eseguire**

Run: `venv/bin/pytest tests/test_solver_subject_buckets.py tests/test_solver_same_day.py -q`
Expected: PASS — inclusi i test esistenti di `SAME_DAY`, che il refactor non
deve toccare.

Run: `venv/bin/pytest -q`
Expected: **274 passed** (262 + 12)

- [ ] **Step 8: Commit**

```bash
git add domain/solver/builders/base.py domain/solver/builders/subject_buckets.py domain/solver/vocabulary.py tests/solver_harness.py tests/test_solver_subject_buckets.py
git commit -m "$(cat <<'EOF'
feat(solver): SAME_HALF_DAY e TWO_DAYS, sullo scheletro di materia

SubjectBuilder itera per firma di settimana con deduplicazione, quindi la
semplificazione "tutte co-attive" che SameDayBuilder dichiarava non serve
piu' e sparisce dal docstring invece di restare li' a sembrare una
strategia da imitare. Sulla firma unica del Fermi il costo e' zero.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: `MAX_HOURS_DAY`, `MAX_HOURS_HALF_DAY`, `FORBIDDEN_SEQUENCE`

**Files:**
- Modify: `domain/solver/builders/subject_buckets.py`
- Modify: `tests/solver_harness.py` (tre derivatori)
- Test: `tests/test_solver_subject_maxhours.py`

**Interfaces:**
- Produces: `MaxHoursDayBuilder` (`T.MAX_HOURS_DAY`),
  `MaxHoursHalfDayBuilder` (`T.MAX_HOURS_HALF_DAY`),
  `ForbiddenSequenceBuilder` (`T.FORBIDDEN_SEQUENCE`).

**⚠ `_MaxHours.violations` somma solo `a`, mai `b`.** Anche quando A ≠ B, il
tetto vale sulle ore della **sola** materia A. Sommare anche B sarebbe un
vincolo diverso, e più stretto in modo non richiesto.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_subject_maxhours.py
"""Tetto di ore per materia in un secchio, e sequenza vietata."""
import pytest

from domain.models import Subject, SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tipo", [T.MAX_HOURS_DAY, T.MAX_HOURS_HALF_DAY,
                                  T.FORBIDDEN_SEQUENCE])
def test_sul_banco(tipo, seed):
    run_family(tipo, seed)


def test_max_hours_day_limita_la_materia():
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.MAX_HOURS_DAY, param=120)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    per_giorno = {}
    for (day, _slot) in soluzione.placements.values():
        per_giorno[day] = per_giorno.get(day, 0) + 1
    assert max(per_giorno.values()) <= 2


def test_forbidden_sequence_vieta_l_adiacenza():
    """B non puo' iniziare esattamente dove A finisce, nello stesso giorno."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    (ga, sa), (gb, sb) = soluzione.placements[a.id], soluzione.placements[b.id]
    assert not (ga == gb and sb == sa + 1)
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_subject_maxhours.py -q`
Expected: FAIL

- [ ] **Step 3: Aggiungere i tre builder a `subject_buckets.py`**

```python
from domain.solver.residual import residual_cap


class _MaxHoursSubject(SubjectBuilder):
    """⚠ Il checker somma le ore della **sola** materia A, anche quando
    A != B: `_MaxHours.violations` itera su `a` e ignora `b`."""

    KIND = None

    def buckets(self, ctx):
        n = ctx.grid.days_per_cycle
        return range(n) if self.KIND == "day" else range(n * 2)

    def post(self, ctx, model, row, keys, rep):
        if row.param is None:
            return
        for bucket in self.buckets(ctx):
            lits = ctx.vocab.subject_literals(keys, row.subject_a_id, self.KIND,
                                              bucket, signature=rep)
            terms = [(ctx.activities[aid].duration_minutes, aid, lit)
                     for aid, lit in lits]
            liberi, residuo = residual_cap(ctx, terms, row.param)
            if liberi:
                model.Add(sum(w * lit for w, lit in liberi) <= residuo)


@register(T.MAX_HOURS_DAY)
class MaxHoursDayBuilder(_MaxHoursSubject):
    TYPE, KIND = T.MAX_HOURS_DAY, "day"


@register(T.MAX_HOURS_HALF_DAY)
class MaxHoursHalfDayBuilder(_MaxHoursSubject):
    TYPE, KIND = T.MAX_HOURS_HALF_DAY, "half"


@register(T.FORBIDDEN_SEQUENCE)
class ForbiddenSequenceBuilder(SubjectBuilder):
    """B non puo' iniziare esattamente dove A finisce, nello stesso giorno.
    Proibizione di coppie di celle: nessuna variabile derivata serve."""
    TYPE = T.FORBIDDEN_SEQUENCE

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        a = v.subject_activities(keys, row.subject_a_id, signature=rep)
        b = v.subject_activities(keys, row.subject_b_id, signature=rep)
        for pa in a:
            durata = ctx.activities[pa].duration_slots
            for pb in b:
                if pb == pa:
                    continue
                if pa not in ctx.free and pb not in ctx.free:
                    continue   # un fatto, non una decisione
                for (day, slot) in sorted(ctx.cells[pa]):
                    fine = slot + durata
                    if (day, fine) not in ctx.cells[pb]:
                        continue
                    model.AddBoolOr([ctx.x[(pa, day, slot)].Not(),
                                     ctx.x[(pb, day, fine)].Not()])
```

- [ ] **Step 4: I tre derivatori**

```python
def _derive_max_hours_subject(w, tipo, kind):
    grid = w.env["grid"]
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            per_secchio = defaultdict(int)
            for aid, (day, slot) in w.placement.items():
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk:
                    secchio = (day if kind == "day"
                               else day * 2 + (slot >= grid.morning_end_slot))
                    per_secchio[secchio] += w.act(aid).duration_minutes
            if per_secchio:
                SubjectConstraint.objects.create(
                    subject_a=subject, subject_b=subject, school_class=klass,
                    type=tipo, param=max(per_secchio.values()))
                return


@deriver(ST.MAX_HOURS_DAY, {"subject_max_hours_day"})
def _derive_max_hours_day(w):
    _derive_max_hours_subject(w, ST.MAX_HOURS_DAY, "day")


@deriver(ST.MAX_HOURS_HALF_DAY, {"subject_max_hours_half_day"})
def _derive_max_hours_half_day(w):
    _derive_max_hours_subject(w, ST.MAX_HOURS_HALF_DAY, "half")


@deriver(ST.FORBIDDEN_SEQUENCE, {"subject_forbidden_sequence"})
def _derive_forbidden_sequence(w):
    """Una coppia di materie che nel testimone non compare mai adiacente."""
    for klass in w.env["classes"]:
        adiacenti = set()
        for aid, (day, slot) in w.placement.items():
            if klass.pk not in w.tokens[aid]:
                continue
            fine = slot + w.act(aid).duration_slots
            for altro, (day2, slot2) in w.placement.items():
                if altro != aid and day2 == day and slot2 == fine and klass.pk in w.tokens[altro]:
                    adiacenti.add((w.act(aid).subject_id, w.act(altro).subject_id))
        for a in w.env["subjects"]:
            for b in w.env["subjects"]:
                if a.pk != b.pk and (a.pk, b.pk) not in adiacenti:
                    SubjectConstraint.objects.create(
                        subject_a=a, subject_b=b, school_class=klass,
                        type=ST.FORBIDDEN_SEQUENCE)
                    return
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_subject_maxhours.py -q`
Expected: PASS (17 test)

Run: `venv/bin/pytest -q`
Expected: **291 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/subject_buckets.py tests/solver_harness.py tests/test_solver_subject_maxhours.py
git commit -m "$(cat <<'EOF'
feat(solver): MAX_HOURS_DAY, MAX_HOURS_HALF_DAY, FORBIDDEN_SEQUENCE

I tetti di ore contano la sola materia A anche quando A != B: e' cosi' che
_MaxHours.violations itera, e sommare anche B sarebbe un vincolo diverso.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 5 — I sette vincoli di materia d'ordine

### Task 12: `WEEKLY_ORDER`

**Files:**
- Create: `domain/solver/builders/subject_order.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/solver_harness.py` (un derivatore)
- Test: `tests/test_solver_subject_order.py`

**Interfaces:**
- Consumes: `vocab.pos`, `vocab.subject_activities`, `SubjectBuilder`.
- Produces: `WeeklyOrderBuilder` (`T.WEEKLY_ORDER`).

**⚠ Il checker esce senza vincolare in due casi**, non uno:
`if row.subject_a_id == row.subject_b_id or not a or not b: return`. Cioè anche
quando **A = B**, che in tutte le altre famiglie è il caso dominante. Entrambi
si conoscono staticamente.

- [ ] **Step 1: Scrivere il test che fallisce**

```python
# tests/test_solver_subject_order.py
"""I vincoli di materia che ragionano sull'ordine. Nessuno di questi richiede
di ordinare davvero: si esprimono tutti con confronti fra coppie."""
import pytest

from domain.models import Subject, SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_weekly_order_sul_banco(seed):
    run_family(T.WEEKLY_ORDER, seed)


def test_weekly_order_impone_la_prima_occorrenza():
    """La prima ora di A dev'essere prima della prima ora di B."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = [make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]]) for _ in range(2)]
    b = [make_activity(matematica, teachers=[env["teacher"]],
                       classes=[env["klass"]]) for _ in range(2)]
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    def prima(gruppo):
        return min(soluzione.placements[x.id] for x in gruppo)
    assert prima(a) <= prima(b)


def test_weekly_order_con_a_uguale_b_non_vincola_nulla():
    """Il checker esce subito quando A = B: il builder deve fare lo stesso,
    altrimenti impone un ordine fra un'attivita' e se stessa."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.WEEKLY_ORDER)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_subject_order.py -q`
Expected: FAIL con `nessun derivatore per SubjectConstraint.Type.WEEKLY_ORDER`

- [ ] **Step 3: Scrivere `domain/solver/builders/subject_order.py`**

```python
"""I vincoli di materia che ragionano sull'**ordine**.

Nessuno di questi richiede di ordinare davvero le occorrenze nel modello: si
esprimono tutti con confronti fra coppie, o con la costruzione «questi due
estremi e niente in mezzo» — la stessa che time_sites.py usa per i cambi di
sede. Ordinare in CP-SAT costa; questi vincoli non lo chiedono."""

from domain.models import SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register

T = SubjectConstraint.Type


@register(T.WEEKLY_ORDER)
class WeeklyOrderBuilder(SubjectBuilder):
    """La prima occorrenza di A precede la prima occorrenza di B.

    ⚠ WeeklyOrderChecker esce senza vincolare in **due** casi:
    `if row.subject_a_id == row.subject_b_id or not a or not b: return`.
    Anche con A = B, quindi — che nelle altre famiglie e' invece il caso
    dominante."""
    TYPE = T.WEEKLY_ORDER

    def post(self, ctx, model, row, keys, rep):
        if row.subject_a_id == row.subject_b_id:
            return
        v = ctx.vocab
        a = v.subject_activities(keys, row.subject_a_id, signature=rep)
        b = v.subject_activities(keys, row.subject_b_id, signature=rep)
        if not a or not b:
            return
        limite = ctx.grid.days_per_cycle * ctx.grid.slots_per_day
        prima_a = model.NewIntVar(0, limite, f"first_a_{row.pk}_{rep}")
        model.AddMinEquality(prima_a, [v.pos(aid) for aid in a])
        prima_b = model.NewIntVar(0, limite, f"first_b_{row.pk}_{rep}")
        model.AddMinEquality(prima_b, [v.pos(aid) for aid in b])
        model.Add(prima_a <= prima_b)
```

- [ ] **Step 4: Il derivatore**

```python
@deriver(ST.WEEKLY_ORDER, {"subject_weekly_order"})
def _derive_weekly_order(w):
    """Sceglie l'ordine che il testimone gia' esibisce."""
    for klass in w.env["classes"]:
        prime = {}
        for aid, cella in w.placement.items():
            if klass.pk in w.tokens[aid]:
                s = w.act(aid).subject_id
                prime[s] = min(prime.get(s, cella), cella)
        materie = sorted(prime, key=lambda s: prime[s])
        if len(materie) >= 2:
            SubjectConstraint.objects.create(
                subject_a_id=materie[0], subject_b_id=materie[-1],
                school_class=klass, type=ST.WEEKLY_ORDER)
            return
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_subject_order.py -q`
Expected: PASS (7 test)

Run: `venv/bin/pytest -q`
Expected: **298 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/subject_order.py domain/solver/builders/__init__.py tests/solver_harness.py tests/test_solver_subject_order.py
git commit -m "$(cat <<'EOF'
feat(solver): WEEKLY_ORDER

AddMinEquality sulle posizioni canalizzate. Il builder esce senza
vincolare anche con A = B, come fa il checker: e' il caso che nelle altre
dodici famiglie e' dominante, e qui invece non vincola nulla.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: `IMPOSED_SUCCESSION`

**Files:**
- Modify: `domain/solver/builders/subject_order.py`
- Modify: `tests/solver_harness.py` (un derivatore)
- Test: `tests/test_solver_subject_order.py` (aggiunge test)

**Interfaces:**
- Produces: `ImposedSuccessionBuilder` (`T.IMPOSED_SUCCESSION`).

Due semantiche in una riga, come nel checker. **Con A = B**: gli scarti fra
mezze giornate consecutive non superano `delay`. **Con A ≠ B**: dopo ogni
occorrenza di A ne serve una di B entro `delay` mezze giornate.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# in coda a tests/test_solver_subject_order.py

@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_imposed_succession_sul_banco(seed):
    run_family(T.IMPOSED_SUCCESSION, seed)


def test_imposed_succession_a_uguale_b_non_lascia_buchi_lunghi():
    """Due ore della stessa materia, ritardo massimo una mezza giornata: non
    possono stare a piu' di una mezza giornata di distanza."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.IMPOSED_SUCCESSION, param=1)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    mezze = sorted(day * 2 + (0 if slot < 4 else 1)
                   for (day, slot) in soluzione.placements.values())
    assert mezze[-1] - mezze[0] <= 1
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_subject_order.py -q -k imposed`
Expected: FAIL

- [ ] **Step 3: Aggiungere il builder a `subject_order.py`**

```python
@register(T.IMPOSED_SUCCESSION)
class ImposedSuccessionBuilder(SubjectBuilder):
    """Con A = B: gli scarti fra mezze giornate **consecutive** non superano
    `delay`. Si esprime senza ordinare: per ogni coppia di mezze giornate
    u < v con v - u > delay, si vieta «A in u, A in v, e nessuna A in mezzo».
    Su dieci mezze giornate sono 45 coppie.

    Con A != B: dopo ogni occorrenza di A ne serve una di B entro `delay`
    mezze giornate — un OR reificato sulle mezze giornate di B."""
    TYPE = T.IMPOSED_SUCCESSION

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        delay = row.param or 1
        n = ctx.grid.days_per_cycle * 2
        sa = [v.subject_bucket(keys, row.subject_a_id, "half", h, signature=rep)
              for h in range(n)]
        if row.subject_a_id == row.subject_b_id:
            for u in range(n):
                for w in range(u + delay + 1, n):
                    model.AddBoolOr(
                        [sa[u].Not(), sa[w].Not()]
                        + [sa[m] for m in range(u + 1, w)])
            return
        sb = [v.subject_bucket(keys, row.subject_b_id, "half", h, signature=rep)
              for h in range(n)]
        for u in range(n):
            finestra = [sb[w] for w in range(u + 1, min(u + delay + 1, n))]
            # A in u implica almeno una B nella finestra; se la finestra e'
            # vuota, A non puo' stare in u
            model.AddBoolOr([sa[u].Not()] + finestra)
```

- [ ] **Step 4: Il derivatore**

```python
@deriver(ST.IMPOSED_SUCCESSION, {"subject_imposed_succession"})
def _derive_imposed_succession(w):
    """A = B, con il ritardo massimo osservato fra occorrenze consecutive."""
    grid = w.env["grid"]
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            mezze = sorted(
                day * 2 + (slot >= grid.morning_end_slot)
                for aid, (day, slot) in w.placement.items()
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk)
            if len(mezze) < 2:
                continue
            scarto = max(b - a for a, b in zip(mezze, mezze[1:]))
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=ST.IMPOSED_SUCCESSION, param=max(1, scarto))
            return
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_subject_order.py -q`
Expected: PASS (13 test)

Run: `venv/bin/pytest -q`
Expected: **304 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/subject_order.py tests/solver_harness.py tests/test_solver_subject_order.py
git commit -m "$(cat <<'EOF'
feat(solver): IMPOSED_SUCCESSION, senza ordinare

"Gli scarti fra occorrenze consecutive non superano delay" si dice come
"per ogni coppia u < v troppo distante, non entrambe con niente in mezzo".
Su dieci mezze giornate sono 45 coppie: ordinare in CP-SAT sarebbe costato
molto di piu' per la stessa cosa.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: `HALF_DAY_GAP` — il conservativo dimostrato

**Files:**
- Modify: `domain/solver/builders/subject_order.py`
- Modify: `tests/solver_harness.py` (un derivatore)
- Test: `tests/test_solver_half_day_gap.py`

**Interfaces:**
- Produces: `HalfDayGapBuilder` (`T.HALF_DAY_GAP`).

**Il conservativo numero uno** (spec §4.2). `HalfDayGapChecker` ordina le
occorrenze e vincola le **coppie consecutive**, e con A ≠ B soltanto quelle
incrociate (`crossed = same or s1 != s2`). Il builder vincola **tutte** le
coppie incrociate. Le consecutive incrociate sono un sottoinsieme di tutte le
incrociate, quindi ogni piazzamento accettato dal modello è accettato dal
checker: più stretto, mai più largo.

**⚠ Il derivatore deriva contro la regola del builder** (tutte le coppie), non
contro quella del checker. È così che la direzione diventa verificata a ogni
esecuzione invece che argomentata una volta (spec §5.2).

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_half_day_gap.py
"""Scarto minimo fra occorrenze, in mezze giornate. Il checker e' simmetrico
anche con A != B: lo scarto e' una distanza, e la distanza non ha verso."""
import pytest

from domain.models import SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_half_day_gap_sul_banco(seed):
    run_family(T.HALF_DAY_GAP, seed)


def test_half_day_gap_separa_le_occorrenze():
    """Tre ore della stessa materia, scarto minimo due mezze giornate."""
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=2)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    mezze = sorted(day * 2 + (0 if slot < 4 else 1)
                   for (day, slot) in soluzione.placements.values())
    assert all(b - a >= 2 for a, b in zip(mezze, mezze[1:]))
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_half_day_gap.py -q`
Expected: FAIL

- [ ] **Step 3: Aggiungere il builder a `subject_order.py`**

```python
@register(T.HALF_DAY_GAP)
class HalfDayGapBuilder(SubjectBuilder):
    """Scarto minimo fra occorrenze, misurato in mezze giornate.

    ⚠ **Conservativo, con la direzione dimostrata** (spec §4.2).
    HalfDayGapChecker ordina le occorrenze e vincola le coppie **consecutive**
    nell'ordinamento, e con A != B soltanto quelle incrociate fra le due
    materie. Qui si vincolano **tutte** le coppie incrociate.

    Direzione: l'insieme delle coppie consecutive incrociate e' un
    sottoinsieme di tutte le coppie incrociate, quindi un piazzamento che
    soddisfa il vincolo su tutte le coppie lo soddisfa in particolare sulle
    consecutive. Il modello e' piu' stretto, mai piu' largo.

    ⚠ Il checker e' **simmetrico** anche con A != B: `crossed` non guarda il
    verso della relazione. Qui idem — nessun ordinamento fra A e B."""
    TYPE = T.HALF_DAY_GAP

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        minimo = row.param
        if not minimo:
            return
        n = ctx.grid.days_per_cycle * 2
        same = row.subject_a_id == row.subject_b_id
        for u in range(n):
            for w in range(u, min(u + minimo, n)):
                if same:
                    if w == u:
                        lits = v.subject_literals(keys, row.subject_a_id,
                                                  "half", u, signature=rep)
                        if len({aid for aid, _ in lits}) > 1:
                            model.Add(sum(lit for _, lit in lits) <= 1)
                        continue
                    a_u = v.subject_bucket(keys, row.subject_a_id, "half", u,
                                           signature=rep)
                    a_w = v.subject_bucket(keys, row.subject_a_id, "half", w,
                                           signature=rep)
                    model.Add(a_u + a_w <= 1)
                else:
                    a_u = v.subject_bucket(keys, row.subject_a_id, "half", u,
                                           signature=rep)
                    b_w = v.subject_bucket(keys, row.subject_b_id, "half", w,
                                           signature=rep)
                    model.Add(a_u + b_w <= 1)
                    if w != u:
                        b_u = v.subject_bucket(keys, row.subject_b_id, "half",
                                               u, signature=rep)
                        a_w = v.subject_bucket(keys, row.subject_a_id, "half",
                                               w, signature=rep)
                        model.Add(b_u + a_w <= 1)
```

- [ ] **Step 4: Il derivatore, contro la regola del builder**

```python
@deriver(ST.HALF_DAY_GAP, {"subject_half_day_gap"})
def _derive_half_day_gap(w):
    """⚠ Deriva contro la regola del **builder** (tutte le coppie), non contro
    quella del checker (le sole coppie consecutive incrociate). Il testimone
    resta valido per entrambi, e la direzione conservativa e' verificata a
    ogni esecuzione invece che argomentata una volta in spec."""
    grid = w.env["grid"]
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            mezze = sorted(
                day * 2 + (slot >= grid.morning_end_slot)
                for aid, (day, slot) in w.placement.items()
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk)
            if len(mezze) < 2:
                continue
            minimo = min(b - a for a in mezze for b in mezze if b > a)
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=ST.HALF_DAY_GAP, param=minimo)
            return
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_half_day_gap.py -q`
Expected: PASS (6 test)

Run: `venv/bin/pytest -q`
Expected: **310 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/subject_order.py tests/solver_harness.py tests/test_solver_half_day_gap.py
git commit -m "$(cat <<'EOF'
feat(solver): HALF_DAY_GAP, il conservativo dimostrato

Il checker vincola le coppie consecutive nell'ordinamento; il builder
vincola tutte le coppie incrociate. Le prime sono un sottoinsieme delle
seconde, quindi il modello e' piu' stretto e mai piu' largo.

Il derivatore del banco deriva contro la regola del builder, non contro
quella del checker: la direzione e' cosi' verificata a ogni esecuzione.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: I quattro `PARTS_*`

**Files:**
- Create: `domain/solver/builders/subject_parts.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/solver_harness.py` (partizioni nella scuola, quattro derivatori)
- Test: `tests/test_solver_subject_parts.py`

**Interfaces:**
- Produces: `PartsBeforeBuilder` (`T.PARTS_BEFORE_CLASS`),
  `PartsAfterBuilder` (`T.PARTS_AFTER_CLASS`),
  `PartsHomogeneousHalfBuilder` (`T.PARTS_BEFORE_OR_AFTER_CLASS_H`),
  `PartsHomogeneousDayBuilder` (`T.PARTS_BEFORE_OR_AFTER_CLASS_AB`).

**⚠ Il secchio dei due omogenei è diverso.** `_PartsOrder.bucket` restituisce
`pl.day`; `PartsHomogeneousHalfChecker` lo **sovrascrive** con la mezza
giornata. Quindi `_H` = mezza giornata, `_AB` = giornata. È l'unica differenza
fra i due, e invertirla non fa fallire nessun test ovvio.

**⚠ `_PartsOrder.violations` usa solo `a`**, mai `b`: la materia B non entra.

- [ ] **Step 1: Dare partizioni alla scuola del banco**

In `tests/solver_harness.py`, dentro `_school`, dopo la creazione delle classi:

```python
    from domain.models import ClassPart, ClassPartition
    partizione = ClassPartition.objects.create(
        school_class=classes[0], name="LINGUA")
    parts = [ClassPart.objects.create(name=n, partition=partizione)
             for n in ("1A_ING", "1A_TED")]
```
e nel dizionario restituito: `"parts": parts`.

In `_make_activities`, in coda, aggiungere due attività di parte:

```python
    for part in env["parts"]:
        subject = rng.choice(env["subjects"])
        act = Activity.objects.create(
            subject=subject, duration_slots=1, duration_minutes=60,
            week_mask=rng.choice(MASKS))
        act.teachers.add(rng.choice(env["teachers"]))
        act.parts.add(part)
        service, _ = Service.objects.get_or_create(
            study_plan=part.effective_study_plan, subject=subject,
            defaults={"class_minutes": 0})
        service.class_minutes += 60
        service.save()
        out.append(act)
```

⚠ Questo arricchisce **tutti** i banchi di prova, non solo questo task: le
famiglie già scritte inizieranno a vedere attività di parte e i loro token.
È voluto. Se qualche seed diventasse infattibile, `build_witness` lo dice con
un messaggio esplicito («la fixture è troppo densa») e si riduce il numero di
attività per classe da `capienza // 2` a `capienza // 3`.

- [ ] **Step 2: Scrivere i test che falliscono**

```python
# tests/test_solver_subject_parts.py
"""L'ordine fra le ore in gruppo e le ore a classe intera: i quattro valori
Parties...Classe di EDT."""
import pytest

from domain.models import ClassPart, ClassPartition, SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tipo", [T.PARTS_BEFORE_CLASS, T.PARTS_AFTER_CLASS,
                                  T.PARTS_BEFORE_OR_AFTER_CLASS_H,
                                  T.PARTS_BEFORE_OR_AFTER_CLASS_AB])
def test_parts_sul_banco(tipo, seed):
    run_family(tipo, seed)


def _classe_con_parte(env):
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="LINGUA")
    return ClassPart.objects.create(name="1A_ING", partition=partizione)


def test_parts_before_class_mette_le_parti_prima():
    """Un'ora di gruppo e un'ora a classe intera nello stesso giorno: la
    prima dev'essere quella di gruppo."""
    env = mini_school()
    parte = _classe_con_parte(env)
    gruppo = make_activity(env["subject"], teachers=[env["teacher"]], parts=[parte])
    intera = make_activity(env["subject"], classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.PARTS_BEFORE_CLASS)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    (gg, sg), (gi, si) = soluzione.placements[gruppo.id], soluzione.placements[intera.id]
    if gg == gi:
        assert sg <= si


def test_parts_after_class_mette_le_parti_dopo():
    env = mini_school()
    parte = _classe_con_parte(env)
    gruppo = make_activity(env["subject"], teachers=[env["teacher"]], parts=[parte])
    intera = make_activity(env["subject"], classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.PARTS_AFTER_CLASS)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    (gg, sg), (gi, si) = soluzione.placements[gruppo.id], soluzione.placements[intera.id]
    if gg == gi:
        assert sg >= si
```

- [ ] **Step 3: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_subject_parts.py -q`
Expected: FAIL

- [ ] **Step 4: Scrivere `domain/solver/builders/subject_parts.py`**

```python
"""L'ordine fra le ore **in gruppo** e le ore **a classe intera** dentro lo
stesso secchio: i quattro valori Parties...Classe di EDT.

⚠ `_PartsOrder.violations` guarda la sola materia A: B non entra.

⚠ Il secchio dei due omogenei e' diverso, e la differenza sta in una
sovrascrittura di metodo facile da non vedere: `_PartsOrder.bucket` restituisce
il giorno, e `PartsHomogeneousHalfChecker` lo sovrascrive con la mezza
giornata. Quindi _H = mezza giornata, _AB = giornata."""

from domain.models import SubjectConstraint
from domain.models.resources import Resource
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register

T = SubjectConstraint.Type


class _PartsOrder(SubjectBuilder):
    KIND = "day"
    MODE = None   # "before" | "after" | "homogeneous"

    def _livelli(self, ctx, keys, row, rep):
        """(celle di classe intera, celle di parte), come
        [(id, giorno, fascia, letterale)]."""
        kinds = ctx.states[rep].kinds
        classe, parte = [], []
        for aid in ctx.vocab.subject_activities(keys, row.subject_a_id,
                                                signature=rep):
            e_classe = any(kinds.get(k) == Resource.Kind.CLASS
                           for k in ctx.tokens[aid])
            for (day, slot) in sorted(ctx.cells[aid]):
                voce = (aid, day, slot, ctx.x[(aid, day, slot)])
                (classe if e_classe else parte).append(voce)
        return classe, parte

    def post(self, ctx, model, row, keys, rep):
        classe, parte = self._livelli(ctx, keys, row, rep)
        if not classe or not parte:
            return
        v = ctx.vocab
        if self.MODE in ("before", "after"):
            for (_ap, dp, sp, xp) in parte:
                for (_ac, dc, sc, xc) in classe:
                    if v.bucket_of(self.KIND, dp, sp) != v.bucket_of(self.KIND, dc, sc):
                        continue
                    male = sp > sc if self.MODE == "before" else sp < sc
                    if male:
                        model.AddBoolOr([xp.Not(), xc.Not()])
            return
        # omogeneo: tutte le parti prima di tutte le classi, **oppure** tutte
        # le classi prima di tutte le parti. E' esattamente «al piu' una
        # transizione» nella sequenza di etichette del checker.
        secchi = {v.bucket_of(self.KIND, d, s) for (_a, d, s, _x) in classe + parte}
        for secchio in sorted(secchi):
            prima_le_parti = model.NewBoolVar(f"parts_first_{row.pk}_{rep}_{secchio}")
            for (_ap, dp, sp, xp) in parte:
                if v.bucket_of(self.KIND, dp, sp) != secchio:
                    continue
                for (_ac, dc, sc, xc) in classe:
                    if v.bucket_of(self.KIND, dc, sc) != secchio:
                        continue
                    if sp > sc:
                        model.AddBoolOr([xp.Not(), xc.Not()]).OnlyEnforceIf(
                            prima_le_parti)
                    if sp < sc:
                        model.AddBoolOr([xp.Not(), xc.Not()]).OnlyEnforceIf(
                            prima_le_parti.Not())


@register(T.PARTS_BEFORE_CLASS)
class PartsBeforeBuilder(_PartsOrder):
    TYPE, MODE, KIND = T.PARTS_BEFORE_CLASS, "before", "day"


@register(T.PARTS_AFTER_CLASS)
class PartsAfterBuilder(_PartsOrder):
    TYPE, MODE, KIND = T.PARTS_AFTER_CLASS, "after", "day"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_H)
class PartsHomogeneousHalfBuilder(_PartsOrder):
    TYPE, MODE, KIND = T.PARTS_BEFORE_OR_AFTER_CLASS_H, "homogeneous", "half"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
class PartsHomogeneousDayBuilder(_PartsOrder):
    TYPE, MODE, KIND = T.PARTS_BEFORE_OR_AFTER_CLASS_AB, "homogeneous", "day"
```

- [ ] **Step 5: I quattro derivatori**

```python
def _derive_parts(w, tipo, kind):
    """Crea la riga solo se il testimone la soddisfa gia'. Se nessuna
    (classe, materia) va bene per quel modo, non crea nulla: meglio un seed
    vacuo che un testimone invalido — run_family lo direbbe al punto 1."""
    grid = w.env["grid"]
    klass = w.env["classes"][0]
    for subject in w.env["subjects"]:
        secchi = defaultdict(list)
        for aid, (day, slot) in w.placement.items():
            if w.act(aid).subject_id != subject.pk:
                continue
            if not (w.tokens[aid] & ({klass.pk} | {p.pk for p in w.env["parts"]})):
                continue
            e_classe = klass.pk in w.tokens[aid]
            secchio = (day if kind == "day"
                       else day * 2 + (slot >= grid.morning_end_slot))
            secchi[secchio].append((slot, "class" if e_classe else "part"))
        ok = True
        for _s, voci in secchi.items():
            voci.sort()
            etichette = [e for _s2, e in voci]
            if "class" not in etichette or "part" not in etichette:
                continue
            transizioni = sum(x != y for x, y in zip(etichette, etichette[1:]))
            if tipo == ST.PARTS_BEFORE_CLASS:
                ok &= etichette[0] == "part" and transizioni <= 1
            elif tipo == ST.PARTS_AFTER_CLASS:
                ok &= etichette[0] == "class" and transizioni <= 1
            else:
                ok &= transizioni <= 1
        if ok:
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=tipo)
            return


@deriver(ST.PARTS_BEFORE_CLASS, {"subject_parts_order"})
def _derive_parts_before(w):
    _derive_parts(w, ST.PARTS_BEFORE_CLASS, "day")


@deriver(ST.PARTS_AFTER_CLASS, {"subject_parts_order"})
def _derive_parts_after(w):
    _derive_parts(w, ST.PARTS_AFTER_CLASS, "day")


@deriver(ST.PARTS_BEFORE_OR_AFTER_CLASS_H, {"subject_parts_order"})
def _derive_parts_h(w):
    _derive_parts(w, ST.PARTS_BEFORE_OR_AFTER_CLASS_H, "half")


@deriver(ST.PARTS_BEFORE_OR_AFTER_CLASS_AB, {"subject_parts_order"})
def _derive_parts_ab(w):
    _derive_parts(w, ST.PARTS_BEFORE_OR_AFTER_CLASS_AB, "day")
```

- [ ] **Step 6: Eseguire**

Run: `venv/bin/pytest tests/test_solver_subject_parts.py -q`
Expected: PASS (22 test)

Run: `venv/bin/pytest -q`
Expected: **332 passed**. ⚠ Se qualche test di un'ondata precedente diventa
rosso, la causa è l'arricchimento della fixture allo Step 1, non il builder
nuovo: le attività di parte hanno reso più densa la scuola del banco.

- [ ] **Step 7: Commit**

```bash
git add domain/solver/builders/subject_parts.py domain/solver/builders/__init__.py tests/solver_harness.py tests/test_solver_subject_parts.py
git commit -m "$(cat <<'EOF'
feat(solver): i quattro PARTS_*

L'omogeneo ("al piu' una transizione" nella sequenza di etichette) e' la
disgiunzione "tutte le parti prima, oppure tutte le classi prima", con un
booleano per secchio.

_H usa la mezza giornata e _AB la giornata: la differenza sta in una
sovrascrittura di bucket() nel checker, facile da non vedere.

La scuola del banco guadagna una partizione e due attivita' di parte, cosi'
gli atomi di ADR-017 entrano in tutti i banchi di prova.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 6 — Lo strutturale che resta

### Task 16: `structural:didactic_weight`

**Files:**
- Create: `domain/solver/builders/weight.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/solver_harness.py` (un derivatore)
- Test: `tests/test_solver_weight.py`

**Interfaces:**
- Produces: `DidacticWeightBuilder` (`"structural:didactic_weight"`).

**⚠ Tre dettagli del checker.** Il peso di un'attività è
`subject.didactic_weight × duration_slots` — una costante nota a build time. Le
unità su cui pesa sono le **parti** nei token, o la classe se la classe non ha
partizioni (`_student_keys`). E il tetto **settimanale** della classe prevale
su quello d'istituto: `class_caps[part_class[key]]`, e si ricade su
`settings.max_weight_week` solo se è `None`. **Ogni tetto `None` è spento**,
non zero.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_weight.py
"""Il peso didattico: il vincolo di carico cognitivo. In una base reale del
prodotto i quattro tetti sono tutti a «nessuno», quindi questo builder di
norma non posta nulla — il test li accende apposta."""
import pytest

from domain.models import InstituteSettings
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_peso_sul_banco(seed):
    run_family("structural:didactic_weight", seed)


def test_il_tetto_giornaliero_distribuisce_il_carico():
    env = mini_school()
    env["subject"].didactic_weight = 2
    env["subject"].save()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 4})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    per_giorno = {}
    for (day, _slot) in soluzione.placements.values():
        per_giorno[day] = per_giorno.get(day, 0) + 2
    assert max(per_giorno.values()) <= 4


def test_i_tetti_spenti_non_postano_nulla():
    """Tutti i tetti a None: il modello dev'essere identico a quello senza
    questo builder. Si verifica sul conteggio dei constraint."""
    from domain.solver.model import build_model
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": None, "max_weight_morning": None,
                        "max_weight_afternoon": None, "max_weight_week": None})
    model, _ctx = build_model(env["schedule"])
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    senza_peso = len(proto.constraints)
    InstituteSettings.objects.update_or_create(pk=1, defaults={"max_weight_day": 99})
    model2, _ = build_model(env["schedule"])
    proto2 = model2.proto if hasattr(model2, "proto") else model2.Proto()
    assert len(proto2.constraints) > senza_peso
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_weight.py -q`
Expected: FAIL

- [ ] **Step 3: Scrivere `domain/solver/builders/weight.py`**

```python
"""Il peso didattico (ADR-011): Totale = Peso x Durata, contato **per unita'
studente** e non per classe — il caso _REL/_ALT verificato sui dati.

⚠ In una base reale del prodotto i quattro tetti d'istituto sono tutti a
«nessuno»: questo builder di norma non posta nulla. E' corretto, e non e' un
bug da cercare quando il conteggio dei constraint non cambia."""

from collections import defaultdict

from domain.models.resources import Resource
from domain.solver.registry import Builder, register
from domain.solver.residual import residual_cap


def _student_keys(ctx, rep, aid):
    kinds = ctx.states[rep].kinds
    parts = [k for k in ctx.tokens[aid]
             if kinds.get(k) == Resource.Kind.CLASS_PART]
    if parts:
        return parts
    return [k for k in ctx.tokens[aid] if kinds.get(k) == Resource.Kind.CLASS]


@register("structural:didactic_weight")
class DidacticWeightBuilder(Builder):
    def build(self, ctx, model):
        v = ctx.vocab
        posted = set()
        for rep, _ in ctx.signatures:
            state = ctx.states[rep]
            s = state.settings
            per_day, per_half, per_week = (defaultdict(list), defaultdict(list),
                                           defaultdict(list))
            for aid, act in ctx.activities.items():
                if aid not in state.activities:
                    continue
                peso = act.subject.didactic_weight * act.duration_slots
                for (day, slot) in sorted(ctx.cells[aid]):
                    lit = ctx.x[(aid, day, slot)]
                    meta = v.half_of(slot)
                    for key in _student_keys(ctx, rep, aid):
                        per_day[(key, day)].append((peso, aid, lit))
                        per_half[(key, day, meta)].append((peso, aid, lit))
                        per_week[key].append((peso, aid, lit))

            def posta(bucket, terms, cap):
                if cap is None:
                    return
                firma = (bucket, frozenset(aid for _p, aid, _l in terms), cap)
                if firma in posted:
                    return
                posted.add(firma)
                liberi, residuo = residual_cap(ctx, terms, cap)
                if liberi:
                    model.Add(sum(p * lit for p, lit in liberi) <= residuo)

            for (key, day), terms in sorted(per_day.items(), key=lambda kv: str(kv[0])):
                posta(("day", key, day), terms, s.max_weight_day)
            for (key, day, meta), terms in sorted(per_half.items(),
                                                  key=lambda kv: str(kv[0])):
                cap = s.max_weight_morning if meta == 0 else s.max_weight_afternoon
                posta(("half", key, day, meta), terms, cap)
            for key, terms in sorted(per_week.items(), key=str):
                # ⚠ il tetto della classe prevale su quello d'istituto
                cap = state.class_caps.get(state.part_class.get(key, key))
                if cap is None:
                    cap = s.max_weight_week
                posta(("week", key), terms, cap)
```

- [ ] **Step 4: Il derivatore**

```python
@deriver("structural:didactic_weight", {"weight_day", "weight_morning",
                                        "weight_afternoon", "weight_week"})
def _derive_weight(w):
    """Accende i tetti d'istituto sui valori osservati nel testimone. Senza
    questo, il banco proverebbe un builder spento."""
    from domain.models import InstituteSettings
    grid = w.env["grid"]
    per_day, per_half, per_week = defaultdict(int), defaultdict(int), defaultdict(int)
    for aid, (day, slot) in w.placement.items():
        act = w.act(aid)
        peso = act.subject.didactic_weight * act.duration_slots
        meta = slot >= grid.morning_end_slot
        for key in w.tokens[aid]:
            per_day[(key, day)] += peso
            per_half[(key, day, meta)] += peso
            per_week[key] += peso
    settings, _ = InstituteSettings.objects.get_or_create(pk=1)
    settings.max_weight_day = max(per_day.values(), default=0)
    settings.max_weight_morning = max(
        (v for (_k, _d, m), v in per_half.items() if not m), default=0)
    settings.max_weight_afternoon = max(
        (v for (_k, _d, m), v in per_half.items() if m), default=0)
    settings.max_weight_week = max(per_week.values(), default=0)
    settings.save()
```

⚠ Il derivatore somma su **tutti** i token, non solo sulle unità-studente:
è una sovrastima, quindi produce tetti più larghi di quelli osservati. Va
bene — un tetto più largo è comunque soddisfatto dal testimone, e il punto 3
di `run_family` resta capace di scoprire un builder troppo permissivo.

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_weight.py -q`
Expected: PASS (7 test)

Run: `venv/bin/pytest -q`
Expected: **339 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/weight.py domain/solver/builders/__init__.py tests/solver_harness.py tests/test_solver_weight.py
git commit -m "$(cat <<'EOF'
feat(solver): structural:didactic_weight

Peso x durata per unita' studente, con il tetto settimanale della classe
che prevale su quello d'istituto. In una base reale i quattro tetti sono
tutti spenti, quindi di norma questo builder non posta nulla: c'e' un test
che lo verifica, cosi' il silenzio non sembra un bug.

Con questo il registro dei builder e' completo: ventisei chiavi su
ventisette, e la ventisettesima (structural:coverage) non ne ha una per
costruzione.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 7 — Il Fermi

### Task 17: La misura, la diagnosi se cade, e la documentazione

**Files:**
- Modify: `tests/test_solver_oracle.py` (il Fermi con tutti i vincoli)
- Create: `tests/test_solver_registry_completo.py`
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md`
  (una nota di chiusura con i numeri misurati)

**Interfaces:** nessuna nuova.

- [ ] **Step 1: Il test che fissa la copertura del registro**

```python
# tests/test_solver_registry_completo.py
"""Il registro dei builder, a modello completo. Fissa due numeri e una
assenza deliberata, cosi' che un builder aggiunto o perso si veda."""
import pytest

from domain.analysis.registry import REGISTRY as CHECKERS
from domain.solver import builders  # noqa: F401
from domain.solver.registry import BUILDERS

pytestmark = pytest.mark.django_db


def test_ogni_builder_ha_un_checker_con_la_stessa_chiave():
    """«Una riga di dato, due facce»: le chiavi dei builder sono un
    sottoinsieme di quelle dei checker, mai un insieme diverso."""
    orfani = sorted(str(k) for k in BUILDERS if k not in CHECKERS)
    assert orfani == []


def test_structural_coverage_non_ha_un_builder_ed_e_voluto():
    """CoverageChecker e' PLACEMENT_INDEPENDENT: confronta attivita' e servizi
    anagrafici e non guarda mai i piazzamenti. Il solver non crea ne'
    distrugge attivita', quindi non c'e' nulla da vincolare.

    Questo test esiste perche' l'assenza sia **dichiarata** invece che
    sembrare una dimenticanza: se qualcuno aggiungesse un builder per questa
    chiave, dovrebbe prima cancellare questo test — e leggerne il perche'."""
    assert "structural:coverage" in CHECKERS
    assert "structural:coverage" not in BUILDERS


def test_il_registro_dei_builder_e_completo():
    mancanti = sorted(str(k) for k in CHECKERS
                      if k not in BUILDERS and k != "structural:coverage")
    assert mancanti == []
```

- [ ] **Step 2: Eseguire**

Run: `venv/bin/pytest tests/test_solver_registry_completo.py -v`
Expected: PASS (3 test). Se `test_il_registro_dei_builder_e_completo`
fallisce, un builder delle ondate 3–6 non è stato registrato o importato in
`builders/__init__.py`.

- [ ] **Step 3: Estendere l'insieme `CODICI` dell'oracolo del Fermi**

In `tests/test_solver_oracle.py`, sostituire l'insieme `CODICI` — che oggi
elenca le sole cinque famiglie dello spike — con **tutte** le causali `HARD`
delle famiglie modellate:

```python
# le causali delle ventisei famiglie modellate. structural:coverage non c'e':
# non ha un builder, e il solver non puo' violarlo (vedi
# tests/test_solver_registry_completo.py)
CODICI = {
    # strutturali
    "resource_occupied", "resource_occupied_locked", "resource_peak",
    "unavailability", "slot_out_of_grid", "break_straddled", "holiday",
    "site_transition",
    "weight_day", "weight_morning", "weight_afternoon", "weight_week",
    # orari
    "min_distribution", "max_hours_day", "max_hours_morning",
    "max_hours_afternoon", "max_presence", "max_presence_days",
    "arrival_departure", "free_guaranteed", "max_half_days", "only_half_day",
    "max_site_changes", "max_gap",
    # materia
    "subject_same_half_day", "subject_same_day", "subject_two_days",
    "subject_forbidden_sequence", "subject_max_hours_half_day",
    "subject_max_hours_day", "subject_weekly_order",
    "subject_imposed_succession", "subject_half_day_gap",
    "subject_parts_order",
}
```

- [ ] **Step 4: Eseguire il Fermi e registrare la misura**

Run: `venv/bin/pytest tests/test_solver_oracle.py::test_fermi_intero_misurato -q -s`

Il test stampa già `status` e `stats`. **Annotare i quattro numeri**: attività,
variabili, constraint, secondi — e lo stato.

- [ ] **Step 5: Se il Fermi risponde `INFEASIBLE`, diagnosticare**

Non è un fallimento: è la risposta prevista dalla spec §1.3, ed è la ragione
per cui il pezzo 3 (alleggerimenti) esiste. Da fare, in quest'ordine:

```bash
venv/bin/python manage.py analyze
```

e poi restringere per famiglia, disattivando temporaneamente un builder per
volta con un `pytest` mirato che costruisce il modello senza quella chiave:

```python
# script usa-e-getta, NON da committare
from domain.solver.registry import BUILDERS
from domain.solver.model import solve
sospese = {}
for chiave in list(BUILDERS):
    sospese[chiave] = BUILDERS.pop(chiave)
    print(chiave, solve(schedule, time_limit=60).status)
    BUILDERS[chiave] = sospese.pop(chiave)
```

Il risultato da riportare è **il nome della famiglia** che rende infattibile
l'istanza, non «INFEASIBLE».

- [ ] **Step 6: Aggiornare `CLAUDE.md`**

Nella struttura dei documenti, sostituire la riga di `domain/solver/` con:

```
  solver/               il modello CP-SAT: vocabolario di variabili derivate,
                        residuo di ADR-018, ventisei builder su ventisette
```

Nella nota di stato, sostituire il paragrafo che dice «cinque vincoli su
ventisette» con la descrizione del modello completo, i numeri misurati allo
Step 4, e il rimando ai tre pezzi che restano (aule, alleggerimenti +
lessicografico, violatore di Hall).

Aggiungere una voce di changelog datata che racconti, nell'ordine: il
vocabolario e perché esiste; ADR-018 nelle sue tre forme (tetto, minimo,
implicazione) e la scoperta di `frozen_occupies`; il generatore a testimone e
perché rende impossibile un oracolo vacuo; le **due trappole trovate leggendo
i checker** (`FREE_GUARANTEED` che conta le mezze giornate libere solo sui
giorni con attività, `MAX_PRESENCE` che usa la giornata intera dove il D.T.B.
usa la mezza); i due conservativi con la loro direzione; e la misura del Fermi
con l'esito della diagnosi se è caduto.

- [ ] **Step 7: Chiudere la spec**

In coda a `docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md`,
aggiungere una sezione «§9 — Esito», con: i numeri del Fermi, quali famiglie
sono risultate esatte e quali conservative **a consuntivo** (il bilancio di
§4.5 era una previsione), e ogni scostamento fra spec e implementazione, con
la ragione.

- [ ] **Step 8: Eseguire tutto un'ultima volta**

Run: `venv/bin/pytest -q`
Expected: **342 passed** (339 + 3)

- [ ] **Step 9: Commit**

```bash
git add tests/test_solver_registry_completo.py tests/test_solver_oracle.py CLAUDE.md docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md
git commit -m "$(cat <<'EOF'
feat(solver): il modello hard completo, e la misura sul Fermi

L'oracolo del Fermi ora copre tutte le famiglie modellate, non le cinque
dello spike. Il registro e' fissato da un test: ventisei builder su
ventisette checker, e l'assenza del ventisettesimo e' dichiarata invece
che silenziosa.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Nota per chi esegue

**Tre modi di fallire, e dicono cose diverse.** `run_family` distingue
apposta: fallimento al punto 1 = il **derivatore** ha creato una riga che il
testimone non soddisfa; al punto 2 (`INFEASIBLE`) = il **builder è troppo
stretto** oltre quanto la spec consenta; al punto 3 = il **builder è troppo
largo**, e accetta ciò che il checker boccia. Solo il terzo è un difetto di
correttezza; il secondo di solito è una svista nel derivatore che ha reso il
vincolo più duro del testimone.

**Se un numero di test atteso non torna**, non inseguirlo: i conteggi in
questo piano sono indicativi e dipendono da quanti seed sopravvivono ai
derivatori che si astengono (diversi creano righe solo se il testimone offre
un caso adatto). Ciò che deve tornare è che **nessun test sia rosso** e che il
totale non **diminuisca** fra un task e il successivo.

**Non aggiungere un test di equivalenza modello ⟺ checker.** Fallirebbe
legittimamente su `HALF_DAY_GAP` e `site_transition`, che sono conservativi
per decisione (spec §1.2 e §5.5).
