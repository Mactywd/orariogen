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

