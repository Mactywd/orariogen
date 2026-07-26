# Analisi dei vincoli — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Il sottosistema di analisi del dominio v1 — predicati con causali nominate, dominio residuo (`S.P.`/`Nr G.`), aritmetica di capienza e comando `manage.py analyze` — dalla spec approvata [2026-07-26-analisi-vincoli-design.md](../specs/2026-07-26-analisi-vincoli-design.md).

**Architecture:** Package `domain/analysis/` (codice puro, nessuna migrazione): un registro mappa ogni tipo di vincolo dello schema a un checker (predicato + causale); i predicati girano su uno `ScheduleState` in memoria costruito per settimana; i findings sono dataclass mai persistite. Il dominio residuo è piazzamento di prova + delta di violazioni hard; la capienza è l'ottimo esatto di un rilassamento (verdetto mai falso-positivo).

**Tech Stack:** Django ≥5.1, pytest + pytest-django, SQLite. Nessuna dipendenza nuova.

## Global Constraints

- **Prosa (docstring, commenti, messaggi, commit) in italiano; identificatori in inglese.** Sui gruppi solo `partition` / `part` / `group`.
- **Findings mai su DB** (principio 2 del design): dataclass, nessun nuovo modello, **nessuna migrazione** in tutto il piano.
- **L'orario invalido è ammesso** (principio 3): nessun predicato impedisce nulla — descrive.
- **Esattezza**: la capienza non deve mai sottostimare il piazzabile (solo rilassamenti); un verdetto negativo è una dimostrazione.
- **`InstituteSettings.load()` scrive alla prima lettura** (get_or_create): nei percorsi di sola lettura dell'analisi usare `InstituteSettings.objects.filter(pk=1).first() or InstituteSettings()`.
- Test con `venv/bin/pytest`. Se `venv/` manca: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`.
- Prima di ogni `git add`: controllare `git status` e non aggiungere mai `__pycache__/` o `db.sqlite3`.
- Prefissi commit: `feat(analysis):`, `test:`, `docs:`.
- Messaggi delle causali: frasi italiane dal catalogo EDT ([diagnostica.md](../../edt/diagnostica.md)), solo i codici davvero emessi dai checker.

## Struttura dei file (a fine piano)

```
domain/analysis/__init__.py        vuoto
domain/analysis/findings.py        Severity, Finding                     (Task 1)
domain/analysis/causali.py         CAUSALI, message()                    (Task 1)
domain/analysis/state.py           Placed, activity_tokens, ScheduleState (Task 2)
domain/analysis/registry.py        Checker, register, REGISTRY, all_checkers (Task 3)
domain/analysis/conformity.py      week_signatures, check_schedule       (Task 3)
domain/analysis/checkers/__init__.py                                     (Task 3, esteso dopo)
domain/analysis/checkers/occupation.py                                   (Task 3)
domain/analysis/checkers/unavailability.py                               (Task 3)
domain/analysis/checkers/grid.py                                         (Task 4)
domain/analysis/checkers/sites.py                                        (Task 4)
domain/analysis/checkers/time_constraints.py   8 tipi                    (Task 5)
domain/analysis/checkers/subject_constraints.py 13 tipi                  (Task 6)
domain/analysis/checkers/weight.py                                       (Task 7)
domain/analysis/checkers/coverage.py                                     (Task 7)
domain/analysis/domain_size.py     DomainSize, residual_domain           (Task 8)
domain/analysis/capacity.py        CapacityFinding, analyze_capacity     (Task 9)
domain/management/__init__.py, commands/__init__.py, commands/analyze.py (Task 10)
tests/analysis_helpers.py          mini_school, make_activity, place     (Task 2)
tests/test_analysis_findings.py                                          (Task 1)
tests/test_analysis_state.py                                             (Task 2)
tests/test_analysis_conformity.py                                        (Task 3, esteso in 4)
tests/test_analysis_time_constraints.py                                  (Task 5)
tests/test_analysis_subject_constraints.py                               (Task 6)
tests/test_analysis_weight_coverage.py + completezza                     (Task 7)
tests/test_analysis_domain_size.py                                       (Task 8)
tests/test_analysis_capacity.py    diagnosi EDT A e B                    (Task 9)
tests/test_analyze_command.py                                            (Task 10)
tests/test_fermi_constraints.py    Fermi arricchito                      (Task 11)
tests/test_constraint_negatives.py code del piano 1                      (Task 12)
```

Convenzione condivisa (usata ovunque, definita qui una volta): **le chiavi di
occupazione sono pk di `Resource`**. Con la multi-table inheritance
`Teacher.pk == Resource.pk`, quindi i pk dei modelli concreti sono direttamente
chiavi valide. La regola dei conflitti sulle unità: la classe intera occupa sé
stessa **e tutte le sue parti**; la parte occupa **solo sé stessa**; il
raggruppamento occupa **le parti membre**. Parti di partizioni diverse della
stessa classe **non** confliggono (regola v1 dichiarata nella spec).

---

### Task 1: Findings e catalogo delle causali

**Files:**
- Create: `domain/analysis/__init__.py` (vuoto), `domain/analysis/findings.py`, `domain/analysis/causali.py`
- Test: `tests/test_analysis_findings.py`

**Interfaces:**
- Produces: `Severity` (StrEnum: HARD/OPTIONAL/PREFERENCE), `Finding(code, message, severity, resources=(), activities=(), quantities={}, weeks=())` con property `key`; `causali.CAUSALI: dict[str, str]`, `causali.message(code, **kwargs) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_findings.py
"""Findings: la forma del verdetto. Mai persistiti (principio 2)."""
import re

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity


def _finding(**overrides):
    base = dict(
        code="subject_same_day",
        message="Italiano, troppe attività nella giornata",
        severity=Severity.HARD,
        resources=(3,),
        activities=(7, 9),
        quantities={"day": 2, "count": 2},
    )
    base.update(overrides)
    return Finding(**base)


def test_finding_key_ignora_il_messaggio_e_le_settimane():
    a = _finding()
    b = _finding(message="altro testo", weeks=(0, 1))
    assert a.key == b.key


def test_finding_key_distingue_le_quantita():
    assert _finding().key != _finding(quantities={"day": 3, "count": 2}).key


def test_message_formatta_i_nomi():
    msg = causali.message("unavailability", resource="ROSSI")
    assert msg == "ROSSI ha una indisponibilità"


def test_tutte_le_causali_usano_solo_segnaposto_noti():
    ammessi = {"resource", "subject", "unit"}
    for code, template in causali.CAUSALI.items():
        campi = set(re.findall(r"{(\w+)}", template))
        assert campi <= ammessi, f"{code}: segnaposto {campi - ammessi}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_analysis_findings.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis'`

- [ ] **Step 3: Write minimal implementation**

`domain/analysis/__init__.py`: file vuoto.

```python
# domain/analysis/findings.py
"""Il verdetto dell'analisi: dataclass mai persistite (principio 2 del design).
Ogni finding porta la causale, la frase italiana già formattata e le quantità
— il verdetto è un numero verificabile, non un aggettivo."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class Severity(StrEnum):
    HARD = "hard"            # rosso
    OPTIONAL = "optional"    # giallo: violabile solo con override globale
    PREFERENCE = "preference"  # verde


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Severity
    resources: tuple[int, ...] = ()    # pk delle Resource coinvolte
    activities: tuple[int, ...] = ()   # pk delle Activity coinvolte
    quantities: Mapping[str, int] = field(default_factory=dict)
    weeks: tuple[int, ...] = ()        # settimane in cui la violazione vale

    @property
    def key(self):
        """Identità per il dedup fra firme di settimana: messaggio e settimane
        esclusi apposta."""
        return (self.code, self.resources, self.activities,
                tuple(sorted(self.quantities.items())))
```

```python
# domain/analysis/causali.py
"""Il catalogo delle causali nominate: codice → frase italiana, ripreso quasi
alla lettera dal catalogo EDT (AffSco_UtilDiagnostic, docs/edt/diagnostica.md).
Solo i codici che i checker emettono davvero. Segnaposto ammessi:
{resource}, {subject}, {unit}."""

CAUSALI: dict[str, str] = {
    # occupazione (Task 3)
    "resource_occupied": "{resource} è già occupata in un'attività",
    "resource_occupied_locked": "{resource} è già occupata in un'attività bloccata",
    "resource_peak": "{resource} ha raggiunto il suo picco d'occupazione",
    # indisponibilità (Task 3)
    "unavailability": "{resource} ha una indisponibilità",
    "unavailability_optional": "{resource} ha un'indisponibilità opzionale",
    "preference": "{resource} ha una preferenza",
    # griglia e sedi (Task 4)
    "slot_out_of_grid": "L'attività esce dalla griglia oraria",
    "break_straddled": "Intervallo non rispettato",
    "holiday": "Giorno festivo",
    "site_transition": "Tempo insufficiente per il trasferimento di sede",
    # vincoli orari sulla risorsa (Task 5)
    "min_distribution": "{resource}, distribuzione minima non rispettata",
    "max_hours_day": "{resource}, massimo di ore nella giornata superato",
    "max_hours_morning": "{resource}, massimo di ore nella mattinata superato",
    "max_hours_afternoon": "{resource}, massimo di ore nel pomeriggio superato",
    "max_presence": "Massimo di ore di presenza superato",
    "max_presence_days": "Massimo di giorni di presenza superato",
    "arrival_departure": "{resource} non rispetta le entrate/uscite richieste",
    "free_guaranteed": "{resource} non ha più giorni e 1/2 giornate libere",
    "max_half_days": "Massimo di 1/2 giornate di lavoro superate",
    "only_half_day": "{resource} lavora entrambe le mezze giornate",
    "max_site_changes": "Numero di cambi di sede superiore al limite fissato",
    "max_gap": "Durata tollerata dei buchi superata",
    # vincoli di materia (Task 6)
    "subject_same_half_day": "{subject}, troppe attività nella mezza giornata",
    "subject_same_day": "{subject}, troppe attività nella giornata",
    "subject_two_days": "{subject}, troppe attività su 2 giorni",
    "subject_forbidden_sequence": "{subject}, sequenza indesiderata di attività",
    "subject_max_hours_half_day": "{subject}, troppe ore nella mezza giornata",
    "subject_max_hours_day": "{subject}, troppe ore nella giornata",
    "subject_weekly_order": "{subject}, ordine settimanale non rispettato",
    "subject_imposed_succession": "{subject}, sequenza imposta non rispettata",
    "subject_half_day_gap": "{subject}, numero di mezze giornate insufficiente",
    "subject_parts_order": ("{subject}, ordine delle attività in gruppo rispetto "
                            "alle attività a classe intera non rispettato"),
    # peso didattico e copertura (Task 7)
    "weight_day": "Limite dei pesi didattici superato nella giornata",
    "weight_morning": "Limite dei pesi didattici superato nella mattinata",
    "weight_afternoon": "Limite dei pesi didattici superato nel pomeriggio",
    "weight_week": "Limite settimanale dei pesi didattici superato",
    "coverage_mismatch": "{unit}, {subject}: monte ore delle attività diverso dal servizio",
}


def message(code: str, **kwargs) -> str:
    return CAUSALI[code].format(**kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_findings.py -v`
Expected: 4 PASS. Poi l'intera suite: `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/__init__.py domain/analysis/findings.py domain/analysis/causali.py tests/test_analysis_findings.py
git commit -m "feat(analysis): findings e catalogo delle causali"
```

---

### Task 2: ScheduleState — lo snapshot in memoria

**Files:**
- Create: `domain/analysis/state.py`, `tests/analysis_helpers.py`
- Test: `tests/test_analysis_state.py`

**Interfaces:**
- Consumes: modelli `domain.models`, `domain.weeks`.
- Produces: `activity_tokens(activity, assigned_room_id=None) -> (frozenset[int], dict[int, int])`; `Placed(activity_id, day, start_slot, slots)`; `ScheduleState` con attributi `schedule, grid, week, settings, activities, placed, occupancy, tokens, material_quantity, capacity, kinds, resource_names, unavailability, holidays, n_weeks`, classmethod `build(schedule, week=0)`, metodi `place(activity, day, start_slot)`, `unplace(activity_id)`, `resource_days(key) -> dict[int, list[int]]`. Helper di test `mini_school() -> dict`, `make_activity(...)`, `place(schedule, activity, day, slot, room=None)`.

- [ ] **Step 1: Write the test helpers**

```python
# tests/analysis_helpers.py
"""Fixture minima per i test dell'analisi: una scuola giocattolo con griglia
5×6, anno di 4 settimane, una classe, un docente, una materia."""
import datetime as dt

from domain import weeks
from domain.models import (
    Activity, Discipline, Period, Placement, Schedule, SchoolClass, SchoolYear,
    StudyPlan, Subject, Teacher, TimeGrid,
)

N_WEEKS = 4
FULL = weeks.full_mask(N_WEEKS)


def mini_school():
    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4
    )
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 10, 11),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1",
        start_date=year.start_date, end_date=year.end_date,
    )
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    return {
        "grid": grid, "year": year, "period": period, "schedule": schedule,
        "discipline": disc, "subject": subject, "plan": plan,
        "klass": klass, "teacher": teacher,
    }


def make_activity(subject, *, teachers=(), classes=(), parts=(), groups=(),
                  rooms=(), slots=1, mask=FULL, **flags):
    a = Activity.objects.create(
        subject=subject, duration_slots=slots, duration_minutes=slots * 60,
        week_mask=mask, **flags,
    )
    for t in teachers:
        a.teachers.add(t)
    for c in classes:
        a.classes.add(c)
    for p in parts:
        a.parts.add(p)
    for g in groups:
        a.groups.add(g)
    for r in rooms:
        a.rooms.add(r)
    return a


def place(schedule, activity, day, slot, room=None):
    return Placement.objects.create(
        schedule=schedule, activity=activity, day=day, start_slot=slot,
        assigned_room=room,
    )
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_analysis_state.py
"""ScheduleState: la regola dei conflitti sulle unità e la meccanica del
piazzamento di prova."""
import datetime as dt

import pytest

from domain.analysis.state import ScheduleState, activity_tokens
from domain.models import ClassPart, ClassPartition, Group, ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _with_parts(env):
    partition = ClassPartition.objects.create(school_class=env["klass"], name="LINGUE")
    p1 = ClassPart.objects.create(name="1A-fra", partition=partition)
    p2 = ClassPart.objects.create(name="1A-spa", partition=partition)
    return p1, p2


def test_classe_intera_occupa_se_stessa_e_le_parti():
    env = mini_school()
    p1, p2 = _with_parts(env)
    a = make_activity(env["subject"], classes=[env["klass"]])
    keys, _ = activity_tokens(a)
    assert keys == {env["klass"].pk, p1.pk, p2.pk}


def test_la_parte_occupa_solo_se_stessa():
    env = mini_school()
    p1, p2 = _with_parts(env)
    a = make_activity(env["subject"], parts=[p1])
    keys, _ = activity_tokens(a)
    assert keys == {p1.pk}


def test_il_raggruppamento_occupa_le_parti_membre():
    env = mini_school()
    p1, p2 = _with_parts(env)
    g = Group.objects.create(name="G-LINGUE")
    g.parts.add(p1, p2)
    a = make_activity(env["subject"], groups=[g])
    keys, _ = activity_tokens(a)
    assert keys == {p1.pk, p2.pk}


def test_build_indicizza_i_piazzamenti():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    place(env["schedule"], a, day=1, slot=2)
    state = ScheduleState.build(env["schedule"])
    assert state.placed[a.id].slots == (2,)
    assert state.occupancy[(env["teacher"].pk, 1, 2)] == [a.id]
    assert state.resource_days(env["klass"].pk) == {1: [2]}


def test_place_unplace_e_reversibile():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    state = ScheduleState.build(env["schedule"])
    state.place(a, day=0, start_slot=3)
    assert state.occupancy[(env["klass"].pk, 0, 4)] == [a.id]
    state.unplace(a.id)
    assert (env["klass"].pk, 0, 4) not in state.occupancy
    assert a.id not in state.placed


def test_attivita_fuori_settimana_esclusa():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], mask=0b0010)
    place(env["schedule"], a, day=0, slot=0)
    assert a.id not in ScheduleState.build(env["schedule"], week=0).activities
    assert a.id in ScheduleState.build(env["schedule"], week=1).activities


def test_indisponibilita_con_data_mappa_sulla_settimana():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=2, slot=0, level="hard",
        date=dt.date(2026, 9, 23),  # mercoledì della settimana 1
    )
    assert (env["teacher"].pk, 2, 0) not in ScheduleState.build(env["schedule"], week=0).unavailability
    state = ScheduleState.build(env["schedule"], week=1)
    assert state.unavailability[(env["teacher"].pk, 2, 0)] == "hard"


def test_livello_piu_severo_vince():
    env = mini_school()
    ResourceUnavailability.objects.create(resource=env["teacher"], day=0, slot=0, level="preference")
    ResourceUnavailability.objects.create(resource=env["teacher"], day=0, slot=0, level="hard")
    state = ScheduleState.build(env["schedule"])
    assert state.unavailability[(env["teacher"].pk, 0, 0)] == "hard"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_state.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.state'`

- [ ] **Step 4: Write the implementation**

```python
# domain/analysis/state.py
"""Lo snapshot in memoria di uno Schedule per una settimana data. Costruito
una volta dal DB, poi interrogato (e mutato dai piazzamenti di prova) dai
checker in millisecondi. Le chiavi di occupazione sono pk di Resource
(con la MTI, Teacher.pk == Resource.pk)."""

from collections import defaultdict
from dataclasses import dataclass

from domain import weeks
from domain.models import (
    Activity, ClassPart, Holiday, InstituteSettings, Resource,
    ResourceUnavailability, TimeGrid,
)

_SEVERITY_ORDER = {"hard": 0, "optional": 1, "preference": 2}


def activity_tokens(activity, assigned_room_id=None):
    """Chiavi di occupazione e quantità dei materiali di un'attività.
    Regola dei conflitti sulle unità (v1): la classe intera occupa sé stessa
    e tutte le sue parti; la parte occupa solo sé stessa; il raggruppamento
    occupa le parti membre. Parti di partizioni diverse non confliggono."""
    keys, materials = set(), {}
    for t in activity.teachers.all():
        keys.add(t.pk)
    for c in activity.classes.all():
        keys.add(c.pk)
        keys.update(ClassPart.objects.filter(
            partition__school_class=c).values_list("pk", flat=True))
    for p in activity.parts.all():
        keys.add(p.pk)
    for g in activity.groups.all():
        keys.update(g.parts.values_list("pk", flat=True))
    if assigned_room_id is not None:
        keys.add(assigned_room_id)
    else:
        keys.update(r.pk for r in activity.rooms.all())
    for s in activity.staff.all():
        keys.add(s.pk)
    for req in activity.material_requirements.all():
        keys.add(req.material_id)
        materials[req.material_id] = req.quantity
    return frozenset(keys), materials


@dataclass(frozen=True)
class Placed:
    activity_id: int
    day: int
    start_slot: int
    slots: tuple[int, ...]


class ScheduleState:
    def __init__(self, schedule, grid, week, settings):
        self.schedule = schedule
        self.grid = grid
        self.week = week
        self.settings = settings
        self.activities = {}          # id → Activity (attive nella settimana)
        self.placed = {}              # id → Placed
        self.occupancy = defaultdict(list)  # (chiave, giorno, fascia) → [activity_id]
        self.tokens = {}              # id → frozenset di chiavi
        self.material_quantity = {}   # (activity_id, chiave) → quantità
        self.capacity = {}            # chiave → capacità simultanea
        self.kinds = {}               # chiave → Resource.Kind
        self.resource_names = {}      # chiave → nome
        self.unavailability = {}      # (chiave, giorno, fascia) → livello più severo
        self.holidays = set()         # giorni festivi di questa settimana
        self.n_weeks = 1

    @classmethod
    def build(cls, schedule, week=0):
        grid = TimeGrid.objects.first()
        settings = InstituteSettings.objects.filter(pk=1).first() or InstituteSettings()
        state = cls(schedule, grid, week, settings)

        for r in Resource.objects.values("id", "name", "kind", "simultaneous_capacity"):
            state.resource_names[r["id"]] = r["name"]
            state.kinds[r["id"]] = r["kind"]
            state.capacity[r["id"]] = r["simultaneous_capacity"]

        placements = {p.activity_id: p for p in schedule.placements.all()}
        acts = (Activity.objects
                .exclude(immobility=Activity.Immobility.SUSPENDED)
                .select_related("subject", "site")
                .prefetch_related("teachers", "classes", "parts", "groups",
                                  "rooms", "staff", "material_requirements"))
        for a in acts:
            if not weeks.week_in_mask(a.week_mask, week):
                continue
            state.activities[a.id] = a
            pl = placements.get(a.id)
            keys, materials = activity_tokens(
                a, assigned_room_id=pl.assigned_room_id if pl else None)
            state.tokens[a.id] = keys
            for k, q in materials.items():
                state.material_quantity[(a.id, k)] = q
            if pl is not None:
                state.place(a, pl.day, pl.start_slot)

        year = schedule.period.school_year
        state.n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
        for u in ResourceUnavailability.objects.all():
            day = u.day
            if u.date is not None:
                delta = (u.date - year.first_week_monday).days
                if delta // 7 != week:
                    continue
                day = delta % 7
            key = (u.resource_id, day, u.slot)
            current = state.unavailability.get(key)
            if current is None or _SEVERITY_ORDER[u.level] < _SEVERITY_ORDER[current]:
                state.unavailability[key] = u.level
        for h in Holiday.objects.filter(school_year=year):
            delta = (h.date - year.first_week_monday).days
            if delta // 7 == week and 0 <= delta % 7 < grid.days_per_cycle:
                state.holidays.add(delta % 7)
        return state

    def place(self, activity, day, start_slot):
        slots = tuple(range(start_slot, start_slot + activity.duration_slots))
        self.placed[activity.id] = Placed(activity.id, day, start_slot, slots)
        for key in self.tokens[activity.id]:
            for s in slots:
                self.occupancy[(key, day, s)].append(activity.id)

    def unplace(self, activity_id):
        pl = self.placed.pop(activity_id)
        for key in self.tokens[activity_id]:
            for s in pl.slots:
                cell = self.occupancy[(key, pl.day, s)]
                cell.remove(activity_id)
                if not cell:
                    del self.occupancy[(key, pl.day, s)]

    def resource_days(self, key):
        """giorno → fasce occupate ordinate, per una chiave di occupazione."""
        out = defaultdict(set)
        for (k, day, slot), acts in self.occupancy.items():
            if k == key and acts:
                out[day].add(slot)
        return {d: sorted(s) for d, s in sorted(out.items())}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_state.py -v`
Expected: 8 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 6: Commit**

```bash
git add domain/analysis/state.py tests/analysis_helpers.py tests/test_analysis_state.py
git commit -m "feat(analysis): ScheduleState, lo snapshot in memoria per settimana"
```

---

### Task 3: Registro, conformità, occupazione e indisponibilità

**Files:**
- Create: `domain/analysis/registry.py`, `domain/analysis/conformity.py`, `domain/analysis/checkers/__init__.py`, `domain/analysis/checkers/occupation.py`, `domain/analysis/checkers/unavailability.py`
- Test: `tests/test_analysis_conformity.py`

**Interfaces:**
- Consumes: `Finding`, `Severity`, `causali.message`, `ScheduleState`, helper di test del Task 2.
- Produces: `Checker` (base, metodo `check(self, state, resources=None)`); `register(*keys)` decoratore; `REGISTRY: dict`; `all_checkers() -> list[Checker]`; `week_signatures(schedule) -> list[tuple[int, tuple[int, ...]]]`; `check_schedule(schedule) -> list[Finding]`. Chiavi di registro: `"structural:<nome>"` per i checker non-enum, i valori enum stessi per i tipi (Task 5 e 6).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_conformity.py
"""Conformità: occupazione, indisponibilità e la fusione per firme di settimana."""
import pytest

from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.models import Material, ResourceUnavailability
from domain.models.activities import ActivityMaterialRequirement
from tests.analysis_helpers import FULL, make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_orario_pulito_nessun_finding():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    assert check_schedule(env["schedule"]) == []


def test_doppia_occupazione_del_docente():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["resource_occupied"]
    f = findings[0]
    assert f.severity == Severity.HARD
    assert f.resources == (env["teacher"].pk,)
    assert set(f.activities) == {a.id, b.id}
    assert f.quantities["load"] == 2 and f.quantities["capacity"] == 1
    assert f.weeks == (0, 1, 2, 3)  # annuale: la violazione vale ogni settimana


def test_occupante_bloccato_cambia_causale():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], immobility="fixed")
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert check_schedule(env["schedule"])[0].code == "resource_occupied_locked"


def test_maschere_disgiunte_non_confliggono():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b0011)
    b = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b1100)
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert check_schedule(env["schedule"]) == []


def test_picco_materiale_oltre_capacita():
    env = mini_school()
    carrello = Material.objects.create(name="Portatili", simultaneous_capacity=10)
    a = make_activity(env["subject"])
    b = make_activity(env["subject"])
    ActivityMaterialRequirement.objects.create(activity=a, material=carrello, quantity=6)
    ActivityMaterialRequirement.objects.create(activity=b, material=carrello, quantity=6)
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["resource_peak"]
    assert findings[0].quantities["load"] == 12


def test_indisponibilita_tre_livelli():
    env = mini_school()
    for day, level in [(0, "hard"), (1, "optional"), (2, "preference")]:
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=day, slot=0, level=level)
        act = make_activity(env["subject"], teachers=[env["teacher"]])
        place(env["schedule"], act, day=day, slot=0)
    by_code = {f.code: f for f in check_schedule(env["schedule"])}
    assert by_code["unavailability"].severity == Severity.HARD
    assert by_code["unavailability_optional"].severity == Severity.OPTIONAL
    assert by_code["preference"].severity == Severity.PREFERENCE


def test_firme_di_settimana():
    env = mini_school()
    annuale = make_activity(env["subject"], teachers=[env["teacher"]], mask=FULL)
    una_tantum = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b0100)
    place(env["schedule"], annuale, day=0, slot=0)
    place(env["schedule"], una_tantum, day=0, slot=1)
    sigs = week_signatures(env["schedule"])
    reps = sorted(wks for _, wks in sigs)
    assert reps == [(0, 1, 3), (2,)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_conformity.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.conformity'`

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/registry.py
"""Il registro dei checker: la struttura in cui «ogni vincolo esiste due
volte» (principio 4). Ogni tipo di vincolo dello schema ha una voce; il
piano CP-SAT aggancerà il builder alla stessa voce."""


class Checker:
    """`check()` produce i findings sullo stato. `resources`, se dato, è un
    filtro di ottimizzazione: il checker può saltare il lavoro sulle risorse
    fuori dall'insieme, ma i findings che le toccano devono restare completi."""

    def check(self, state, resources=None):
        raise NotImplementedError


REGISTRY = {}


def register(*keys):
    def decorator(cls):
        for key in keys:
            REGISTRY[key] = cls
        return cls
    return decorator


def all_checkers():
    from domain.analysis import checkers  # noqa: F401 — forza la registrazione
    out, seen = [], set()
    for cls in REGISTRY.values():
        if cls not in seen:
            seen.add(cls)
            out.append(cls())
    return out
```

```python
# domain/analysis/checkers/__init__.py
"""L'import registra i checker nel REGISTRY. Esteso dai task successivi."""
from . import occupation, unavailability  # noqa: F401
```

```python
# domain/analysis/checkers/occupation.py
"""Risorsa occupata e capacità cumulativa: un solo meccanismo per aule con
Qtà > 1 e materiali con quantità (una risorsa cumulativa sola)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import Activity

_LOCKED = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


@register("structural:occupation")
class OccupationChecker(Checker):
    def check(self, state, resources=None):
        for (key, day, slot), acts in sorted(state.occupancy.items()):
            if resources is not None and key not in resources:
                continue
            load = sum(state.material_quantity.get((aid, key), 1) for aid in acts)
            cap = state.capacity.get(key, 1)
            if load <= cap:
                continue
            locked = any(state.activities[a].immobility in _LOCKED for a in acts)
            code = ("resource_peak" if cap > 1
                    else "resource_occupied_locked" if locked
                    else "resource_occupied")
            name = state.resource_names.get(key, str(key))
            yield Finding(
                code, causali.message(code, resource=name), Severity.HARD,
                resources=(key,), activities=tuple(sorted(acts)),
                quantities={"day": day, "slot": slot, "load": load, "capacity": cap},
            )
```

```python
# domain/analysis/checkers/unavailability.py
"""I tre pennelli rosso/giallo/verde, generici sulla risorsa."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register

_CODE = {"hard": "unavailability", "optional": "unavailability_optional",
         "preference": "preference"}
_SEV = {"hard": Severity.HARD, "optional": Severity.OPTIONAL,
        "preference": Severity.PREFERENCE}
_ORDER = ["hard", "optional", "preference"]


@register("structural:unavailability")
class UnavailabilityChecker(Checker):
    def check(self, state, resources=None):
        for aid, pl in sorted(state.placed.items()):
            for key in sorted(state.tokens[aid]):
                if resources is not None and key not in resources:
                    continue
                hit = [state.unavailability[(key, pl.day, s)]
                       for s in pl.slots if (key, pl.day, s) in state.unavailability]
                if not hit:
                    continue
                level = min(hit, key=_ORDER.index)
                name = state.resource_names.get(key, str(key))
                yield Finding(
                    _CODE[level], causali.message(_CODE[level], resource=name),
                    _SEV[level], resources=(key,), activities=(aid,),
                    quantities={"day": pl.day, "slots": len(hit)},
                )
```

```python
# domain/analysis/conformity.py
"""check_schedule: valuta ogni firma di settimana distinta una volta sola e
fonde i findings identici annotando le settimane."""

from dataclasses import replace

from domain import weeks
from domain.analysis.findings import Severity
from domain.analysis.registry import all_checkers
from domain.analysis.state import ScheduleState
from domain.models import Activity, Holiday, ResourceUnavailability

_RANK = {Severity.HARD: 0, Severity.OPTIONAL: 1, Severity.PREFERENCE: 2}


def week_signatures(schedule):
    """[(settimana rappresentante, tutte le settimane con la stessa firma)].
    La firma include attività attive, indisponibilità datate e festivi."""
    year = schedule.period.school_year
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
    masks = list(Activity.objects
                 .exclude(immobility=Activity.Immobility.SUSPENDED)
                 .values_list("id", "week_mask"))
    dated = list(ResourceUnavailability.objects
                 .exclude(date=None).values_list("id", "date"))
    holidays = list(Holiday.objects.filter(school_year=year)
                    .values_list("id", "date"))

    def week_of(date):
        return (date - year.first_week_monday).days // 7

    signatures = {}
    for w in range(n_weeks):
        sig = (
            frozenset(i for i, m in masks if weeks.week_in_mask(m, w)),
            frozenset(i for i, d in dated if week_of(d) == w),
            frozenset(i for i, d in holidays if week_of(d) == w),
        )
        signatures.setdefault(sig, []).append(w)
    return [(ws[0], tuple(ws)) for ws in signatures.values()]


def check_schedule(schedule):
    merged = {}
    for representative, wks in week_signatures(schedule):
        state = ScheduleState.build(schedule, week=representative)
        for checker in all_checkers():
            for f in checker.check(state):
                if f.key in merged:
                    combined = tuple(sorted(set(merged[f.key].weeks) | set(wks)))
                    merged[f.key] = replace(merged[f.key], weeks=combined)
                else:
                    merged[f.key] = replace(f, weeks=wks)
    return sorted(merged.values(),
                  key=lambda f: (_RANK[f.severity], f.code, f.resources, f.activities))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_conformity.py -v`
Expected: 7 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/registry.py domain/analysis/conformity.py domain/analysis/checkers/ tests/test_analysis_conformity.py
git commit -m "feat(analysis): registro dei checker, conformità, occupazione e indisponibilità"
```

---

### Task 4: Checker di griglia e sedi

**Files:**
- Create: `domain/analysis/checkers/grid.py`, `domain/analysis/checkers/sites.py`
- Modify: `domain/analysis/checkers/__init__.py` (aggiungere i due import)
- Test: aggiungere a `tests/test_analysis_conformity.py`

**Interfaces:**
- Consumes: `Checker`, `register`, `Finding`, `Severity`, `causali`, `ScheduleState` (attributi `grid`, `holidays`, `settings.site_transition_slots`, `occupancy`, `resource_days`).
- Produces: checker `"structural:grid"` (fuori griglia, intervalli, festivi) e `"structural:site_transition"`.

- [ ] **Step 1: Write the failing tests** (append a `tests/test_analysis_conformity.py`)

```python
# --- Task 4: griglia e sedi ---
import datetime as dt

from domain.models import Break, Holiday, Site


def test_blocco_a_cavallo_dell_intervallo():
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=2)
    rispetta = make_activity(env["subject"], classes=[env["klass"]], slots=2,
                             respects_breaks=True)
    ignora = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    place(env["schedule"], rispetta, day=0, slot=1)   # fasce 1-2: a cavallo
    place(env["schedule"], ignora, day=1, slot=1)
    codes = [f.code for f in check_schedule(env["schedule"])]
    assert codes == ["break_straddled"]


def test_fuori_griglia():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)
    place(env["schedule"], a, day=0, slot=4)  # 4+3 > 6 fasce
    assert [f.code for f in check_schedule(env["schedule"])] == ["slot_out_of_grid"]


def test_giorno_festivo():
    env = mini_school()
    Holiday.objects.create(school_year=env["year"], date=dt.date(2026, 9, 16))  # mer, sett. 0
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=2, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["holiday"]
    assert findings[0].weeks == (0,)  # solo la settimana del festivo


def test_transizione_di_sede_troppo_stretta():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)  # nessuna fascia libera fra le due
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["site_transition"]
    assert findings[0].resources == (env["teacher"].pk,)


def test_transizione_di_sede_con_fascia_libera_ok():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=2)  # una fascia libera = default
    assert check_schedule(env["schedule"]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_conformity.py -v`
Expected: i 5 nuovi FAIL (nessun finding emesso), i 7 del Task 3 PASS.

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/checkers/grid.py
"""Vincoli della griglia: fuori griglia, intervalli (respects_breaks), festivi."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:grid")
class GridChecker(Checker):
    def check(self, state, resources=None):
        g = state.grid
        boundaries = [b.boundary_slot for b in g.breaks.all()]
        for aid, pl in sorted(state.placed.items()):
            act = state.activities[aid]
            if resources is not None and not (state.tokens[aid] & resources):
                continue
            if pl.day >= g.days_per_cycle or pl.start_slot + act.duration_slots > g.slots_per_day:
                yield Finding("slot_out_of_grid", causali.message("slot_out_of_grid"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day, "slot": pl.start_slot})
            if act.respects_breaks and any(
                    pl.start_slot < b < pl.start_slot + act.duration_slots
                    for b in boundaries):
                yield Finding("break_straddled", causali.message("break_straddled"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day, "slot": pl.start_slot})
            if pl.day in state.holidays:
                yield Finding("holiday", causali.message("holiday"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day})
```

```python
# domain/analysis/checkers/sites.py
"""Transizione fra sedi: fra due attività consecutive su sedi diverse servono
site_transition_slots fasce libere (regola semplice di ADR-015 §3)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:site_transition")
class SiteTransitionChecker(Checker):
    def check(self, state, resources=None):
        needed = state.settings.site_transition_slots
        keys = sorted({k for (k, _, _) in state.occupancy})
        for key in keys:
            if resources is not None and key not in resources:
                continue
            for day, slots in state.resource_days(key).items():
                sequence = []  # (fascia, sede, attività) per fasce con sede nota
                for s in slots:
                    for aid in state.occupancy[(key, day, s)]:
                        site = state.activities[aid].site_id
                        if site is not None:
                            sequence.append((s, site, aid))
                for (s1, site1, a1), (s2, site2, a2) in zip(sequence, sequence[1:]):
                    if site1 != site2 and s2 - s1 - 1 < needed:
                        yield Finding(
                            "site_transition", causali.message("site_transition"),
                            Severity.HARD, resources=(key,),
                            activities=tuple(sorted({a1, a2})),
                            quantities={"day": day, "gap_slots": s2 - s1 - 1,
                                        "needed_slots": needed},
                        )
```

In `domain/analysis/checkers/__init__.py`:

```python
from . import grid, occupation, sites, unavailability  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_conformity.py -v`
Expected: 12 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/checkers/ tests/test_analysis_conformity.py
git commit -m "feat(analysis): checker di griglia (intervalli, festivi) e transizione di sede"
```

---

### Task 5: Gli otto vincoli orari sulla risorsa

**Files:**
- Create: `domain/analysis/checkers/time_constraints.py`
- Modify: `domain/analysis/checkers/__init__.py` (aggiungere `time_constraints`)
- Test: `tests/test_analysis_time_constraints.py`

**Interfaces:**
- Consumes: `ResourceTimeConstraint` (8 tipi, chiavi di `params` documentate in [constraints.py](../../../domain/models/constraints.py)), `Checker`, `register`, `ScheduleState.resource_days`.
- Produces: un checker registrato per **ogni** valore di `ResourceTimeConstraint.Type` (chiave di registro = il valore enum stesso). Semantica scelta e dichiarata (da [vincoli.md](../../edt/vincoli.md)): la **presenza** è l'estensione dal primo all'ultimo slot occupato (include i buchi, ≠ attività); i **buchi** si contano **per mezza giornata** (la pausa pranzo non è mai un buco); `MAX_PRESENCE.days` = massimo di giorni con presenza, `MAX_PRESENCE.max_minutes` = massimo di presenza per giornata; `ARRIVAL_DEPARTURE.days` = numero minimo di giornate che rispettano `not_before_slot`/`not_after_slot` (le giornate vuote contano come rispettate); le mezze giornate libere di `FREE_GUARANTEED` non contano quelle dentro giornate interamente libere.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_time_constraints.py
"""Gli otto tipi di ResourceTimeConstraint, uno scenario minimo ciascuno."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import ResourceTimeConstraint, Site
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = ResourceTimeConstraint.Type


def _constraint(env, type_, params):
    return ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=type_, params=params)


def _teach(env, day, slot, slots=1):
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=slots)
    place(env["schedule"], a, day=day, slot=slot)
    return a


def _codes(env):
    return [f.code for f in check_schedule(env["schedule"])]


def test_min_distribution():
    env = mini_school()
    _constraint(env, T.MIN_DISTRIBUTION, {"min_days": 2, "min_minutes_per_day": 120})
    _teach(env, day=0, slot=0, slots=2)   # un solo giorno qualificante
    _teach(env, day=1, slot=0)            # 60' < 120'
    assert _codes(env) == ["min_distribution"]


def test_max_hours_giornata_e_mattina():
    env = mini_school()
    _constraint(env, T.MAX_HOURS, {"day_minutes": 240, "morning_minutes": 120})
    for slot in range(5):                  # 5h nello stesso giorno, 4 di mattina
        _teach(env, day=0, slot=slot)
    assert sorted(_codes(env)) == ["max_hours_day", "max_hours_morning"]


def test_max_presence_span_con_buco():
    env = mini_school()
    _constraint(env, T.MAX_PRESENCE, {"days": 5, "max_minutes": 180})
    _teach(env, day=0, slot=0)
    _teach(env, day=0, slot=4)             # presenza = fasce 0..4 = 300' > 180'
    assert _codes(env) == ["max_presence"]


def test_max_presence_giorni():
    env = mini_school()
    _constraint(env, T.MAX_PRESENCE, {"days": 2, "max_minutes": 360})
    for day in range(3):
        _teach(env, day=day, slot=0)
    assert _codes(env) == ["max_presence_days"]


def test_arrival_departure():
    env = mini_school()
    _constraint(env, T.ARRIVAL_DEPARTURE, {"days": 5, "not_before_slot": 1})
    _teach(env, day=0, slot=0)             # inizia alla fascia 0: giorno non conforme
    assert _codes(env) == ["arrival_departure"]


def test_free_guaranteed():
    env = mini_school()
    _constraint(env, T.FREE_GUARANTEED, {"free_days": 2, "free_half_days": 0})
    for day in range(4):                   # lavora 4 giorni su 5: 1 libero < 2
        _teach(env, day=day, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["free_guaranteed"]
    assert findings[0].quantities["free_days"] == 1


def test_max_half_days_e_solo_mezza_giornata():
    env = mini_school()
    _constraint(env, T.MAX_HALF_DAYS,
                {"max_half_days": 1, "only_half_day_per_day": True})
    _teach(env, day=0, slot=0)             # mattina
    _teach(env, day=0, slot=5)             # pomeriggio: 2 mezze giornate, stesso giorno
    assert sorted(_codes(env)) == ["max_half_days", "only_half_day"]


def test_max_site_changes():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    _constraint(env, T.MAX_SITE_CHANGES, {"per_day": 0})
    a = _teach(env, day=0, slot=0)
    b = _teach(env, day=0, slot=3)         # fascia libera sufficiente (default 1)
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    assert _codes(env) == ["max_site_changes"]


def test_max_gap_per_mezza_giornata():
    env = mini_school()
    _constraint(env, T.MAX_GAP_HOURS, {"max_gap_minutes": 60})
    _teach(env, day=0, slot=0)
    _teach(env, day=0, slot=3)             # buco di 2 fasce in mattinata = 120'
    _teach(env, day=1, slot=3)
    _teach(env, day=1, slot=4)             # pausa pranzo fra le fasce 3 e 4: non è un buco
    assert _codes(env) == ["max_gap"]
```

Nota sul test dei buchi: con `morning_end_slot = 4` le fasce 0–3 sono mattina e
4–5 pomeriggio, quindi le fasce 3 e 4 dello stesso giorno stanno in mezze
giornate diverse e non generano buco.

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_time_constraints.py -v`
Expected: 9 FAIL (nessun finding emesso: i checker non esistono).

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/checkers/time_constraints.py
"""Gli otto tipi di ResourceTimeConstraint (l'asse Cardinalità), sulla risorsa
generica: stessa tabella per docenti e classi. Presenza ≠ attività: la
presenza include i buchi. I buchi si contano per mezza giornata: la pausa
pranzo non è mai un buco (linea di fine mattinata, vincoli.md)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ResourceTimeConstraint

T = ResourceTimeConstraint.Type


def _finding(state, code, row, **quantities):
    name = state.resource_names.get(row.resource_id, str(row.resource_id))
    return Finding(code, causali.message(code, resource=name), Severity.HARD,
                   resources=(row.resource_id,), quantities=quantities)


class _TimeChecker(Checker):
    TYPE = None

    def check(self, state, resources=None):
        for row in ResourceTimeConstraint.objects.filter(type=self.TYPE):
            if resources is not None and row.resource_id not in resources:
                continue
            yield from self.violations(state, row, state.resource_days(row.resource_id))

    def violations(self, state, row, days):
        raise NotImplementedError


def _presence_minutes(state, slots):
    return (slots[-1] - slots[0] + 1) * state.grid.slot_minutes


def _halves(state, slots):
    """(fasce di mattina, fasce di pomeriggio)."""
    boundary = state.grid.morning_end_slot
    return [s for s in slots if s < boundary], [s for s in slots if s >= boundary]


@register(T.MIN_DISTRIBUTION)
class MinDistributionChecker(_TimeChecker):
    TYPE = T.MIN_DISTRIBUTION

    def violations(self, state, row, days):
        threshold = row.params["min_minutes_per_day"]
        qualifying = [d for d, slots in days.items()
                      if len(slots) * state.grid.slot_minutes >= threshold]
        if len(qualifying) < row.params["min_days"]:
            yield _finding(state, "min_distribution", row,
                           days=len(qualifying), min_days=row.params["min_days"])


@register(T.MAX_HOURS)
class MaxHoursChecker(_TimeChecker):
    TYPE = T.MAX_HOURS

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
                    yield _finding(state, code, row,
                                   day=day, minutes=n_slots * sm, max_minutes=cap)


@register(T.MAX_PRESENCE)
class MaxPresenceChecker(_TimeChecker):
    TYPE = T.MAX_PRESENCE

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


@register(T.ARRIVAL_DEPARTURE)
class ArrivalDepartureChecker(_TimeChecker):
    TYPE = T.ARRIVAL_DEPARTURE

    def violations(self, state, row, days):
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        compliant = 0
        for day in range(state.grid.days_per_cycle):
            slots = days.get(day)
            if not slots:
                compliant += 1  # giornata vuota: rispettata
                continue
            ok = ((not_before is None or slots[0] >= not_before)
                  and (not_after is None or slots[-1] < not_after))
            compliant += ok
        if compliant < row.params["days"]:
            yield _finding(state, "arrival_departure", row,
                           days=compliant, min_days=row.params["days"])


@register(T.FREE_GUARANTEED)
class FreeGuaranteedChecker(_TimeChecker):
    TYPE = T.FREE_GUARANTEED

    def violations(self, state, row, days):
        free_days = [d for d in range(state.grid.days_per_cycle) if d not in days]
        free_halves = 0
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            free_halves += (not morning) + (not afternoon)
        short_days = len(free_days) < row.params.get("free_days", 0)
        short_halves = free_halves < row.params.get("free_half_days", 0)
        if short_days or short_halves:
            yield _finding(state, "free_guaranteed", row,
                           free_days=len(free_days), free_half_days=free_halves,
                           min_free_days=row.params.get("free_days", 0),
                           min_free_half_days=row.params.get("free_half_days", 0))


@register(T.MAX_HALF_DAYS)
class MaxHalfDaysChecker(_TimeChecker):
    TYPE = T.MAX_HALF_DAYS

    def violations(self, state, row, days):
        worked, both = 0, []
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            worked += bool(morning) + bool(afternoon)
            if morning and afternoon:
                both.append(day)
        cap = row.params.get("max_half_days")
        if cap is not None and worked > cap:
            yield _finding(state, "max_half_days", row,
                           half_days=worked, max_half_days=cap)
        if row.params.get("only_half_day_per_day"):
            for day in both:
                yield _finding(state, "only_half_day", row, day=day)


def _site_sequence(state, key, day, slots):
    sequence = []
    for s in slots:
        for aid in state.occupancy[(key, day, s)]:
            site = state.activities[aid].site_id
            if site is not None:
                sequence.append(site)
    return sequence


@register(T.MAX_SITE_CHANGES)
class MaxSiteChangesChecker(_TimeChecker):
    TYPE = T.MAX_SITE_CHANGES

    def violations(self, state, row, days):
        per_week = 0
        for day, slots in days.items():
            sites = _site_sequence(state, row.resource_id, day, slots)
            changes = sum(a != b for a, b in zip(sites, sites[1:]))
            per_week += changes
            cap = row.params.get("per_day")
            if cap is not None and changes > cap:
                yield _finding(state, "max_site_changes", row,
                               day=day, changes=changes, max_changes=cap)
        cap = row.params.get("per_week")
        if cap is not None and per_week > cap:
            yield _finding(state, "max_site_changes", row,
                           changes=per_week, max_changes=cap)


@register(T.MAX_GAP_HOURS)
class MaxGapChecker(_TimeChecker):
    TYPE = T.MAX_GAP_HOURS

    def violations(self, state, row, days):
        sm = state.grid.slot_minutes
        total = 0
        for day, slots in days.items():
            for half in _halves(state, slots):
                if len(half) >= 2:
                    total += (half[-1] - half[0] + 1 - len(half)) * sm
        cap = row.params["max_gap_minutes"]
        if total > cap:
            yield _finding(state, "max_gap", row,
                           gap_minutes=total, max_gap_minutes=cap)
```

In `domain/analysis/checkers/__init__.py`:

```python
from . import grid, occupation, sites, time_constraints, unavailability  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_time_constraints.py -v`
Expected: 9 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/checkers/ tests/test_analysis_time_constraints.py
git commit -m "feat(analysis): gli otto vincoli orari sulla risorsa"
```

---

### Task 6: I tredici vincoli di materia

**Files:**
- Create: `domain/analysis/checkers/subject_constraints.py`
- Modify: `domain/analysis/checkers/__init__.py` (aggiungere `subject_constraints`)
- Test: `tests/test_analysis_subject_constraints.py`

**Interfaces:**
- Consumes: `SubjectConstraint` (13 tipi, relazione **orientata**, `A = B` caso dominante; `param` = minuti per i `MAX_HOURS_*`, mezze giornate per successioni e scarti), `Checker`, `register`, `ScheduleState`.
- Produces: un checker registrato per **ogni** valore di `SubjectConstraint.Type`. Semantica scelta e dichiarata: le attività si attribuiscono alla mezza giornata della **fascia di partenza**; una riga di vincolo si applica alle attività i cui token intersecano l'espansione dell'unità della riga (stessa regola dei conflitti); i quattro `PARTS_*` distinguono attività **a classe intera** (i token contengono una chiave di tipo `class`) da attività **in gruppo** (nessuna chiave di tipo `class`): `PARTS_BEFORE` = nel giorno, ogni ora in gruppo inizia prima di ogni ora a classe intera; `PARTS_AFTER` simmetrico; `_H` = nessuna interlacciatura dentro la **mezza giornata**; `_AB` = nessuna interlacciatura dentro la **giornata**.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_subject_constraints.py
"""I tredici tipi di SubjectConstraint, uno scenario minimo ciascuno."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import ClassPart, ClassPartition, Subject, SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = SubjectConstraint.Type


def _row(env, type_, subject_b=None, param=None):
    return SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=subject_b or env["subject"], type=type_, param=param)


def _lesson(env, day, slot, subject=None, slots=1):
    a = make_activity(subject or env["subject"], classes=[env["klass"]], slots=slots)
    place(env["schedule"], a, day=day, slot=slot)
    return a


def _other_subject(env):
    return Subject.objects.create(code="MAT", name="Matematica",
                                  discipline=env["discipline"])


def _codes(env):
    return [f.code for f in check_schedule(env["schedule"])]


def test_same_half_day_incompatible():
    env = mini_school()
    _row(env, T.SAME_HALF_DAY_INCOMPATIBLE)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=2)          # stessa mattina
    assert _codes(env) == ["subject_same_half_day"]


def test_same_day_incompatible():
    env = mini_school()
    _row(env, T.SAME_DAY_INCOMPATIBLE)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=5)          # mattina + pomeriggio: stessa giornata
    assert _codes(env) == ["subject_same_day"]


def test_same_day_orientato_fra_due_materie():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.SAME_DAY_INCOMPATIBLE, subject_b=mat)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=1, subject=mat)
    assert _codes(env) == ["subject_same_day"]


def test_two_days_incompatible():
    env = mini_school()
    _row(env, T.TWO_DAYS_INCOMPATIBLE)
    _lesson(env, day=1, slot=0)
    _lesson(env, day=2, slot=0)          # giorni consecutivi
    assert _codes(env) == ["subject_two_days"]


def test_forbidden_sequence():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.FORBIDDEN_SEQUENCE, subject_b=mat)
    _lesson(env, day=0, slot=0, slots=2)
    _lesson(env, day=0, slot=2, subject=mat)  # MAT subito dopo ITA
    assert _codes(env) == ["subject_forbidden_sequence"]


def test_max_hours_half_day():
    env = mini_school()
    _row(env, T.MAX_HOURS_HALF_DAY, param=60)
    _lesson(env, day=0, slot=0, slots=2)      # 120' > 60' nella mattinata
    assert _codes(env) == ["subject_max_hours_half_day"]


def test_max_hours_day():
    env = mini_school()
    _row(env, T.MAX_HOURS_DAY, param=120)
    _lesson(env, day=0, slot=0, slots=2)
    _lesson(env, day=0, slot=4)               # 180' > 120' nella giornata
    assert _codes(env) == ["subject_max_hours_day"]


def test_weekly_order():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.WEEKLY_ORDER, subject_b=mat)  # ITA prima di MAT nella settimana
    _lesson(env, day=1, slot=0)
    _lesson(env, day=0, slot=0, subject=mat)  # MAT arriva prima: violazione
    assert _codes(env) == ["subject_weekly_order"]


def test_imposed_succession():
    env = mini_school()
    _row(env, T.IMPOSED_SUCCESSION, param=2)  # occorrenze a distanza max 2 mezze g.
    _lesson(env, day=0, slot=0)
    _lesson(env, day=2, slot=0)               # 4 mezze giornate dopo: violazione
    assert _codes(env) == ["subject_imposed_succession"]


def test_half_day_gap():
    env = mini_school()
    _row(env, T.HALF_DAY_GAP, param=3)        # scarto minimo 3 mezze giornate
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=5)               # scarto 1: violazione
    assert _codes(env) == ["subject_half_day_gap"]


def _with_part(env):
    partition = ClassPartition.objects.create(school_class=env["klass"], name="SDOPP")
    return ClassPart.objects.create(name="1A-g1", partition=partition)


def _part_lesson(env, part, day, slot):
    a = make_activity(env["subject"], parts=[part])
    place(env["schedule"], a, day=day, slot=slot)
    return a


def test_parts_before_class():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_CLASS)
    _lesson(env, day=0, slot=1)               # classe intera alla fascia 1
    _part_lesson(env, part, day=0, slot=2)    # gruppo dopo: violazione
    assert _codes(env) == ["subject_parts_order"]


def test_parts_after_class():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_AFTER_CLASS)
    _part_lesson(env, part, day=0, slot=1)    # gruppo prima: violazione
    _lesson(env, day=0, slot=2)
    assert _codes(env) == ["subject_parts_order"]


def test_parts_no_interleaving_half_day():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_OR_AFTER_CLASS_H)
    _part_lesson(env, part, day=0, slot=0)
    _lesson(env, day=0, slot=1)               # classe in mezzo al gruppo
    _part_lesson(env, part, day=0, slot=2)    # interlacciato: violazione
    assert _codes(env) == ["subject_parts_order"]


def test_parts_no_interleaving_day_ok_se_compatti():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    _lesson(env, day=0, slot=0)
    _part_lesson(env, part, day=0, slot=4)    # tutte le ore classe, poi il gruppo
    _part_lesson(env, part, day=0, slot=5)
    assert _codes(env) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_subject_constraints.py -v`
Expected: 13 FAIL (nessun finding emesso); l'ultimo (`ok_se_compatti`) può già passare a vuoto — accettabile: il suo valore è da rosso-verde con gli altri.

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/checkers/subject_constraints.py
"""I tredici tipi di SubjectConstraint (l'asse Relazione): orientati,
A = B come caso dominante. Le attività si attribuiscono alla mezza giornata
della fascia di partenza. Una riga si applica alle attività i cui token
intersecano l'espansione dell'unità della riga."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, Group, SubjectConstraint
from domain.models.resources import Resource

T = SubjectConstraint.Type


def _unit_keys(row):
    if row.school_class_id:
        parts = ClassPart.objects.filter(
            partition__school_class_id=row.school_class_id).values_list("pk", flat=True)
        return frozenset({row.school_class_id, *parts})
    if row.class_part_id:
        return frozenset({row.class_part_id})
    return frozenset(Group.objects.get(pk=row.group_id)
                     .parts.values_list("pk", flat=True))


def _unit_resources(row):
    """I pk di Resource che identificano l'unità nel finding (per i
    raggruppamenti, che non sono Resource, le parti membre)."""
    if row.school_class_id:
        return (row.school_class_id,)
    if row.class_part_id:
        return (row.class_part_id,)
    return tuple(sorted(Group.objects.get(pk=row.group_id)
                        .parts.values_list("pk", flat=True)))


def _placed_of(state, keys, subject_id):
    return sorted(
        (pl for aid, pl in state.placed.items()
         if state.activities[aid].subject_id == subject_id
         and state.tokens[aid] & keys),
        key=lambda p: (p.day, p.start_slot))


def _half(state, day, slot):
    return day * 2 + (0 if slot < state.grid.morning_end_slot else 1)


def _is_class_level(state, aid):
    return any(state.kinds.get(k) == Resource.Kind.CLASS for k in state.tokens[aid])


class _SubjectChecker(Checker):
    TYPE = None
    CODE = None

    def check(self, state, resources=None):
        rows = (SubjectConstraint.objects.filter(type=self.TYPE)
                .select_related("subject_a", "subject_b"))
        for row in rows:
            keys = _unit_keys(row)
            if resources is not None and not (keys & resources):
                continue
            a = _placed_of(state, keys, row.subject_a_id)
            b = (a if row.subject_a_id == row.subject_b_id
                 else _placed_of(state, keys, row.subject_b_id))
            yield from self.violations(state, row, a, b)

    def finding(self, state, row, activity_ids, **quantities):
        return Finding(
            self.CODE, causali.message(self.CODE, subject=row.subject_a.name),
            Severity.HARD, resources=_unit_resources(row),
            activities=tuple(sorted(set(activity_ids))), quantities=quantities)


class _BucketIncompatible(_SubjectChecker):
    """Incompatibilità per secchio (mezza giornata o giornata)."""

    def bucket(self, state, pl):
        raise NotImplementedError

    def violations(self, state, row, a, b):
        buckets = defaultdict(lambda: ([], []))
        for pl in a:
            buckets[self.bucket(state, pl)][0].append(pl.activity_id)
        if row.subject_a_id != row.subject_b_id:
            for pl in b:
                buckets[self.bucket(state, pl)][1].append(pl.activity_id)
        for bucket, (la, lb) in sorted(buckets.items()):
            if row.subject_a_id == row.subject_b_id and len(la) > 1:
                yield self.finding(state, row, la, bucket=bucket, count=len(la))
            elif row.subject_a_id != row.subject_b_id and la and lb:
                yield self.finding(state, row, la + lb, bucket=bucket)


@register(T.SAME_HALF_DAY_INCOMPATIBLE)
class SameHalfDayChecker(_BucketIncompatible):
    TYPE, CODE = T.SAME_HALF_DAY_INCOMPATIBLE, "subject_same_half_day"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayChecker(_BucketIncompatible):
    TYPE, CODE = T.SAME_DAY_INCOMPATIBLE, "subject_same_day"

    def bucket(self, state, pl):
        return pl.day


@register(T.TWO_DAYS_INCOMPATIBLE)
class TwoDaysChecker(_SubjectChecker):
    TYPE, CODE = T.TWO_DAYS_INCOMPATIBLE, "subject_two_days"

    def violations(self, state, row, a, b):
        a_days = defaultdict(list)
        b_days = defaultdict(list)
        for pl in a:
            a_days[pl.day].append(pl.activity_id)
        for pl in b:
            b_days[pl.day].append(pl.activity_id)
        for day in sorted(a_days):
            if b_days.get(day + 1):
                acts = a_days[day] + b_days[day + 1]
                if len(set(acts)) > 1:
                    yield self.finding(state, row, acts, day=day)


@register(T.FORBIDDEN_SEQUENCE)
class ForbiddenSequenceChecker(_SubjectChecker):
    TYPE, CODE = T.FORBIDDEN_SEQUENCE, "subject_forbidden_sequence"

    def violations(self, state, row, a, b):
        for pa in a:
            end = pa.start_slot + state.activities[pa.activity_id].duration_slots
            for pb in b:
                if (pb.activity_id != pa.activity_id
                        and pb.day == pa.day and pb.start_slot == end):
                    yield self.finding(state, row, [pa.activity_id, pb.activity_id],
                                       day=pa.day, slot=pb.start_slot)


class _MaxHours(_SubjectChecker):
    def bucket(self, state, pl):
        raise NotImplementedError

    def violations(self, state, row, a, b):
        minutes = defaultdict(int)
        acts = defaultdict(list)
        for pl in a:
            key = self.bucket(state, pl)
            minutes[key] += state.activities[pl.activity_id].duration_minutes
            acts[key].append(pl.activity_id)
        for key in sorted(minutes):
            if row.param is not None and minutes[key] > row.param:
                yield self.finding(state, row, acts[key], bucket=key,
                                   minutes=minutes[key], max_minutes=row.param)


@register(T.MAX_HOURS_HALF_DAY)
class MaxHoursHalfDayChecker(_MaxHours):
    TYPE, CODE = T.MAX_HOURS_HALF_DAY, "subject_max_hours_half_day"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.MAX_HOURS_DAY)
class MaxHoursDayChecker(_MaxHours):
    TYPE, CODE = T.MAX_HOURS_DAY, "subject_max_hours_day"

    def bucket(self, state, pl):
        return pl.day


@register(T.WEEKLY_ORDER)
class WeeklyOrderChecker(_SubjectChecker):
    TYPE, CODE = T.WEEKLY_ORDER, "subject_weekly_order"

    def violations(self, state, row, a, b):
        if row.subject_a_id == row.subject_b_id or not a or not b:
            return
        first_a = (a[0].day, a[0].start_slot)
        first_b = (b[0].day, b[0].start_slot)
        if first_b < first_a:
            yield self.finding(state, row, [a[0].activity_id, b[0].activity_id])


@register(T.IMPOSED_SUCCESSION)
class ImposedSuccessionChecker(_SubjectChecker):
    TYPE, CODE = T.IMPOSED_SUCCESSION, "subject_imposed_succession"

    def violations(self, state, row, a, b):
        delay = row.param or 1
        if row.subject_a_id == row.subject_b_id:
            halves = [(_half(state, p.day, p.start_slot), p.activity_id) for p in a]
            for (h1, a1), (h2, a2) in zip(halves, halves[1:]):
                if h2 - h1 > delay:
                    yield self.finding(state, row, [a1, a2],
                                       gap=h2 - h1, max_gap=delay)
        else:
            b_halves = [_half(state, p.day, p.start_slot) for p in b]
            for pa in a:
                ha = _half(state, pa.day, pa.start_slot)
                if not any(0 < hb - ha <= delay for hb in b_halves):
                    yield self.finding(state, row, [pa.activity_id], max_gap=delay)


@register(T.HALF_DAY_GAP)
class HalfDayGapChecker(_SubjectChecker):
    TYPE, CODE = T.HALF_DAY_GAP, "subject_half_day_gap"

    def violations(self, state, row, a, b):
        same = row.subject_a_id == row.subject_b_id
        merged = [(_half(state, p.day, p.start_slot), p.activity_id, "a") for p in a]
        if not same:
            merged += [(_half(state, p.day, p.start_slot), p.activity_id, "b") for p in b]
        merged.sort()
        for (h1, a1, s1), (h2, a2, s2) in zip(merged, merged[1:]):
            crossed = same or s1 != s2
            if crossed and a1 != a2 and h2 - h1 < row.param:
                yield self.finding(state, row, [a1, a2],
                                   gap=h2 - h1, min_gap=row.param)


class _PartsOrder(_SubjectChecker):
    CODE = "subject_parts_order"
    MODE = None  # "before" | "after" | "homogeneous"

    def bucket(self, state, pl):
        return pl.day

    def violations(self, state, row, a, b):
        buckets = defaultdict(list)
        for pl in a:
            label = "class" if _is_class_level(state, pl.activity_id) else "part"
            buckets[self.bucket(state, pl)].append((pl.start_slot, label, pl.activity_id))
        for bucket, entries in sorted(buckets.items()):
            entries.sort()
            labels = [label for _, label, _ in entries]
            if "class" not in labels or "part" not in labels:
                continue
            bad = False
            if self.MODE == "before":
                bad = max(s for s, l, _ in entries if l == "part") > min(
                    s for s, l, _ in entries if l == "class")
            elif self.MODE == "after":
                bad = min(s for s, l, _ in entries if l == "part") < max(
                    s for s, l, _ in entries if l == "class")
            else:  # homogeneous: nessuna interlacciatura
                transitions = sum(x != y for x, y in zip(labels, labels[1:]))
                bad = transitions > 1
            if bad:
                yield self.finding(state, row, [aid for _, _, aid in entries],
                                   bucket=bucket)


@register(T.PARTS_BEFORE_CLASS)
class PartsBeforeChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_CLASS, "before"


@register(T.PARTS_AFTER_CLASS)
class PartsAfterChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_AFTER_CLASS, "after"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_H)
class PartsHomogeneousHalfChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_H, "homogeneous"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
class PartsHomogeneousDayChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_AB, "homogeneous"
```

In `domain/analysis/checkers/__init__.py`:

```python
from . import (grid, occupation, sites, subject_constraints,  # noqa: F401
               time_constraints, unavailability)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_subject_constraints.py -v`
Expected: 14 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/checkers/ tests/test_analysis_subject_constraints.py
git commit -m "feat(analysis): i tredici vincoli di materia"
```

---

### Task 7: Peso didattico, copertura monte ore e completezza del registro

**Files:**
- Create: `domain/analysis/checkers/weight.py`, `domain/analysis/checkers/coverage.py`
- Modify: `domain/analysis/checkers/__init__.py`
- Test: `tests/test_analysis_weight_coverage.py`

**Interfaces:**
- Consumes: `Subject.didactic_weight` (default 1), `SchoolClass.max_weekly_weight_per_student`, `InstituteSettings.max_weight_{morning,afternoon,day,week}`, `Service`, `ClassPart.effective_study_plan`.
- Produces: checker `"structural:didactic_weight"` e `"structural:coverage"`. Semantica dichiarata: il peso si conteggia **per parte, non per classe** (`Totale = Peso × Durata` in ore; per le classi senza partizioni la classe è la propria unica "parte"); tetti nullable = spenti; il tetto settimanale di classe (per alunno) prevale su quello d'istituto. La copertura confronta, per ogni **unità-studente** (parte, o classe senza parti), la somma dei minuti delle attività che la occupano con i servizi del piano effettivo — il predicato anti-inversione STO/SCI di [vincoli-attesi.md](../../../data/liceo-fermi/vincoli-attesi.md).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_weight_coverage.py
"""Peso didattico (per parte), copertura monte ore, completezza del registro."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.registry import REGISTRY, all_checkers
from domain.models import (
    ClassPart, ClassPartition, InstituteSettings, ResourceTimeConstraint,
    Service, SubjectConstraint,
)
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _institute(**caps):
    settings = InstituteSettings.load()
    for name, value in caps.items():
        setattr(settings, name, value)
    settings.save()


def test_peso_oltre_il_tetto_di_giornata():
    env = mini_school()
    _institute(max_weight_day=3)
    env["subject"].didactic_weight = 2
    env["subject"].save()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)  # 2×2 = 4 > 3
    place(env["schedule"], a, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["weight_day"]
    assert findings[0].quantities == {"day": 0, "weight": 4, "max_weight": 3}


def test_peso_per_parte_non_per_classe():
    """Il caso _REL/_ALT: due parti in parallelo non sommano i pesi."""
    env = mini_school()
    _institute(max_weight_day=2)
    partition = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=partition)
    alt = ClassPart.objects.create(name="1A_ALT", partition=partition)
    a = make_activity(env["subject"], parts=[rel], slots=2)   # peso 2 sulla parte
    b = make_activity(env["subject"], parts=[alt], slots=2)   # peso 2 sull'altra
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    # ogni parte riceve 120' ma il servizio (condiviso) ne ha accumulati 240:
    # si riallinea al monte ore per studente, che è 120'
    Service.objects.filter(study_plan=env["plan"], subject=env["subject"]) \
        .update(class_minutes=120)
    assert check_schedule(env["schedule"]) == []  # 2 ≤ 2 per ciascuna parte


def test_tetto_settimanale_di_classe_prevale():
    env = mini_school()
    _institute(max_weight_week=100)
    env["klass"].max_weekly_weight_per_student = 2
    env["klass"].save()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)  # peso 3 > 2
    place(env["schedule"], a, day=0, slot=0)
    assert [f.code for f in check_schedule(env["schedule"])] == ["weight_week"]


def test_copertura_monte_ore():
    env = mini_school()
    make_activity(env["subject"], classes=[env["klass"]])  # il servizio nasce a 60'
    service = Service.objects.get(study_plan=env["plan"], subject=env["subject"])
    service.class_minutes = 120                            # 60' contro 120'
    service.save()
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["coverage_mismatch"]
    assert findings[0].quantities == {"expected_minutes": 120, "actual_minutes": 60}


def test_copertura_quadrata_nessun_finding():
    env = mini_school()
    make_activity(env["subject"], classes=[env["klass"]], slots=2)
    assert check_schedule(env["schedule"]) == []


def test_registro_completo():
    """Ogni valore di enum ha un checker: nessun buco silenzioso nel verdetto."""
    all_checkers()  # forza la registrazione
    for value in ResourceTimeConstraint.Type.values:
        assert value in REGISTRY, f"ResourceTimeConstraint.Type.{value} senza checker"
    for value in SubjectConstraint.Type.values:
        assert value in REGISTRY, f"SubjectConstraint.Type.{value} senza checker"
    structural = {k for k in REGISTRY if isinstance(k, str) and k.startswith("structural:")}
    assert structural == {
        "structural:occupation", "structural:unavailability", "structural:grid",
        "structural:site_transition", "structural:didactic_weight",
        "structural:coverage",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_weight_coverage.py -v`
Expected: FAIL — i primi cinque a vuoto, `test_registro_completo` sulle due chiavi strutturali mancanti.

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/checkers/weight.py
"""Il peso didattico (ADR-011): Totale = Peso × Durata (in ore), conteggiato
per parte, non per classe (il caso _REL/_ALT verificato sui dati). Tetti
d'istituto per mattina/pomeriggio/giornata/settimana; il tetto settimanale
per alunno della classe prevale su quello d'istituto. Tetti NULL = spenti."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, SchoolClass
from domain.models.resources import Resource


def _student_keys(state, activity_id):
    """Le unità-studente su cui pesa un'attività: le parti nei token, o la
    classe stessa se la classe non ha partizioni."""
    tokens = state.tokens[activity_id]
    parts = [k for k in tokens if state.kinds.get(k) == Resource.Kind.CLASS_PART]
    if parts:
        return parts
    return [k for k in tokens if state.kinds.get(k) == Resource.Kind.CLASS]


@register("structural:didactic_weight")
class DidacticWeightChecker(Checker):
    def check(self, state, resources=None):
        s = state.settings
        per_day, per_half, per_week = (defaultdict(int), defaultdict(int),
                                       defaultdict(int))
        acts = defaultdict(set)
        for aid, pl in state.placed.items():
            act = state.activities[aid]
            weight = act.subject.didactic_weight * act.duration_slots
            half = "morning" if pl.start_slot < state.grid.morning_end_slot else "afternoon"
            for key in _student_keys(state, aid):
                per_day[(key, pl.day)] += weight
                per_half[(key, pl.day, half)] += weight
                per_week[key] += weight
                acts[key].add(aid)

        def emit(code, key, weight, cap, **extra):
            name = state.resource_names.get(key, str(key))
            return Finding(code, causali.message(code), Severity.HARD,
                           resources=(key,), activities=tuple(sorted(acts[key])),
                           quantities={"weight": weight, "max_weight": cap, **extra})

        for (key, day), weight in sorted(per_day.items()):
            if resources is not None and key not in resources:
                continue
            if s.max_weight_day is not None and weight > s.max_weight_day:
                yield emit("weight_day", key, weight, s.max_weight_day, day=day)
        half_caps = {"morning": s.max_weight_morning, "afternoon": s.max_weight_afternoon}
        for (key, day, half), weight in sorted(per_half.items()):
            if resources is not None and key not in resources:
                continue
            cap = half_caps[half]
            if cap is not None and weight > cap:
                code = "weight_morning" if half == "morning" else "weight_afternoon"
                yield emit(code, key, weight, cap, day=day)

        part_class = dict(ClassPart.objects.values_list(
            "pk", "partition__school_class_id"))
        class_caps = dict(SchoolClass.objects.values_list(
            "pk", "max_weekly_weight_per_student"))
        for key, weight in sorted(per_week.items()):
            if resources is not None and key not in resources:
                continue
            cap = class_caps.get(part_class.get(key, key))
            if cap is None:
                cap = s.max_weight_week
            if cap is not None and weight > cap:
                yield emit("weight_week", key, weight, cap)
```

```python
# domain/analysis/checkers/coverage.py
"""Copertura del monte ore per (unità-studente × materia): il predicato
anti-inversione STO/SCI. Confronta le attività (piazzate o no) con i servizi
del piano effettivo. È un predicato sui dati, non sull'orario."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, SchoolClass, Service, Subject


def _student_units():
    """(chiave Resource, StudyPlan effettivo, nome) per ogni parte, o per la
    classe se non ha partizioni."""
    for klass in SchoolClass.objects.select_related("study_plan"):
        parts = list(ClassPart.objects.filter(partition__school_class=klass)
                     .select_related("partition__school_class__study_plan", "study_plan"))
        if parts:
            for part in parts:
                yield part.pk, part.effective_study_plan, part.name
        else:
            yield klass.pk, klass.study_plan, klass.name


@register("structural:coverage")
class CoverageChecker(Checker):
    def check(self, state, resources=None):
        subject_names = dict(Subject.objects.values_list("id", "name"))
        services = defaultdict(dict)
        for s in Service.objects.all():
            services[s.study_plan_id][s.subject_id] = s.class_minutes
        for key, plan, unit_name in _student_units():
            if resources is not None and key not in resources:
                continue
            expected = services.get(plan.pk, {})
            actual = defaultdict(int)
            for aid, act in state.activities.items():
                if key in state.tokens[aid]:
                    actual[act.subject_id] += act.duration_minutes
            for subject_id in sorted(expected.keys() | actual.keys()):
                want, got = expected.get(subject_id, 0), actual.get(subject_id, 0)
                if want != got:
                    yield Finding(
                        "coverage_mismatch",
                        causali.message("coverage_mismatch", unit=unit_name,
                                        subject=subject_names[subject_id]),
                        Severity.HARD, resources=(key,),
                        quantities={"expected_minutes": want, "actual_minutes": got},
                    )
```

In `domain/analysis/checkers/__init__.py`:

```python
from . import (coverage, grid, occupation, sites, subject_constraints,  # noqa: F401
               time_constraints, unavailability, weight)
```

⚠ Attenzione ai test esistenti: `CoverageChecker` gira dentro `check_schedule`,
quindi i test dei task precedenti che creano attività **senza** servizi
corrispondenti produrrebbero `coverage_mismatch` inattesi. La fixture
`mini_school` non crea servizi, quindi ogni attività su `1A` genererebbe un
mismatch. **Correzione contestuale al task**: in `tests/analysis_helpers.py`,
`make_activity` deve mantenere allineato il servizio del piano:

```python
# in tests/analysis_helpers.py — sostituire make_activity con questa versione
from domain.models import Service


def make_activity(subject, *, teachers=(), classes=(), parts=(), groups=(),
                  rooms=(), slots=1, mask=FULL, **flags):
    a = Activity.objects.create(
        subject=subject, duration_slots=slots, duration_minutes=slots * 60,
        week_mask=mask, **flags,
    )
    for t in teachers:
        a.teachers.add(t)
    for c in classes:
        a.classes.add(c)
        _sync_service(c.study_plan, subject, slots * 60)
    for p in parts:
        a.parts.add(p)
        _sync_service(p.effective_study_plan, subject, slots * 60)
    for g in groups:
        a.groups.add(g)
        for p in g.parts.all():
            _sync_service(p.effective_study_plan, subject, slots * 60)
    for r in rooms:
        a.rooms.add(r)
    return a


def _sync_service(plan, subject, minutes):
    """Tiene la copertura quadrata: il monte ore del servizio cresce con le
    attività create dalla fixture."""
    service, _ = Service.objects.get_or_create(
        study_plan=plan, subject=subject, defaults={"class_minutes": 0})
    service.class_minutes += minutes
    service.save()
```

I test del passo 1 sono già scritti per questa meccanica: le attività si
creano prima (il servizio nasce allineato via `_sync_service`) e il mismatch
si costruisce sovrascrivendo poi `class_minutes`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_weight_coverage.py -v` → 6 PASS.
Poi **tutta la suite**: `venv/bin/pytest` → tutti verdi (i task precedenti
restano verdi grazie a `_sync_service`).

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/checkers/ tests/analysis_helpers.py tests/test_analysis_weight_coverage.py
git commit -m "feat(analysis): peso didattico per parte, copertura monte ore, registro completo"
```

---

### Task 8: Dominio residuo (`S.P.` / `Nr G.`)

**Files:**
- Create: `domain/analysis/domain_size.py`
- Test: `tests/test_analysis_domain_size.py`

**Interfaces:**
- Consumes: `ScheduleState` (`place`/`unplace`/`tokens`), `all_checkers`, `Severity`.
- Produces: `DomainSize(placements, days)`; `residual_domain(activity, state) -> DomainSize`. Semantica: piazzamento di prova su ogni (giorno, fascia di partenza) in cui il blocco entra nella griglia; ammissibile se non introduce **nuove** violazioni hard rispetto alla baseline (le preesistenti non squalificano — l'orario invalido è ammesso). Se l'attività è piazzata, si sospende prima del conto e si ripristina alla fine.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_domain_size.py
"""S.P. / Nr G.: il dominio residuo, ricalcolato mai memorizzato (ADR-007)."""
import pytest

from domain.analysis.domain_size import residual_domain
from domain.analysis.state import ScheduleState
from domain.models import ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_griglia_vuota_dominio_pieno():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 30  # 5 giorni × 6 fasce
    assert size.days == 5


def test_il_blocco_riduce_le_partenze():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)
    state = ScheduleState.build(env["schedule"])
    assert residual_domain(a, state).placements == 20  # 4 partenze × 5 giorni


def test_indisponibilita_esclude_il_giorno():
    env = mini_school()
    for slot in range(6):
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=0, slot=slot, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 24 and size.days == 4


def test_sospendere_un_vicino_alza_il_dominio():
    """Il comportamento osservato in EDT: i valori salgono sospendendo
    un'attività e si riabbassano richiudendo il buco."""
    env = mini_school()
    occupante = make_activity(env["subject"], teachers=[env["teacher"]])
    libera = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], occupante, day=0, slot=0)
    state = ScheduleState.build(env["schedule"])
    con_vicino = residual_domain(libera, state).placements
    state.unplace(occupante.id)
    senza_vicino = residual_domain(libera, state).placements
    state.place(occupante, 0, 0)
    di_nuovo = residual_domain(libera, state).placements
    assert senza_vicino == con_vicino + 1
    assert di_nuovo == con_vicino


def test_attivita_gia_piazzata_si_sospende_e_ripristina():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=2, slot=3)
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 30       # da sola: tutto libero
    assert state.placed[a.id].day == 2 # ripristinata dov'era


def test_violazioni_preesistenti_non_squalificano():
    """Due attività già in conflitto: il dominio di una terza non ne risente."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)   # conflitto preesistente
    altra = make_activity(env["subject"], classes=[env["klass"]])
    state = ScheduleState.build(env["schedule"])
    assert residual_domain(altra, state).placements == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_domain_size.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.domain_size'`

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/domain_size.py
"""S.P. / Nr G. — la dimensione del dominio residuo (motore-risoluzione.md):
«numero di fasce orarie possibili per il piazzamento dell'attività nel
rispetto di tutti i vincoli», ricalcolato contro lo stato corrente.
Calcolato, mai memorizzato (ADR-007)."""

from dataclasses import dataclass

from domain.analysis.findings import Severity
from domain.analysis.registry import all_checkers


@dataclass(frozen=True)
class DomainSize:
    placements: int   # S.P.: fasce orarie possibili
    days: int         # Nr G.: giorni distinti possibili


def _hard_keys(state, resources, checkers):
    keys = set()
    for checker in checkers:
        for f in checker.check(state, resources=resources):
            if f.severity == Severity.HARD:
                keys.add(f.key)
    return keys


def residual_domain(activity, state):
    """Piazzamento di prova su ogni collocazione: ammissibile se non introduce
    nuove violazioni hard rispetto alla baseline. Le violazioni preesistenti
    non squalificano (l'orario invalido è ammesso)."""
    checkers = all_checkers()
    was = state.placed.get(activity.id)
    if was is not None:
        state.unplace(activity.id)
    resources = state.tokens[activity.id]
    baseline = _hard_keys(state, resources, checkers)
    grid = state.grid
    count, days = 0, set()
    try:
        for day in range(grid.days_per_cycle):
            for start in range(grid.slots_per_day - activity.duration_slots + 1):
                state.place(activity, day, start)
                fresh = _hard_keys(state, resources, checkers) - baseline
                state.unplace(activity.id)
                if not fresh:
                    count += 1
                    days.add(day)
    finally:
        if was is not None and activity.id not in state.placed:
            state.place(activity, was.day, was.start_slot)
    return DomainSize(count, len(days))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_domain_size.py -v`
Expected: 6 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/domain_size.py tests/test_analysis_domain_size.py
git commit -m "feat(analysis): dominio residuo S.P. / Nr G. come piazzamento di prova"
```

---

### Task 9: L'analisi di capienza, con le due diagnosi EDT

**Files:**
- Create: `domain/analysis/capacity.py`
- Test: `tests/test_analysis_capacity.py`

**Interfaces:**
- Consumes: `activity_tokens`, modelli (`Activity`, `SubjectConstraint`, `ResourceTimeConstraint`, `ResourceUnavailability`, `SchoolClass`, `ClassPart`, `Group`, `TimeGrid`, `SchoolYear`), `domain.weeks`.
- Produces: `CapacityFinding(statement, unit_label, subject_label, teacher_label, n_activities, required_minutes, placeable_minutes, culprits, remedies, activities)`; `analyze_capacity() -> list[CapacityFinding]`. Il conto è l'**ottimo esatto di un rilassamento** (mai falsi allarmi): per (unità, materia), assegnazione ottima delle attività ai giorni sotto indisponibilità hard ricorrenti dell'unità e del docente comune, incompatibilità della materia con sé stessa (mezza giornata / giornata / 2 giorni), max ore materia (giornata, mezza giornata ripiegata su giornata), max ore risorsa, giornate libere garantite del docente. I colpevoli si trovano **per sottrazione** (famiglia rimossa → deficit sanato).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis_capacity.py
"""Le due diagnosi osservate in EDT (diagnostica.md), riprodotte come fixture."""
import pytest

from domain.analysis.capacity import analyze_capacity
from domain.models import ResourceTimeConstraint, SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _lettere_10h(env):
    """Diagnosi A: sei attività di LETTERE (2+2+2+2+1+1 = 10h) su una classe,
    materia incompatibile con sé stessa nella giornata, 5 giorni."""
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    return SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)


def test_diagnosi_a_lettere():
    env = mini_school()
    _lettere_10h(env)
    findings = analyze_capacity()
    assert len(findings) == 1
    f = findings[0]
    assert f.statement == ("I vincoli della classe non permettono il "
                           "piazzamento di tutte le attività.")
    assert f.n_activities == 6
    assert f.required_minutes == 600
    assert f.placeable_minutes == 540      # le 5 attività più lunghe: 9h00
    assert any("incompatib" in c.lower() for c in f.culprits)
    assert "Rendere i vincoli delle materie meno vincolanti" in f.remedies
    assert "Diminuire la durata delle attività" in f.remedies


def test_diagnosi_b_incrociata():
    """Diagnosi B: 4 attività di 6h, stessa incompatibilità, più le due
    giornate libere del docente: innocui separatamente, fatali insieme."""
    env = mini_school()
    for slots in (2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=ResourceTimeConstraint.Type.FREE_GUARANTEED,
        params={"free_days": 2, "free_half_days": 0})
    findings = analyze_capacity()
    assert len(findings) == 1
    f = findings[0]
    assert f.statement == ("I vincoli incrociati della classe e del docente "
                           "non permettono il piazzamento di tutte le attività.")
    assert f.required_minutes == 360
    assert f.placeable_minutes == 300      # 3 giorni × 1 attività: 2+2+1
    assert f.teacher_label == "Rossi Anna"
    assert "Diminuire i giorni e 1/2 giornate libere" in f.remedies
    assert len(f.culprits) >= 2            # entrambe le famiglie mostrate


def test_ciascun_vincolo_da_solo_e_innocuo():
    """Il controllo negativo della diagnosi B: senza l'altro vincolo, nessun
    finding — il verdetto è esatto, mai un falso allarme."""
    env = mini_school()
    for slots in (2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    assert analyze_capacity() == []        # 5 giorni × 1 attività ≥ 4 attività


def test_dieci_ore_senza_vincoli_entrano():
    env = mini_school()
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], classes=[env["klass"]], slots=slots)
    assert analyze_capacity() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analysis_capacity.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.capacity'`

- [ ] **Step 3: Write the implementation**

```python
# domain/analysis/capacity.py
"""L'aritmetica di capienza (fase 4 di EDT, diagnostica.md): per (unità,
materia), quante ore entrano al massimo contro quante ne servono. L'ottimo è
esatto su un RILASSAMENTO del problema vero: un verdetto negativo è una
dimostrazione di infattibilità, mai una stima. Il caso collettivo su risorse
incrociate (violatore di Hall, fase 5) è fuori scope → piano CP-SAT."""

import itertools
from dataclasses import dataclass
from functools import lru_cache

from domain import weeks
from domain.models import (
    Activity, ClassPart, Group, ResourceTimeConstraint, ResourceUnavailability,
    SchoolClass, SchoolYear, SubjectConstraint, TimeGrid,
)
from domain.analysis.state import activity_tokens

T = SubjectConstraint.Type
RT = ResourceTimeConstraint.Type

_REMEDY = {
    "subject_rows": "Rendere i vincoli delle materie meno vincolanti",
    "unit_unavailability": "Diminuire le indisponibilità delle risorse",
    "teacher_unavailability": "Diminuire le indisponibilità delle risorse",
    "teacher_free_days": "Diminuire i giorni e 1/2 giornate libere",
    "resource_max_hours": "Rendere i massimi orari meno vincolanti",
}
_TEACHER_FAMILIES = {"teacher_unavailability", "teacher_free_days"}


@dataclass(frozen=True)
class CapacityFinding:
    statement: str
    unit_label: str
    subject_label: str
    teacher_label: str | None
    n_activities: int
    required_minutes: int
    placeable_minutes: int
    culprits: tuple[str, ...]
    remedies: tuple[str, ...]
    activities: tuple[int, ...]


def _units():
    for klass in SchoolClass.objects.all():
        parts = frozenset(ClassPart.objects.filter(
            partition__school_class=klass).values_list("pk", flat=True))
        yield klass.name, frozenset({klass.pk}) | parts, frozenset({klass.pk})
    for part in ClassPart.objects.all():
        yield part.name, frozenset({part.pk}), frozenset({part.pk})
    for group in Group.objects.all():
        parts = frozenset(group.parts.values_list("pk", flat=True))
        yield group.name, parts, parts


def _week_groups(acts):
    """Gruppi di attività per firma di settimana: la capienza deve reggere in
    ogni settimana; per il Fermi (tutto annuale) la firma è una."""
    year = SchoolYear.objects.first()
    if year is None:
        return [acts]
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
    groups = {}
    for w in range(n_weeks):
        sig = frozenset(a.id for a in acts if weeks.week_in_mask(a.week_mask, w))
        if sig and sig not in groups:
            groups[sig] = [a for a in acts if a.id in sig]
    return list(groups.values()) or [acts]


def _max_assign(durations, day_caps):
    """Ottimo esatto: massimo dei minuti assegnabili. durations decrescenti;
    day_caps: tuple di (giorno, minuti residui, conteggio residuo, adiacenza
    vietata?)."""
    durations = tuple(sorted(durations, reverse=True))

    @lru_cache(maxsize=None)
    def best(idx, caps):
        if idx == len(durations):
            return 0
        duration = durations[idx]
        top = best(idx + 1, caps)  # l'attività resta fuori
        for i, (day, minutes, count, forbid) in enumerate(caps):
            if minutes >= duration and count > 0:
                updated = list(caps)
                updated[i] = (day, minutes - duration, count - 1, forbid)
                if forbid:
                    updated = [(d, 0, 0, f) if abs(d - day) == 1 else (d, m, c, f)
                               for d, m, c, f in updated]
                top = max(top, duration + best(idx + 1, tuple(updated)))
        return top

    return best(0, day_caps)


def _placeable(grid, group, unit_ids, teacher_ids, subject_id, unit_keys,
               disabled):
    sm, n_days = grid.slot_minutes, grid.days_per_cycle
    unavailable = {d: set() for d in range(n_days)}
    families = []
    if "unit_unavailability" not in disabled:
        families.append(("unit_unavailability", unit_ids))
    if teacher_ids and "teacher_unavailability" not in disabled:
        families.append(("teacher_unavailability", teacher_ids))
    for _, ids in families:
        rows = ResourceUnavailability.objects.filter(
            resource_id__in=ids, level="hard", date=None)
        for u in rows:
            if u.day < n_days:
                unavailable[u.day].add(u.slot)
    available = {d: [s for s in range(grid.slots_per_day)
                     if s not in unavailable[d]] for d in range(n_days)}

    same_day = same_half = two_days = False
    max_day = max_half = None
    if "subject_rows" not in disabled:
        for row in _subject_rows(subject_id, unit_keys):
            if row.type == T.SAME_DAY_INCOMPATIBLE:
                same_day = True
            elif row.type == T.SAME_HALF_DAY_INCOMPATIBLE:
                same_half = True
            elif row.type == T.TWO_DAYS_INCOMPATIBLE:
                two_days = True
            elif row.type == T.MAX_HOURS_DAY and row.param is not None:
                max_day = row.param if max_day is None else min(max_day, row.param)
            elif row.type == T.MAX_HOURS_HALF_DAY and row.param is not None:
                max_half = row.param if max_half is None else min(max_half, row.param)

    resource_day_cap = None
    if "resource_max_hours" not in disabled:
        rows = ResourceTimeConstraint.objects.filter(
            type=RT.MAX_HOURS, resource_id__in=unit_ids | teacher_ids)
        for r in rows:
            cap = r.params.get("day_minutes")
            if cap is not None:
                resource_day_cap = (cap if resource_day_cap is None
                                    else min(resource_day_cap, cap))

    day_caps = []
    for d in range(n_days):
        slots = available[d]
        morning = [s for s in slots if s < grid.morning_end_slot]
        afternoon = [s for s in slots if s >= grid.morning_end_slot]
        cap = len(slots) * sm
        if max_half is not None:
            cap = min(cap, min(len(morning) * sm, max_half)
                      + min(len(afternoon) * sm, max_half))
        if max_day is not None:
            cap = min(cap, max_day)
        if resource_day_cap is not None:
            cap = min(cap, resource_day_cap)
        count = 1 if same_day else (2 if same_half else max(len(slots), 1))
        day_caps.append((d, cap, count, two_days))

    free_days = 0
    if teacher_ids and "teacher_free_days" not in disabled:
        rows = ResourceTimeConstraint.objects.filter(
            type=RT.FREE_GUARANTEED, resource_id__in=teacher_ids)
        for r in rows:
            free_days = max(free_days, r.params.get("free_days", 0))

    durations = [a.duration_minutes for a in group]
    kept = max(0, n_days - free_days)
    best = 0
    for combo in itertools.combinations(range(n_days), kept):
        caps = tuple(day_caps[d] for d in combo)
        best = max(best, _max_assign(durations, caps))
    return best


def _subject_rows(subject_id, unit_keys):
    from domain.analysis.checkers.subject_constraints import _unit_keys
    rows = SubjectConstraint.objects.filter(
        subject_a_id=subject_id, subject_b_id=subject_id)
    return [row for row in rows if _unit_keys(row) & unit_keys]


def _culprit_labels(family, subject, teacher_name, rows):
    if family == "subject_rows":
        return [f"Vincolo materia: {subject.name}/{subject.name} — "
                f"{row.get_type_display()}" for row in rows]
    if family == "teacher_free_days":
        return [f"Giorni e 1/2 giornate libere di {teacher_name}"]
    if family == "teacher_unavailability":
        return [f"Indisponibilità di {teacher_name}"]
    if family == "unit_unavailability":
        return ["Indisponibilità dell'unità"]
    return ["Massimi orari della risorsa"]


def analyze_capacity():
    grid = TimeGrid.objects.first()
    if grid is None:
        return []
    acts = list(Activity.objects
                .exclude(immobility=Activity.Immobility.SUSPENDED)
                .select_related("subject")
                .prefetch_related("teachers", "classes", "parts", "groups",
                                  "rooms", "staff", "material_requirements"))
    tokens = {a.id: activity_tokens(a)[0] for a in acts}
    teacher_sets = {a.id: frozenset(t.pk for t in a.teachers.all()) for a in acts}
    teacher_names = {t.pk: t.name
                     for a in acts for t in a.teachers.all()}
    findings, seen = [], set()
    for week_acts in _week_groups(acts):
        for unit_label, unit_keys, unit_ids in _units():
            by_subject = {}
            for a in week_acts:
                if tokens[a.id] & unit_keys:
                    by_subject.setdefault(a.subject_id, []).append(a)
            for subject_id, group in by_subject.items():
                dedup = (frozenset(a.id for a in group), subject_id)
                if dedup in seen:
                    continue
                seen.add(dedup)
                common = frozenset.intersection(
                    *(teacher_sets[a.id] for a in group))
                required = sum(a.duration_minutes for a in group)
                args = (grid, group, unit_ids, common, subject_id, unit_keys)
                placeable = _placeable(*args, disabled=frozenset())
                if placeable >= required:
                    continue
                subject = group[0].subject
                teacher_name = (teacher_names[next(iter(common))]
                                if len(common) == 1 else None)
                culprits, remedies = [], {"Diminuire la durata delle attività"}
                guilty_families = set()
                for family in _REMEDY:
                    if _placeable(*args, disabled=frozenset({family})) >= required:
                        guilty_families.add(family)
                        rows = (_subject_rows(subject_id, unit_keys)
                                if family == "subject_rows" else ())
                        culprits += _culprit_labels(family, subject,
                                                    teacher_name, rows)
                        remedies.add(_REMEDY[family])
                if not culprits:
                    culprits = ["Vincoli combinati: nessuna famiglia da sola "
                                "ripristina la capienza"]
                crossed = guilty_families & _TEACHER_FAMILIES
                unit_side = guilty_families - _TEACHER_FAMILIES
                if crossed and unit_side:
                    statement = ("I vincoli incrociati della classe e del docente "
                                 "non permettono il piazzamento di tutte le attività.")
                elif crossed:
                    statement = ("I vincoli del docente non permettono il "
                                 "piazzamento di tutte le attività.")
                else:
                    statement = ("I vincoli della classe non permettono il "
                                 "piazzamento di tutte le attività.")
                findings.append(CapacityFinding(
                    statement=statement, unit_label=unit_label,
                    subject_label=subject.name, teacher_label=teacher_name,
                    n_activities=len(group), required_minutes=required,
                    placeable_minutes=placeable,
                    culprits=tuple(culprits), remedies=tuple(sorted(remedies)),
                    activities=tuple(sorted(a.id for a in group)),
                ))
    return findings
```

Nota per l'implementatore: in `analyze_capacity` la diagnosi B richiede che i
colpevoli emergano **solo per sottrazione congiunta**? No — per costruzione la
sottrazione è per famiglia singola: nella diagnosi B rimuovere `subject_rows`
porta a 3 giorni senza tetto di conteggio (6h ≥ 6h ✓) e rimuovere
`teacher_free_days` porta a 5 giorni × 1 attività (2+2+1+1 = 6h ✓), quindi
**entrambe** le famiglie risultano colpevoli e lo statement è «incrociati».

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analysis_capacity.py -v`
Expected: 4 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/capacity.py tests/test_analysis_capacity.py
git commit -m "feat(analysis): analisi di capienza esatta con colpevoli per sottrazione"
```

---

### Task 10: Il comando `manage.py analyze`

**Files:**
- Create: `domain/management/__init__.py` (vuoto), `domain/management/commands/__init__.py` (vuoto), `domain/management/commands/analyze.py`
- Test: `tests/test_analyze_command.py`

**Interfaces:**
- Consumes: `analyze_capacity`, `check_schedule`, `residual_domain`, `ScheduleState`, `Severity`.
- Produces: `manage.py analyze [--schedule N]` — senza `--schedule` solo capienza sui dati; con `--schedule` anche conformità e colonna `S.P.` crescente delle attività non piazzate. Output nei quattro riquadri di EDT più il **riepilogo finale navigabile** (la debolezza di EDT annotata in diagnostica.md). `CommandError("Rimangono delle incoerenze.")` se restano problemi hard → exit code ≠ 0, usabile in CI.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analyze_command.py
"""Il comando analyze: report in stile EDT, exit code per la CI."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command("analyze", *args, stdout=out)
    return out.getvalue()


def test_base_pulita():
    mini_school()
    out = _run()
    assert "Nessun problema di capienza" in out
    assert "Verifica terminata: nessuna incoerenza." in out


def test_deficit_di_capienza_stampa_i_quattro_riquadri_e_fallisce():
    env = mini_school()
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    out = StringIO()
    with pytest.raises(CommandError, match="Rimangono delle incoerenze."):
        call_command("analyze", stdout=out)
    text = out.getvalue()
    assert "I vincoli della classe non permettono il piazzamento" in text
    assert "Durata da piazzare: 10h00" in text
    assert "Durata piazzabile:  9h00" in text
    assert "» 1h00 non potrà essere piazzata" in text
    assert "Rendere i vincoli delle materie meno vincolanti" in text
    assert "1 problemi di capienza" in text          # il riepilogo che EDT non ha


def test_conformita_e_sp_con_schedule():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    non_piazzata = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)          # conflitto
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    text = out.getvalue()
    assert "già occupata in un'attività" in text
    assert "S.P." in text and "Italiano" in text      # la colonna delle non piazzate
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_analyze_command.py -v`
Expected: FAIL con `Unknown command: 'analyze'`

- [ ] **Step 3: Write the implementation**

```python
# domain/management/commands/analyze.py
"""L'analisi dei vincoli da riga di comando, nel formato di EDT:
enunciato → dettaglio con l'aritmetica → soluzione → azioni. In coda il
riepilogo navigabile che a EDT manca (diagnostica.md). Exit code ≠ 0 se
restano incoerenze: usabile in CI."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.domain_size import residual_domain
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState
from domain.models import Schedule


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


class Command(BaseCommand):
    help = "Analisi dei vincoli: capienza sui dati e conformità di uno schedule"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int,
                            help="pk dello Schedule di cui verificare la conformità")

    def handle(self, *args, **options):
        capacity = analyze_capacity()
        self.stdout.write("== Analisi di capienza ==")
        if not capacity:
            self.stdout.write("Nessun problema di capienza.")
        for i, f in enumerate(capacity, 1):
            self.stdout.write(f"\n[{i}] {f.statement}")
            header = f"    Unità: {f.unit_label}   Materia: {f.subject_label}"
            if f.teacher_label:
                header += f"   Docente: {f.teacher_label}"
            self.stdout.write(header)
            self.stdout.write(f"    Numero di attività: {f.n_activities}")
            self.stdout.write(f"    Durata da piazzare: {_hm(f.required_minutes)}")
            self.stdout.write(f"    Durata piazzabile:  {_hm(f.placeable_minutes)}")
            gap = f.required_minutes - f.placeable_minutes
            self.stdout.write(f"    » {_hm(gap)} non potrà essere piazzata")
            self.stdout.write("    Soluzione:")
            for culprit in f.culprits:
                self.stdout.write(f"      - {culprit}")
            self.stdout.write("    Azioni:")
            for remedy in f.remedies:
                self.stdout.write(f"      - {remedy}")

        hard = 0
        if options["schedule"]:
            schedule = Schedule.objects.get(pk=options["schedule"])
            findings = check_schedule(schedule)
            self.stdout.write(f"\n== Conformità (schedule {schedule.pk}) ==")
            if not findings:
                self.stdout.write("Nessuna violazione.")
            for f in findings:
                hard += f.severity == Severity.HARD
                details = ", ".join(f"{k}={v}" for k, v in sorted(f.quantities.items()))
                self.stdout.write(f"  [{f.severity}] {f.message}  ({details})")
            state = ScheduleState.build(schedule)
            unplaced = [a for aid, a in sorted(state.activities.items())
                        if aid not in state.placed]
            if unplaced:
                self.stdout.write("\n== S.P. delle attività non piazzate (crescente) ==")
                sized = sorted(((residual_domain(a, state), a) for a in unplaced),
                               key=lambda pair: pair[0].placements)
                for size, act in sized:
                    self.stdout.write(
                        f"  S.P. {size.placements:3d}  Nr G. {size.days}  "
                        f"{act.subject.name} ({_hm(act.duration_minutes)})")

        self.stdout.write("\n== Riepilogo ==")
        self.stdout.write(f"  {len(capacity)} problemi di capienza, "
                          f"{hard} violazioni hard.")
        if capacity or hard:
            raise CommandError("Rimangono delle incoerenze.")
        self.stdout.write("Verifica terminata: nessuna incoerenza.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_analyze_command.py -v`
Expected: 3 PASS. Poi `venv/bin/pytest` → tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add domain/management/ tests/test_analyze_command.py
git commit -m "feat(analysis): comando manage.py analyze con report in stile EDT"
```

---

### Task 11: Il Fermi arricchito dei vincoli attesi

**Files:**
- Modify: `tests/fermi.py` (indisponibilità dei part-time, anno/periodo/schedule)
- Test: `tests/test_fermi_constraints.py`

**Interfaces:**
- Consumes: `tests/fermi.py::build()` (già esistente: restituisce `{"grid", "plans", "classes", "teachers", "subjects"}`), `analyze_capacity`, `check_schedule`, `residual_domain`, `ScheduleState`.
- Produces: `build()` esteso — crea anche `SchoolYear` (33 settimane da `2026-09-14`), `Period`, `Schedule` (chiavi `"year"`, `"period"`, `"schedule"` nel dict) e le **indisponibilità hard a giornata intera dei part-time** da [vincoli-attesi.md](../../../data/liceo-fermi/vincoli-attesi.md): `UNAVAILABLE_DAYS = {"D06": [2, 4], "D09": [0, 1, 3], "D15": [0, 4]}` (giorni scelti qui — il dataset dichiara il bisogno, non i giorni: sono la nostra istanza concreta, dimensionata per restare risolvibile).

- [ ] **Step 1: Modify the fixture**

In `tests/fermi.py`, aggiungere agli import `Period, ResourceUnavailability, Schedule, SchoolYear` e `import datetime as dt`; sotto `WEEKS_IN_YEAR` aggiungere:

```python
UNAVAILABLE_DAYS = {"D06": [2, 4], "D09": [0, 1, 3], "D15": [0, 4]}
```

In fondo a `build()`, prima del `return`:

```python
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14),
        end_date=dt.date(2026, 9, 14) + dt.timedelta(weeks=WEEKS_IN_YEAR) - dt.timedelta(days=1),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(school_year=year, name="Annuale",
                                   start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    for teacher_id, days in UNAVAILABLE_DAYS.items():
        for day in days:
            for slot in range(6):
                ResourceUnavailability.objects.create(
                    resource=teachers[teacher_id], day=day, slot=slot, level="hard")
```

e nel `return` aggiungere `"year": year, "period": period, "schedule": schedule`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_fermi_constraints.py
"""L'analisi sul Fermi: capienza pulita per costruzione, l'inversione STO/SCI
rilevata dalla copertura, le indisponibilità dei part-time attive."""
import time

import pytest

from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.domain_size import residual_domain
from domain.analysis.state import ScheduleState
from domain.models import Activity, Placement, Service
from tests import fermi

pytestmark = pytest.mark.django_db


def test_capienza_del_fermi_pulita():
    """Il dataset è risolvibile per costruzione: nessun verdetto negativo."""
    fermi.build()
    assert analyze_capacity() == []


def test_conformita_su_schedule_vuoto_pulita():
    """Senza piazzamenti, l'unico checker che potrebbe scattare è la
    copertura: sul Fermi corretto non scatta."""
    env = fermi.build()
    assert check_schedule(env["schedule"]) == []


def test_inversione_sto_sci_rilevata():
    """Il caso reale del 2026-07-09: STO e SCI invertite (3h/2h) nei servizi
    del triennio; i totali quadrano lo stesso, la copertura per materia no."""
    env = fermi.build()
    for year in (3, 4, 5):
        plan = env["plans"][f"SCI{year}"]
        sto = Service.objects.get(study_plan=plan, subject=env["subjects"]["STO"])
        sci = Service.objects.get(study_plan=plan, subject=env["subjects"]["SCI"])
        sto.class_minutes, sci.class_minutes = sci.class_minutes, sto.class_minutes
        sto.save(); sci.save()
    findings = check_schedule(env["schedule"])
    assert all(f.code == "coverage_mismatch" for f in findings)
    assert len(findings) == 12  # 6 classi del triennio × 2 materie


def test_indisponibilita_di_d06_attiva():
    env = fermi.build()
    activity = Activity.objects.filter(teachers=env["teachers"]["D06"]).first()
    Placement.objects.create(schedule=env["schedule"], activity=activity,
                             day=2, start_slot=0)  # giorno indisponibile
    codes = [f.code for f in check_schedule(env["schedule"])]
    assert "unavailability" in codes


def test_sp_su_una_classe_sotto_il_secondo():
    """Prestazioni del dominio residuo: la colonna S.P. di una classe intera
    (27 attività, orario riempito alla buona) in meno di un secondo."""
    env = fermi.build()
    klass = env["classes"]["1A"]
    acts = list(Activity.objects.filter(classes=klass)
                .order_by("-duration_slots", "id"))
    day, slot = 0, 0
    for a in acts:
        if slot + a.duration_slots > 6:
            day, slot = day + 1, 0
        Placement.objects.create(schedule=env["schedule"], activity=a,
                                 day=day, start_slot=slot)
        slot += a.duration_slots
    state = ScheduleState.build(env["schedule"])
    start = time.perf_counter()
    for a in acts:
        residual_domain(a, state)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"colonna S.P. di 1A in {elapsed:.2f}s"
```

- [ ] **Step 3: Run tests**

Run: `venv/bin/pytest tests/test_fermi_constraints.py tests/test_fermi_representation.py -v`
Expected: i nuovi 5 PASS **e** i 5 test di rappresentazione esistenti ancora
PASS (la fixture è cambiata: verificare di non aver rotto la quadratura).
Se `test_capienza_del_fermi_pulita` fallisse per un deficit reale introdotto
dai giorni di indisponibilità scelti, i giorni in `UNAVAILABLE_DAYS` vanno
allargati (mai il contrario: non indebolire l'analisi per far passare il test)
e la scelta annotata nel commit.

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/pytest`
Expected: tutti verdi.

- [ ] **Step 5: Commit**

```bash
git add tests/fermi.py tests/test_fermi_constraints.py
git commit -m "test: il Fermi arricchito dei vincoli attesi, con l'inversione STO/SCI rilevata"
```

---

### Task 12: Le code del piano 1 e la chiusura documentale

**Files:**
- Create: `tests/test_constraint_negatives.py`
- Modify: `docs/modello-dominio.md` (riga «12 tipi censiti» → 13), `domain/models/institute.py` (nota su `load()`), `CLAUDE.md` (struttura, stato, changelog)

**Interfaces:**
- Consumes: tutto il piano; i due `_EXACTLY_ONE_UNIT` (in `teachers.py` e `constraints.py`), `uniq_partition_per_class`, `RelaxationQuota`, `Break.straddles`.

- [ ] **Step 1: Write the negative tests**

```python
# tests/test_constraint_negatives.py
"""I test negativi rimandati dal piano 1: i CheckConstraint respingono
davvero i dati malformati."""
import pytest
from django.db import IntegrityError

from domain.models import (
    ClassPartition, RelaxationQuota, SchoolClass, StudyPlan, Subject,
    SubjectConstraint, Teacher, TeachingAssignment,
)
from domain.models.curriculum import Discipline
from domain.models.time import Break, TimeGrid

pytestmark = pytest.mark.django_db


@pytest.fixture
def env():
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    partition = ClassPartition.objects.create(school_class=klass, name="X")
    from domain.models import ClassPart
    part = ClassPart.objects.create(name="1A-x", partition=partition)
    teacher = Teacher.objects.create(name="Rossi", last_name="Rossi", first_name="Anna")
    return {"subject": subject, "klass": klass, "partition": partition,
            "part": part, "teacher": teacher}


def test_cattedra_con_due_unita_respinta(env):
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=env["subject"],
            school_class=env["klass"], class_part=env["part"], weekly_minutes=60)


def test_cattedra_senza_unita_respinta(env):
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=env["subject"], weekly_minutes=60)


def test_vincolo_di_materia_con_due_unita_respinto(env):
    with pytest.raises(IntegrityError):
        SubjectConstraint.objects.create(
            school_class=env["klass"], class_part=env["part"],
            subject_a=env["subject"], subject_b=env["subject"],
            type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)


def test_partizione_duplicata_respinta(env):
    with pytest.raises(IntegrityError):
        ClassPartition.objects.create(school_class=env["klass"], name="X")


def test_quota_globale_senza_risorsa_ammessa(env):
    quota = RelaxationQuota.objects.create(
        family=RelaxationQuota.Family.MAX_HOURS, resource=None, max_violations=3)
    assert quota.resource is None


def test_straddles_con_durata_uno_mai_a_cavallo():
    grid = TimeGrid.objects.create(morning_end_slot=4)
    interval = Break.objects.create(grid=grid, boundary_slot=2)
    assert not interval.straddles(start_slot=1, duration_slots=1)
    assert not interval.straddles(start_slot=2, duration_slots=1)
    assert interval.straddles(start_slot=1, duration_slots=2)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_constraint_negatives.py -v`
Expected: 6 PASS (i vincoli esistono già: qui si prova che mordono).
Se uno fallisse, è un **bug reale dello schema** da riportare, non un test da
adattare.

- [ ] **Step 3: Documentation fixes**

1. In `docs/modello-dominio.md`, sezione «I vincoli», sostituire
   `- \`type\` è un enum sui **12 tipi censiti**` con
   `- \`type\` è un enum sui **13 tipi censiti**` (i 9 con etichetta più i
   quattro `Parties…Classe`; l'enum implementato ha 13 valori).
2. In `domain/models/institute.py`, sopra il metodo `load()`:

```python
    # Nota: load() scrive alla prima lettura (get_or_create). Nei percorsi di
    # sola lettura (domain/analysis) si usa objects.filter(pk=1).first().
```

3. In `CLAUDE.md`:
   - nella sezione «Struttura dei documenti», sotto la riga di `domain/`,
     aggiungere: `domain/analysis/` — `il sottosistema di analisi: predicati con causali nominate, dominio residuo (S.P.), capienza` e, sotto `tests/`, aggiornare la descrizione citando i test dell'analisi;
   - nel riquadro «Stato del progetto», aggiornare la nota finale: i predicati
     e l'analisi di capienza **sono implementati** (citare il numero reale di
     test verdi, misurato con `venv/bin/pytest` a suite completa); il piano
     successivo è il **modello CP-SAT** (piano 3);
   - aggiungere in testa al «Changelog» una voce `2026-07-26 (notte, analisi)`
     che riassuma: package `domain/analysis/` (registro con copertura completa
     verificata da test, `ScheduleState` per settimana, conformità, dominio
     residuo, capienza esatta con le due diagnosi EDT riprodotte, comando
     `manage.py analyze`), il Fermi arricchito dei vincoli attesi con
     l'inversione STO/SCI rilevata, e le code del piano 1 chiuse.

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/pytest`
Expected: tutti verdi. Annotare il numero totale di test per il changelog.

- [ ] **Step 5: Commit**

```bash
git add tests/test_constraint_negatives.py docs/modello-dominio.md domain/models/institute.py CLAUDE.md
git commit -m "test+docs: code del piano 1 chiuse e chiusura documentale dell'analisi"
```

---

## Fuori da questo piano (dichiarato)

- **Violatore di Hall** (fase 5 di EDT: sottoinsiemi infattibili su risorse
  incrociate) → piano 3, col solver.
- **Modello CP-SAT** e builder agganciati al registro → piano 3.
- Serializzazione JSON dei findings, UI → con la UI.
- Suggerimento automatico degli alleggerimenti (ordinare i vincoli per
  fallimenti causati): i findings contabili prodotti qui ne sono la base.






