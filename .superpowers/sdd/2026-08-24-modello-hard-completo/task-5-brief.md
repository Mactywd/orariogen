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

