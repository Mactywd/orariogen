# Spike CP-SAT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tradurre cinque vincoli del registro dell'analisi in constraint CP-SAT e verificare, usando il registro stesso come oracolo, che le due facce dello stesso dato siano d'accordo.

**Architecture:** Un package nuovo `domain/solver/`, separato da `domain/analysis/` perché quest'ultimo resti senza `ortools`. I builder si registrano sotto le **stesse chiavi** dei checker. Le variabili sono booleane `x[a][d][s]` («*a* comincia il giorno *d* alla fascia *s*») con una `AddExactlyOne` per attività; griglia e indisponibilità non sono constraint ma **pre-filtri del dominio**; i vincoli di cardinalità poggiano su letterali canalizzati `occupied[k][d][s]`. Prima di tutto questo, ADR-017: la regola di conflitto fra partizioni si corregge in `domain/analysis/state.py` introducendo gli **atomi**.

**Tech Stack:** Python 3, Django 5.1, `ortools` (CP-SAT), pytest + pytest-django, SQLite.

**Spec:** [`docs/superpowers/specs/2026-08-09-solver-cpsat-spike-design.md`](../specs/2026-08-09-solver-cpsat-spike-design.md)

## Global Constraints

- **Ambiente.** Il worktree parte senza venv. Prima di tutto: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`. Tutti i comandi di test in questo piano usano `venv/bin/pytest`.
- **Lingua.** Prosa, commenti, docstring, messaggi di commit in **italiano**. Codice e identificatori in **inglese**, salvo le chiavi dei dizionari di statistiche, che sono in italiano perché finiscono sotto gli occhi dell'utente.
- **Terminologia.** Solo `partition` / `part` / `group`. Mai «sdoppiamento» negli identificatori, mai `subgroup`.
- **Durate in minuti**, mai in ore. Le fasce si contano in slot.
- **Nessuna migrazione.** Questo piano non tocca i modelli: nessun campo nuovo, nessun `makemigrations`.
- **Nessuna query ORM dentro un builder.** Tutto ciò che un builder legge sta nel `SolverContext`, costruito una volta sola. È lo stesso contratto che vale per i checker rispetto a `ScheduleState`.
- **Un constraint i cui letterali provengono tutti da attività congelate non si posta.** È un fatto, non una decisione: un orario esistente già in violazione renderebbe altrimenti `INFEASIBLE` una richiesta che riguarda altre trenta attività. Ogni builder che posta constraint deve controllare `ctx.has_free(...)` o l'equivalente sulla propria lista di letterali.
- **Semplificazione dichiarata sulle settimane.** Solo il builder dell'occupazione distingue le firme di settimana. `MAX_GAP_HOURS` e `SAME_DAY_INCOMPATIBLE` trattano tutte le attività come co-attive. È **conservativo**: può solo vincolare di più, mai di meno, quindi non può produrre una soluzione che l'oracolo rifiuta. Va scritto nel docstring dei due builder, non lasciato implicito.
- **Scostamento dichiarato dalla spec: `works[k][d]` non si implementa.** La spec lo elenca fra i letterali canalizzati, ma nessuno dei cinque builder lo usa — serve ai vincoli di cardinalità sui *giorni* (giorni liberi, mezze giornate, cambi di sede), che sono fuori da questo spike. Si aggiungerà insieme al primo builder che lo chiede. `occupied[k][d][s]` invece serve, ed è implementato.
- **Commit dopo ogni task**, con prefissi `feat(solver):`, `fix(analysis):`, `test:`, `docs:`.
- **Firma dei commit:** ogni messaggio termina con `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Struttura dei file

| file | responsabilità |
|---|---|
| `domain/analysis/state.py` *(modificato)* | `activity_tokens` guadagna gli atomi; `ScheduleState.build` li precalcola una volta |
| `domain/solver/registry.py` *(nuovo)* | `Builder` con i due hook, `register`, `BUILDERS`, `all_builders` |
| `domain/solver/context.py` *(nuovo)* | `SolverContext`: attività, celle ammissibili, token, indice per cella, letterali canalizzati |
| `domain/solver/model.py` *(nuovo)* | `build_model`, `solve`, `apply`, `Solution` |
| `domain/solver/builders/grid.py` *(nuovo)* | pre-filtro: durata, intervalli, festivi |
| `domain/solver/builders/unavailability.py` *(nuovo)* | pre-filtro: indisponibilità rossa su tutta la durata |
| `domain/solver/builders/occupation.py` *(nuovo)* | conflitto e capacità cumulativa, per firma di settimana |
| `domain/solver/builders/time_constraints.py` *(nuovo)* | `MAX_GAP_HOURS`, il budget settimanale di buchi |
| `domain/solver/builders/subject_constraints.py` *(nuovo)* | `SAME_DAY_INCOMPATIBLE` |
| `tests/test_solver_atoms.py` … `tests/test_solver_oracle.py` *(nuovi)* | uno per task |

---

### Task 1: Gli atomi (ADR-017)

Due partizioni sono due modi di dividere **gli stessi** studenti: una parte dell'una e una parte dell'altra condividono studenti e non possono stare nella stessa fascia. Oggi non confliggono. Si corregge cambiando cosa sono i token: gli **atomi** sono le celle del prodotto delle partizioni.

**Files:**
- Modify: `domain/analysis/state.py`
- Test: `tests/test_solver_atoms.py`

**Interfaces:**
- Consumes: niente (primo task)
- Produces: `AtomMap` (dataclass con `.part: dict[int, frozenset[str]]`, `.klass: dict[int, frozenset[str]]`, `.names: dict[str, str]`, classmethod `.build()`); `activity_tokens(activity, assigned_room_id=None, atoms=None)`

- [ ] **Step 1: Preparare l'ambiente del worktree**

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/pytest -q
```

Atteso: 116 passed. Se questo numero non torna, fermarsi e segnalarlo: il piano parte da una suite verde.

- [ ] **Step 2: Scrivere i test che falliscono**

Creare `tests/test_solver_atoms.py`:

```python
"""ADR-017: parti di partizioni diverse condividono studenti e confliggono.
Parti della stessa partizione no — quello è lo sdoppiamento."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.state import AtomMap
from domain.models import ClassPart, ClassPartition, Group
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _partition(klass, name, *part_names):
    partition = ClassPartition.objects.create(school_class=klass, name=name)
    return [ClassPart.objects.create(name=n, partition=partition) for n in part_names]


def _codici(schedule):
    return [f.code for f in check_schedule(schedule)]


def test_parti_di_partizioni_diverse_confliggono():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    ing, ted = _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[ing])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_parti_della_stessa_partizione_non_confliggono():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" not in _codici(env["schedule"])


def test_una_sola_partizione_non_genera_atomi():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    atoms = AtomMap.build()
    assert atoms.klass == {} and atoms.part == {}
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" not in _codici(env["schedule"])


def test_conflitto_anche_per_la_via_del_raggruppamento():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    ing, ted = _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    g = Group.objects.create(name="ALTERNATIVA")
    g.parts.add(rel)
    a = make_activity(env["subject"], groups=[g])
    b = make_activity(env["subject"], parts=[ing])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_la_classe_intera_confligge_con_ogni_parte():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_l_atomo_ha_un_nome_leggibile():
    env = mini_school()
    _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    atoms = AtomMap.build()
    assert len(atoms.klass[env["klass"].pk]) == 4          # prodotto 2 x 2
    assert set(atoms.names.values()) == {"1A (studenti in comune fra partizioni)"}
```

- [ ] **Step 3: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_atoms.py -v`
Atteso: FAIL — `ImportError: cannot import name 'AtomMap'`.

- [ ] **Step 4: Implementare `AtomMap` in `domain/analysis/state.py`**

Aggiungere `from itertools import product` agli import in cima al file, poi inserire subito **prima** di `def activity_tokens(...)`:

```python
@dataclass(frozen=True)
class AtomMap:
    """ADR-017. Due partizioni della stessa classe sono due modi di dividere
    gli stessi studenti: una parte dell'una e una parte dell'altra hanno
    studenti in comune. Gli atomi sono le celle del prodotto delle partizioni,
    così le parti della stessa partizione restano disgiunte (lo sdoppiamento)
    e quelle di partizioni diverse si intersecano.

    Costruito solo per le classi con almeno due partizioni non vuote: altrove
    le mappe restano vuote e le chiavi di occupazione non cambiano di un bit."""

    part: dict    # ClassPart pk → frozenset di atomi
    klass: dict   # SchoolClass pk → frozenset di atomi
    names: dict   # atomo → nome leggibile, per le causali

    @classmethod
    def build(cls):
        by_class = defaultdict(lambda: defaultdict(list))
        for pk, partition_id, class_id in ClassPart.objects.values_list(
                "pk", "partition_id", "partition__school_class_id"):
            by_class[class_id][partition_id].append(pk)
        class_names = dict(SchoolClass.objects.values_list("pk", "name"))
        part, klass, names = {}, {}, {}
        for class_id, partitions in by_class.items():
            blocks = [sorted(parts) for _, parts in sorted(partitions.items()) if parts]
            if len(blocks) < 2:
                continue
            label = f"{class_names.get(class_id, class_id)} (studenti in comune fra partizioni)"
            keys = []
            for combo in product(*blocks):
                key = "atom:{}:{}".format(class_id, "-".join(str(p) for p in combo))
                keys.append(key)
                names[key] = label
                for part_pk in combo:
                    part.setdefault(part_pk, set()).add(key)
            klass[class_id] = frozenset(keys)
        return cls({p: frozenset(v) for p, v in part.items()}, klass, names)


EMPTY_ATOMS = AtomMap({}, {}, {})
```

- [ ] **Step 5: Far passare gli atomi per tutte e tre le vie in `activity_tokens`**

Sostituire il corpo di `activity_tokens` (firma compresa) con:

```python
def activity_tokens(activity, assigned_room_id=None, atoms=None):
    """Chiavi di occupazione e quantità dei materiali di un'attività.
    Regola dei conflitti sulle unità: la classe intera occupa sé stessa, tutte
    le sue parti e tutti i suoi atomi; la parte occupa sé stessa e i propri
    atomi; il raggruppamento occupa le parti membre e i loro atomi. Parti di
    partizioni diverse della stessa classe condividono un atomo, quindi
    confliggono (ADR-017); parti della stessa partizione no."""
    if atoms is None:
        atoms = AtomMap.build()
    keys, materials = set(), {}
    for t in activity.teachers.all():
        keys.add(t.pk)
    for c in activity.classes.all():
        keys.add(c.pk)
        keys.update(ClassPart.objects.filter(
            partition__school_class=c).values_list("pk", flat=True))
        keys |= atoms.klass.get(c.pk, frozenset())
    for p in activity.parts.all():
        keys.add(p.pk)
        keys |= atoms.part.get(p.pk, frozenset())
    for g in activity.groups.all():
        for part_pk in g.parts.values_list("pk", flat=True):
            keys.add(part_pk)
            keys |= atoms.part.get(part_pk, frozenset())
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
```

- [ ] **Step 6: Costruire la mappa una volta sola in `ScheduleState.build`**

In `ScheduleState.build`, subito dopo il ciclo `for r in Resource.objects.values(...)`, aggiungere:

```python
        atoms = AtomMap.build()
        state.resource_names.update(atoms.names)
```

e nella chiamata dentro il ciclo delle attività passare la mappa:

```python
            keys, materials = activity_tokens(
                a, assigned_room_id=pl.assigned_room_id if pl else None,
                atoms=atoms)
```

- [ ] **Step 7: Eseguire i test del task**

Run: `venv/bin/pytest tests/test_solver_atoms.py -v`
Atteso: 6 passed.

- [ ] **Step 8: Eseguire la suite intera — nessuna regressione**

Run: `venv/bin/pytest -q`
Atteso: 122 passed (116 preesistenti + 6 nuovi). Se qualcuno dei 116 fallisce, **non** modificare il test: la promessa è che le classi con meno di due partizioni non cambino comportamento, quindi un test rotto è un bug in `AtomMap.build`.

- [ ] **Step 9: Commit**

```bash
git add domain/analysis/state.py tests/test_solver_atoms.py
git commit -m "fix(analysis): ADR-017, parti di partizioni diverse confliggono

Due partizioni sono due modi di dividere gli stessi studenti: una parte
dell'una e una dell'altra hanno studenti in comune. La regola v1 non lo
vedeva perche' un insieme di token non sa dire due cose opposte sulla
stessa coppia. Gli atomi (le celle del prodotto delle partizioni) lo
risolvono senza toccare l'architettura a intersezione di insiemi.

Aggiunti per tutte e tre le vie con cui una parte entra nelle chiavi:
diretta, via raggruppamento, via espansione della classe intera. Solo per
le classi con almeno due partizioni: altrove nulla cambia.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Il registro dei builder

**Files:**
- Create: `domain/solver/__init__.py`, `domain/solver/registry.py`, `domain/solver/builders/__init__.py`
- Test: `tests/test_solver_registry.py`

**Interfaces:**
- Consumes: `domain.analysis.registry.REGISTRY` (per il test di inclusione)
- Produces: `Builder` (metodi `restrict(self, ctx)` e `build(self, ctx, model)`, entrambi no-op di default), `register(*keys)`, `BUILDERS: dict`, `all_builders() -> list[Builder]`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_registry.py`:

```python
"""Il registro dei builder: stesse chiavi dei checker, package separato."""
import pytest

from domain.analysis.registry import REGISTRY, all_checkers
from domain.solver.registry import BUILDERS, Builder, all_builders, register


def test_register_mette_la_classe_sotto_ogni_chiave():
    @register("prova:uno", "prova:due")
    class Finto(Builder):
        def build(self, ctx, model):
            return None

    try:
        assert BUILDERS["prova:uno"] is Finto
        assert BUILDERS["prova:due"] is Finto
    finally:
        del BUILDERS["prova:uno"], BUILDERS["prova:due"]


def test_all_builders_istanzia_ogni_classe_una_volta_sola():
    tipi = [type(b) for b in all_builders()]
    assert len(tipi) == len(set(tipi))


def test_i_due_hook_sono_no_op_di_default():
    assert Builder().restrict(None) is None
    assert Builder().build(None, None) is None


def test_le_chiavi_dei_builder_sono_chiavi_del_registro_dei_checker():
    all_checkers()   # forza la registrazione dei checker
    all_builders()   # forza la registrazione dei builder
    assert set(BUILDERS) <= set(REGISTRY)


def test_ogni_builder_implementa_almeno_un_hook():
    all_builders()
    for chiave, cls in BUILDERS.items():
        assert (cls.restrict is not Builder.restrict
                or cls.build is not Builder.build), chiave
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_registry.py -v`
Atteso: FAIL — `ModuleNotFoundError: No module named 'domain.solver'`.

- [ ] **Step 3: Creare il package**

`domain/solver/__init__.py`: file vuoto.

`domain/solver/builders/__init__.py`:

```python
"""L'import registra i builder nel BUILDERS. Esteso dai task successivi."""
```

`domain/solver/registry.py`:

```python
"""Il registro dei builder CP-SAT. Stesse chiavi del registro dei predicati
(domain/analysis/registry.py): «una riga di dato, due facce». Package
separato perché domain/analysis non dipenda da ortools — la diagnostica
dev'essere usabile senza tirarsi dietro un solver."""


class Builder:
    """Due tempi diversi, entrambi no-op di default. `restrict` pota il
    dominio *prima* che le variabili esistano — è così che griglia e
    indisponibilità non diventano constraint. `build` posta constraint sulle
    variabili già create. Un builder ne implementa almeno uno."""

    def restrict(self, ctx):
        return None

    def build(self, ctx, model):
        return None


BUILDERS = {}


def register(*keys):
    def decorator(cls):
        for key in keys:
            BUILDERS[key] = cls
        return cls
    return decorator


def all_builders():
    from domain.solver import builders  # noqa: F401 — forza la registrazione
    out, seen = [], set()
    for cls in BUILDERS.values():
        if cls not in seen:
            seen.add(cls)
            out.append(cls())
    return out
```

- [ ] **Step 4: Eseguire i test**

Run: `venv/bin/pytest tests/test_solver_registry.py -v`
Atteso: 5 passed. `BUILDERS` è ancora vuoto, quindi le ultime due asserzioni passano a vuoto: torneranno a mordere man mano che i builder si registrano.

- [ ] **Step 5: Commit**

```bash
git add domain/solver tests/test_solver_registry.py
git commit -m "feat(solver): il registro dei builder, con i due hook

restrict() pota il dominio prima che le variabili esistano, build() posta
constraint dopo. Chiavi condivise col registro dei predicati, package
separato perche' domain/analysis resti senza ortools.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Il contesto del solver

**Files:**
- Create: `domain/solver/context.py`
- Test: `tests/test_solver_context.py`

**Interfaces:**
- Consumes: `domain.analysis.conformity.week_signatures`, `domain.analysis.state.ScheduleState`
- Produces: `SolverContext` con i campi `schedule, grid, signatures, states, activities, free, cells, tokens, capacity, material_quantity, time_rows, subject_rows, x, by_cell`; classmethod `build(schedule, extraction=None)`; metodi `index_cells()`, `has_free(key, day, slot) -> bool`, `occupied(model, key, day, slot) -> BoolVar`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_context.py`:

```python
"""Il contesto: celle ammissibili, congelamento, indice per cella."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Extraction
from domain.solver.context import SolverContext
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_celle_iniziali_secondo_la_durata():
    env = mini_school()
    a = make_activity(env["subject"], slots=1)
    b = make_activity(env["subject"], slots=2)
    ctx = SolverContext.build(env["schedule"])
    assert len(ctx.cells[a.id]) == 30   # 5 giorni x 6 fasce
    assert len(ctx.cells[b.id]) == 25   # 5 giorni x 5 partenze possibili
    assert ctx.free == {a.id, b.id}


def test_attivita_fissa_congelata_alla_sua_cella():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    place(env["schedule"], a, day=2, slot=3)
    ctx = SolverContext.build(env["schedule"])
    assert ctx.cells[a.id] == {(2, 3)}
    assert a.id not in ctx.free


def test_attivita_fissa_mai_piazzata_esce_dal_modello():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    ctx = SolverContext.build(env["schedule"])
    assert a.id not in ctx.activities


def test_estrazione_libera_solo_le_sue_attivita():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], b, day=1, slot=1)
    estrazione = Extraction.objects.create(name="lavoro")
    estrazione.activities.add(a)
    ctx = SolverContext.build(env["schedule"], extraction=estrazione)
    assert ctx.free == {a.id}
    assert ctx.cells[b.id] == {(1, 1)}   # il resto e' dato


def test_token_e_capacita_arrivano_dallo_stato():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx = SolverContext.build(env["schedule"])
    assert env["teacher"].pk in ctx.tokens[a.id]
    assert env["klass"].pk in ctx.tokens[a.id]
    assert ctx.capacity[env["teacher"].pk] == 1


def test_indice_per_cella_e_canalizzazione():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    ctx = SolverContext.build(env["schedule"])
    model = cp_model.CpModel()
    for (d, s) in sorted(ctx.cells[a.id]):
        ctx.x[(a.id, d, s)] = model.NewBoolVar(f"x_{d}_{s}")
    ctx.index_cells()
    key = env["teacher"].pk
    # durata 2: partendo da (0, 0) copre le fasce 0 e 1
    assert (a.id, ctx.x[(a.id, 0, 0)]) in ctx.by_cell[(key, 0, 1)]
    assert ctx.has_free(key, 0, 1) is True
    assert ctx.has_free(key, 0, 99) is False
    occ = ctx.occupied(model, key, 0, 0)
    assert ctx.occupied(model, key, 0, 0) is occ   # memoizzato
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_context.py -v`
Atteso: FAIL — `ModuleNotFoundError: No module named 'domain.solver.context'`.

- [ ] **Step 3: Implementare `domain/solver/context.py`**

```python
"""Lo stato del solver: costruito una volta sola, contiene tutto ciò che i
builder leggono. Nessuna query ORM dentro un builder — è lo stesso contratto
che ScheduleState impone ai checker."""

from collections import defaultdict
from dataclasses import dataclass, field

from domain.analysis.conformity import week_signatures
from domain.analysis.state import ScheduleState
from domain.models import Activity

_IMMOBILE = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


@dataclass
class SolverContext:
    schedule: object
    grid: object
    signatures: list          # [(settimana rappresentante, tutte le settimane)]
    states: dict              # settimana rappresentante → ScheduleState
    activities: dict          # id → Activity presenti nel modello
    free: set                 # id delle attività che il solver può muovere
    cells: dict               # id → set di (giorno, fascia di inizio) ammissibili
    tokens: dict              # id → frozenset di chiavi di occupazione
    capacity: dict            # chiave → capacità simultanea
    material_quantity: dict   # (id attività, chiave) → quantità
    time_rows: list           # righe ResourceTimeConstraint
    subject_rows: list        # [(riga SubjectConstraint, unit_keys precalcolate)]
    x: dict = field(default_factory=dict)        # (id, giorno, fascia) → BoolVar
    by_cell: dict = field(default_factory=dict)  # (chiave, giorno, fascia) → [(id, letterale)]
    _occupied: dict = field(default_factory=dict)

    @classmethod
    def build(cls, schedule, extraction=None):
        signatures = week_signatures(schedule)
        states = {rep: ScheduleState.build(schedule, week=rep) for rep, _ in signatures}
        base = states[signatures[0][0]]
        grid = base.grid
        placed = {p.activity_id: (p.day, p.start_slot)
                  for p in schedule.placements.all()}
        selected = (None if extraction is None
                    else set(extraction.activities.values_list("id", flat=True)))

        activities, free, cells, tokens = {}, set(), {}, {}
        for state in states.values():
            for aid, act in state.activities.items():
                if aid in activities:
                    continue
                movable = (act.immobility not in _IMMOBILE
                           and (selected is None or aid in selected))
                if movable:
                    free.add(aid)
                    cells[aid] = {
                        (d, s)
                        for d in range(grid.days_per_cycle)
                        for s in range(grid.slots_per_day - act.duration_slots + 1)
                    }
                elif aid in placed:
                    # congelata: il dominio è la sua collocazione attuale, e
                    # basta questo a rendere gratis il piazzamento incrementale
                    cells[aid] = {placed[aid]}
                else:
                    # non muovibile e mai piazzata: non c'è niente a cui
                    # congelarla, e nell'orario non occupa nulla. Fuori.
                    continue
                activities[aid] = act
                tokens[aid] = state.tokens[aid]

        material_quantity = {}
        for state in states.values():
            for (aid, key), quantity in state.material_quantity.items():
                if aid in activities:
                    material_quantity[(aid, key)] = quantity

        return cls(
            schedule=schedule, grid=grid, signatures=signatures, states=states,
            activities=activities, free=free, cells=cells, tokens=tokens,
            capacity=base.capacity, material_quantity=material_quantity,
            time_rows=base.time_rows, subject_rows=base.subject_rows,
        )

    def index_cells(self):
        """(chiave, giorno, fascia) → [(id attività, letterale)]. Costruito una
        volta sola dopo la creazione delle variabili: i builder lo leggono, non
        lo ricalcolano."""
        index = defaultdict(list)
        for aid, act in self.activities.items():
            for (d, s) in self.cells[aid]:
                lit = self.x[(aid, d, s)]
                for key in self.tokens[aid]:
                    for slot in range(s, s + act.duration_slots):
                        index[(key, d, slot)].append((aid, lit))
        self.by_cell = dict(index)

    def has_free(self, key, day, slot):
        """C'è almeno un'attività libera che può occupare quella cella? Se no,
        il constraint è un fatto e non una decisione: non si posta."""
        return any(aid in self.free
                   for aid, _ in self.by_cell.get((key, day, slot), ()))

    def occupied(self, model, key, day, slot):
        """Letterale canalizzato: la chiave è occupata in quella cella. Creato
        su richiesta, così esistono solo le canalizzazioni che un vincolo di
        cardinalità chiede davvero."""
        cell = (key, day, slot)
        if cell not in self._occupied:
            var = model.NewBoolVar(f"occ_{key}_{day}_{slot}")
            lits = [lit for _, lit in self.by_cell.get(cell, ())]
            if lits:
                model.AddMaxEquality(var, lits)
            else:
                model.Add(var == 0)
            self._occupied[cell] = var
        return self._occupied[cell]
```

- [ ] **Step 4: Eseguire i test**

Run: `venv/bin/pytest tests/test_solver_context.py -v`
Atteso: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add domain/solver/context.py tests/test_solver_context.py
git commit -m "feat(solver): il contesto, con celle ammissibili e congelamento

Il congelamento incrementale non ha un meccanismo dedicato: un'attivita'
non muovibile ha per dominio la sola cella dove sta gia'. Un'attivita' non
muovibile e mai piazzata esce dal modello, perche' non c'e' niente a cui
congelarla e nell'orario non occupa nulla.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Il modello, `solve` e `apply`

**Files:**
- Create: `domain/solver/model.py`
- Test: `tests/test_solver_model.py`

**Interfaces:**
- Consumes: `SolverContext.build`, `all_builders`
- Produces: `Solution` (frozen dataclass: `status: str`, `placements: dict[int, tuple[int, int]]`, `stats: dict`); `build_model(schedule, extraction=None) -> (CpModel, SolverContext)`; `solve(schedule, extraction=None, time_limit=None) -> Solution`; `apply(solution, schedule) -> None`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_model.py`:

```python
"""Variabili, esecuzione, scrittura dei piazzamenti. Nessun builder registrato
in questo task: qui si verifica solo l'ossatura."""
import pytest

from domain.models import Placement
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_una_variabile_per_cella_e_una_sola_collocazione():
    env = mini_school()
    a = make_activity(env["subject"], slots=2)
    model, ctx = build_model(env["schedule"])
    assert len(ctx.x) == 25
    assert all(chiave[0] == a.id for chiave in ctx.x)


def test_solve_piazza_ogni_attivita_dentro_il_suo_dominio():
    env = mini_school()
    a = make_activity(env["subject"])
    b = make_activity(env["subject"], slots=2)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert set(soluzione.placements) == {a.id, b.id}
    for aid, (giorno, fascia) in soluzione.placements.items():
        assert 0 <= giorno < 5
        assert (giorno, fascia) in build_model(env["schedule"])[1].cells[aid]


def test_apply_scrive_i_piazzamenti():
    env = mini_school()
    a = make_activity(env["subject"])
    soluzione = solve(env["schedule"])
    apply(soluzione, env["schedule"])
    riga = Placement.objects.get(schedule=env["schedule"], activity=a)
    assert (riga.day, riga.start_slot) == soluzione.placements[a.id]


def test_apply_sovrascrive_un_piazzamento_esistente():
    env = mini_school()
    a = make_activity(env["subject"])
    place(env["schedule"], a, day=4, slot=5)
    soluzione = solve(env["schedule"])
    apply(soluzione, env["schedule"])
    assert Placement.objects.filter(schedule=env["schedule"], activity=a).count() == 1


def test_attivita_congelata_resta_dove_sta():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    place(env["schedule"], a, day=3, slot=2)
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id] == (3, 2)


def test_dominio_vuoto_rende_il_modello_infattibile():
    env = mini_school()
    make_activity(env["subject"], slots=7)   # la griglia ne ha 6
    soluzione = solve(env["schedule"])
    assert soluzione.status == "INFEASIBLE"


def test_le_statistiche_ci_sono():
    env = mini_school()
    make_activity(env["subject"])
    stats = solve(env["schedule"]).stats
    assert stats["attivita"] == 1 and stats["libere"] == 1
    assert stats["variabili"] > 0 and stats["secondi"] >= 0
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_model.py -v`
Atteso: FAIL — `ModuleNotFoundError: No module named 'domain.solver.model'`.

- [ ] **Step 3: Implementare `domain/solver/model.py`**

```python
"""Il modello CP-SAT: variabili booleane x[a][d][s], esecuzione, scrittura dei
piazzamenti. L'ordine è obbligato: contesto → restrict() di tutti i builder →
creazione delle variabili sulle celle sopravvissute → build() di tutti."""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from domain.models import Placement
from domain.solver.context import SolverContext
from domain.solver.registry import all_builders

_STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


@dataclass(frozen=True)
class Solution:
    status: str
    placements: dict   # id attività → (giorno, fascia di inizio)
    stats: dict


def build_model(schedule, extraction=None):
    ctx = SolverContext.build(schedule, extraction=extraction)
    builders = all_builders()
    for builder in builders:
        builder.restrict(ctx)

    model = cp_model.CpModel()
    for aid in sorted(ctx.activities):
        lits = []
        for (day, slot) in sorted(ctx.cells[aid]):
            var = model.NewBoolVar(f"x_{aid}_{day}_{slot}")
            ctx.x[(aid, day, slot)] = var
            lits.append(var)
        if lits:
            model.AddExactlyOne(lits)
        else:
            # dominio vuoto: nessuna collocazione sopravvive ai pre-filtri.
            # Il modello è infattibile, e va detto in modo esplicito.
            vuoto = model.NewBoolVar(f"dominio_vuoto_{aid}")
            model.Add(vuoto == 1)
            model.Add(vuoto == 0)

    ctx.index_cells()
    for builder in builders:
        builder.build(ctx, model)
    return model, ctx


def solve(schedule, extraction=None, time_limit=None):
    started = time.monotonic()
    model, ctx = build_model(schedule, extraction=extraction)
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.Solve(model)

    placements = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (aid, day, slot), var in ctx.x.items():
            if solver.Value(var):
                placements[aid] = (day, slot)

    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return Solution(
        status=_STATUS.get(status, str(status)),
        placements=placements,
        stats={
            "attivita": len(ctx.activities),
            "libere": len(ctx.free),
            "variabili": len(proto.variables),
            "constraint": len(proto.constraints),
            "secondi": round(time.monotonic() - started, 3),
        },
    )


def apply(solution, schedule):
    """Scrive i piazzamenti. Il piazzamento è output, mai un campo
    dell'attività: si sovrascrive la riga, non si duplica."""
    for aid, (day, slot) in solution.placements.items():
        Placement.objects.update_or_create(
            schedule=schedule, activity_id=aid,
            defaults={"day": day, "start_slot": slot})
```

- [ ] **Step 4: Eseguire i test**

Run: `venv/bin/pytest tests/test_solver_model.py -v`
Atteso: 7 passed.

- [ ] **Step 5: Eseguire la suite intera**

Run: `venv/bin/pytest -q`
Atteso: 140 passed.

- [ ] **Step 6: Commit**

```bash
git add domain/solver/model.py tests/test_solver_model.py
git commit -m "feat(solver): variabili, solve e apply

Le celle inammissibili non diventano variabili: i pre-filtri girano prima
che il modello esista, cosi' cio' che un checker vieta e' impossibile per
costruzione invece che vietato da un constraint.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: I due pre-filtri — griglia e indisponibilità

Nessuno dei due posta constraint: entrambi tolgono celle dal dominio. È il motivo per cui `Builder` ha due hook.

**Files:**
- Create: `domain/solver/builders/grid.py`, `domain/solver/builders/unavailability.py`
- Modify: `domain/solver/builders/__init__.py`
- Test: `tests/test_solver_prefilters.py`

**Interfaces:**
- Consumes: `SolverContext` (`cells`, `free`, `tokens`, `signatures`, `states`, `grid`, `activities`), `Builder`, `register`
- Produces: `GridBuilder` sotto `"structural:grid"`, `UnavailabilityBuilder` sotto `"structural:unavailability"`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_prefilters.py`:

```python
"""Griglia e indisponibilità: pre-filtri del dominio, non constraint."""
import datetime as dt

import pytest

from domain.models import Break, Holiday, ResourceUnavailability
from domain.solver.model import build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_il_giorno_festivo_esce_dal_dominio():
    env = mini_school()
    Holiday.objects.create(school_year=env["year"], date=dt.date(2026, 9, 16))  # merc. sett. 0
    a = make_activity(env["subject"])
    _, ctx = build_model(env["schedule"])
    assert all(giorno != 2 for (giorno, _) in ctx.cells[a.id])
    assert len(ctx.cells[a.id]) == 24   # 4 giorni x 6 fasce


def test_l_intervallo_non_si_attraversa_se_l_attivita_lo_rispetta():
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=4)
    a = make_activity(env["subject"], slots=2, respects_breaks=True)
    b = make_activity(env["subject"], slots=2)   # non lo rispetta
    _, ctx = build_model(env["schedule"])
    assert (0, 3) not in ctx.cells[a.id]   # coprirebbe le fasce 3 e 4
    assert (0, 3) in ctx.cells[b.id]


def test_l_indisponibilita_rossa_toglie_la_cella():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    _, ctx = build_model(env["schedule"])
    assert (0, 3) not in ctx.cells[a.id]
    assert (0, 2) in ctx.cells[a.id]


def test_l_indisponibilita_vale_su_tutta_la_durata():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    _, ctx = build_model(env["schedule"])
    assert (0, 2) not in ctx.cells[a.id]   # coda sull'indisponibilita'
    assert (0, 3) not in ctx.cells[a.id]
    assert (0, 1) in ctx.cells[a.id]


def test_giallo_e_verde_non_restringono():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="optional")
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=1, slot=3, level="preference")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    _, ctx = build_model(env["schedule"])
    assert (0, 3) in ctx.cells[a.id] and (1, 3) in ctx.cells[a.id]


def test_l_attivita_congelata_non_viene_ripulita():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]], immobility="fixed")
    place(env["schedule"], a, day=0, slot=3)
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id] == (0, 3)   # il piazzamento esistente e' un dato


def test_dominio_azzerato_dai_prefiltri_da_infeasible():
    env = mini_school()
    for giorno in range(5):
        for fascia in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=giorno, slot=fascia, level="hard")
    make_activity(env["subject"], teachers=[env["teacher"]])
    assert solve(env["schedule"]).status == "INFEASIBLE"
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_prefilters.py -v`
Atteso: FAIL — i primi cinque falliscono perché nessuna cella viene tolta (le asserzioni `not in` cadono).

- [ ] **Step 3: Implementare `domain/solver/builders/grid.py`**

```python
"""Griglia: la durata sta nella giornata, l'intervallo non si attraversa, il
giorno festivo non esiste. Pre-filtro del dominio, non constraint.

Un'attività ha **una** collocazione per tutte le sue settimane: un giorno
festivo anche in una sola delle settimane in cui l'attività è attiva esce dal
dominio. È la stessa lettura del checker, che segnalerebbe quella settimana."""

from domain.solver.registry import Builder, register


@register("structural:grid")
class GridBuilder(Builder):
    def restrict(self, ctx):
        grid = ctx.grid
        boundaries = ctx.states[ctx.signatures[0][0]].break_boundaries
        for aid in ctx.free:
            act = ctx.activities[aid]
            holidays = set()
            for rep, _ in ctx.signatures:
                if aid in ctx.states[rep].activities:
                    holidays |= ctx.states[rep].holidays
            ctx.cells[aid] = {
                (day, slot) for (day, slot) in ctx.cells[aid]
                if day < grid.days_per_cycle
                and day not in holidays
                and slot + act.duration_slots <= grid.slots_per_day
                and not (act.respects_breaks and any(
                    slot < b < slot + act.duration_slots for b in boundaries))
            }
```

- [ ] **Step 4: Implementare `domain/solver/builders/unavailability.py`**

```python
"""Indisponibilità rossa: pre-filtro del dominio, su **tutta** la durata
dell'attività. Il checker itera su tutte le fasce del piazzamento, quindi un
filtro che guardasse solo la cella di partenza lascerebbe passare un'attività
di durata ≥ 2 con la coda sull'indisponibilità.

Giallo e verde non restringono nulla: sono violabili, e il loro trattamento
(override globale, preferenze) è fuori da questo spike."""

from collections import defaultdict

from domain.solver.registry import Builder, register


@register("structural:unavailability")
class UnavailabilityBuilder(Builder):
    def restrict(self, ctx):
        blocked = {}
        for rep, _ in ctx.signatures:
            per_key = defaultdict(set)
            for (key, day, slot), level in ctx.states[rep].unavailability.items():
                if level == "hard":
                    per_key[key].add((day, slot))
            blocked[rep] = per_key

        for aid in ctx.free:
            act = ctx.activities[aid]
            forbidden = set()
            for rep, _ in ctx.signatures:
                if aid not in ctx.states[rep].activities:
                    continue
                per_key = blocked[rep]
                for key in ctx.tokens[aid]:
                    forbidden |= per_key.get(key, set())
            if not forbidden:
                continue
            ctx.cells[aid] = {
                (day, slot) for (day, slot) in ctx.cells[aid]
                if not any((day, s) in forbidden
                           for s in range(slot, slot + act.duration_slots))
            }
```

- [ ] **Step 5: Registrare i due moduli**

Sostituire il contenuto di `domain/solver/builders/__init__.py` con:

```python
"""L'import registra i builder nel BUILDERS. Esteso dai task successivi."""
from . import grid, unavailability  # noqa: F401
```

- [ ] **Step 6: Eseguire i test del task**

Run: `venv/bin/pytest tests/test_solver_prefilters.py -v`
Atteso: 7 passed.

- [ ] **Step 7: Eseguire la suite intera**

Run: `venv/bin/pytest -q`
Atteso: 147 passed.

- [ ] **Step 8: Commit**

```bash
git add domain/solver/builders tests/test_solver_prefilters.py
git commit -m "feat(solver): i due pre-filtri, griglia e indisponibilita'

Non postano constraint: tolgono celle dal dominio prima che le variabili
esistano. L'indisponibilita' si valuta su tutta la durata dell'attivita',
non sulla sola cella di partenza, perche' e' cosi' che la legge il checker.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: L'occupazione

Il builder in cui entrano gli atomi del Task 1 e la capacità cumulativa di aule e materiali — un solo meccanismo, come nel checker.

**Files:**
- Create: `domain/solver/builders/occupation.py`
- Modify: `domain/solver/builders/__init__.py`
- Test: `tests/test_solver_occupation.py`

**Interfaces:**
- Consumes: `SolverContext` (`by_cell`, `free`, `capacity`, `material_quantity`, `signatures`, `states`)
- Produces: `OccupationBuilder` sotto `"structural:occupation"`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_occupation.py`:

```python
"""Conflitto di risorsa e capacità cumulativa, per firma di settimana."""
import pytest

from domain import weeks
from domain.models import ClassPart, ClassPartition, Material, Room
from domain.models.activities import ActivityMaterialRequirement
from domain.solver.model import solve
from tests.analysis_helpers import FULL, make_activity, mini_school


pytestmark = pytest.mark.django_db


def _stessa_cella(soluzione, a, b):
    return soluzione.placements[a.id] == soluzione.placements[b.id]


def test_due_attivita_dello_stesso_docente_non_coincidono():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert not _stessa_cella(soluzione, a, b)


def test_il_docente_con_troppe_ore_e_infattibile():
    env = mini_school()
    for _ in range(31):   # la griglia ha 30 fasce
        make_activity(env["subject"], teachers=[env["teacher"]])
    assert solve(env["schedule"]).status == "INFEASIBLE"


def test_la_capacita_simultanea_dell_aula_ammette_due_attivita():
    env = mini_school()
    palestra = Room.objects.create(name="PALESTRA", simultaneous_capacity=2)
    a = make_activity(env["subject"], rooms=[palestra])
    b = make_activity(env["subject"], rooms=[palestra])
    c = make_activity(env["subject"], rooms=[palestra])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    celle = [soluzione.placements[x.id] for x in (a, b, c)]
    assert max(celle.count(cella) for cella in celle) <= 2


def test_la_quantita_di_materiale_e_un_vincolo():
    env = mini_school()
    carrello = Material.objects.create(name="Carrello tablet", simultaneous_capacity=3)
    a = make_activity(env["subject"])
    b = make_activity(env["subject"])
    ActivityMaterialRequirement.objects.create(activity=a, material=carrello, quantity=2)
    ActivityMaterialRequirement.objects.create(activity=b, material=carrello, quantity=2)
    soluzione = solve(env["schedule"])
    assert not _stessa_cella(soluzione, a, b)   # 2 + 2 > 3


def test_maschere_disgiunte_condividono_la_cella():
    env = mini_school()
    prima = weeks.single_week(0) | weeks.single_week(1)
    dopo = weeks.single_week(2) | weeks.single_week(3)
    a = make_activity(env["subject"], teachers=[env["teacher"]], mask=prima)
    b = make_activity(env["subject"], teachers=[env["teacher"]], mask=dopo)
    for _ in range(29):
        make_activity(env["subject"], teachers=[env["teacher"]], mask=FULL)
    # 29 annuali + 2 semestrali in 30 fasce: fattibile solo se a e b coincidono
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert _stessa_cella(soluzione, a, b)


def test_parti_di_partizioni_diverse_non_coincidono():
    env = mini_school()
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[ing])
    soluzione = solve(env["schedule"])
    assert not _stessa_cella(soluzione, a, b)   # ADR-017, dentro il solver


def test_parti_della_stessa_partizione_possono_coincidere():
    env = mini_school()
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    alt = ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    for _ in range(29):
        make_activity(env["subject"], classes=[env["klass"]])
    # 29 attivita' a classe intera + le due parti: stanno in 30 fasce solo se
    # le due parti condividono la cella
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert _stessa_cella(soluzione, a, b)
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_occupation.py -v`
Atteso: FAIL — senza constraint di occupazione il solver piazza tutto nella stessa cella; falliscono i test che chiedono la separazione.

- [ ] **Step 3: Implementare `domain/solver/builders/occupation.py`**

```python
"""Risorsa occupata e capacità cumulativa: un solo meccanismo per le aule con
capacità simultanea > 1 e per i materiali con quantità, esattamente come nel
checker. Qui entrano gli atomi di ADR-017, che sono chiavi come le altre.

È l'unico builder che distingue le firme di settimana: due attività le cui
maschere non si intersecano possono condividere una cella."""

from domain.solver.registry import Builder, register


@register("structural:occupation")
class OccupationBuilder(Builder):
    def build(self, ctx, model):
        posted = set()
        for rep, _ in ctx.signatures:
            active = ctx.states[rep].activities
            for (key, day, slot), entries in ctx.by_cell.items():
                here = [(aid, lit) for aid, lit in entries if aid in active]
                if not any(aid in ctx.free for aid, _ in here):
                    continue   # un fatto, non una decisione
                capacity = ctx.capacity.get(key, 1)
                loads = [(ctx.material_quantity.get((aid, key), 1), lit)
                         for aid, lit in here]
                if sum(quantity for quantity, _ in loads) <= capacity:
                    continue   # non potrebbe superarla nemmeno tutte insieme
                signature = (key, day, slot, frozenset(aid for aid, _ in here))
                if signature in posted:
                    continue   # firme di settimana diverse, stesso constraint
                posted.add(signature)
                model.Add(sum(quantity * lit for quantity, lit in loads) <= capacity)
```

- [ ] **Step 4: Registrare il modulo**

`domain/solver/builders/__init__.py`:

```python
"""L'import registra i builder nel BUILDERS. Esteso dai task successivi."""
from . import grid, occupation, unavailability  # noqa: F401
```

- [ ] **Step 5: Eseguire i test del task**

Run: `venv/bin/pytest tests/test_solver_occupation.py -v`
Atteso: 7 passed.

- [ ] **Step 6: Eseguire la suite intera**

Run: `venv/bin/pytest -q`
Atteso: 154 passed.

- [ ] **Step 7: Commit**

```bash
git add domain/solver/builders tests/test_solver_occupation.py
git commit -m "feat(solver): l'occupazione, con capacita' cumulativa e settimane

Aule con capacita' simultanea e materiali con quantita' passano dallo
stesso constraint, come nel checker. Gli atomi di ADR-017 sono chiavi come
le altre: la regola di conflitto fra partizioni entra nel solver senza una
riga dedicata.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `MAX_GAP_HOURS` — il budget settimanale di buchi

⚠ **Non è una soglia per singolo buco.** `MaxGapChecker` somma i minuti di buco su tutte le mezze giornate della settimana e confronta il totale **una volta sola** (`domain/analysis/checkers/time_constraints.py`, `total` accumulato fuori dal ciclo sui giorni). Tre buchi da un'ora con `D.T.B.` di un'ora e mezza sono una violazione, non tre situazioni legali.

**Files:**
- Create: `domain/solver/builders/time_constraints.py`
- Modify: `domain/solver/builders/__init__.py`
- Test: `tests/test_solver_max_gap.py`

**Interfaces:**
- Consumes: `SolverContext.occupied(model, key, day, slot)`, `SolverContext.has_free`, `ctx.time_rows`
- Produces: `MaxGapBuilder` sotto `ResourceTimeConstraint.Type.MAX_GAP_HOURS`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_max_gap.py`:

```python
"""D.T.B.: budget settimanale di minuti di buco, non soglia per singolo buco."""
import pytest

from domain.models import ResourceTimeConstraint, ResourceUnavailability, Teacher
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = ResourceTimeConstraint.Type


def _solo_queste_fasce(teacher, ammesse):
    """Tutto rosso tranne le celle indicate: costringe la forma della giornata."""
    for giorno in range(5):
        for fascia in range(6):
            if (giorno, fascia) not in ammesse:
                ResourceUnavailability.objects.create(
                    resource=teacher, day=giorno, slot=fascia, level="hard")


def _dtb(teacher, minuti):
    return ResourceTimeConstraint.objects.create(
        resource=teacher, type=T.MAX_GAP_HOURS,
        params={"max_gap_minutes": minuti})


def _scena_due_buchi(env):
    """Due giornate identiche: fascia 0 fissa, fascia 1 vietata, fascia 2 da
    riempire. Ne escono per forza due buchi da 60 minuti, uno per giorno."""
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 2), (1, 0), (1, 2)})
    for giorno in (0, 1):
        fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
        place(env["schedule"], fissa, day=giorno, slot=0)
    return [make_activity(env["subject"], teachers=[docente]) for _ in range(2)]


def test_budget_sufficiente_e_fattibile():
    env = mini_school()
    _scena_due_buchi(env)
    _dtb(env["teacher"], 120)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_due_buchi_da_un_ora_sforano_un_budget_di_un_ora_e_mezza():
    """Il test che distingue budget da soglia. Con una soglia per singolo buco
    ciascuno dei due sarebbe legale (60 <= 90); come budget settimanale la
    somma e' 120 e sfora. E' il caso indicato dalla spec."""
    env = mini_school()
    _scena_due_buchi(env)
    _dtb(env["teacher"], 90)
    assert solve(env["schedule"]).status == "INFEASIBLE"


def test_senza_vincolo_la_stessa_scena_e_fattibile():
    env = mini_school()
    _scena_due_buchi(env)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_il_buco_non_si_conta_a_cavallo_del_pranzo():
    """Fascia 3 (mattina) e fascia 4 (pomeriggio) sono adiacenti nella griglia
    ma stanno in due mezze giornate: fra loro non c'e' nessun buco."""
    env = mini_school()
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 5)})
    fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
    place(env["schedule"], fissa, day=0, slot=0)
    make_activity(env["subject"], teachers=[docente])
    _dtb(docente, 0)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    """Il D.T.B. e' gia' sforato dalle sole attivita' congelate, ma il docente
    non ha niente da piazzare: e' un fatto, non una decisione."""
    env = mini_school()
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 2)})
    for fascia in (0, 2):
        fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
        place(env["schedule"], fissa, day=0, slot=fascia)
    _dtb(docente, 0)
    altro = Teacher.objects.create(name="Neri Ugo", last_name="Neri", first_name="Ugo")
    make_activity(env["subject"], teachers=[altro])
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_max_gap.py -v`
Atteso: FAIL su `test_due_buchi_da_un_ora_sforano_un_budget_di_un_ora` (dà FEASIBLE perché nessun vincolo esiste ancora). Gli altri passano già: sono le guardie che verranno rilette dopo l'implementazione.

- [ ] **Step 3: Implementare `domain/solver/builders/time_constraints.py`**

```python
"""MAX_GAP_HOURS — il D.T.B., «durata tollerata dei buchi».

⚠ È un **budget settimanale**, non una soglia per singolo buco: il checker
somma i minuti di buco su tutte le mezze giornate della settimana e confronta
il totale una volta sola. Qui la stessa cosa, in forma lineare e senza big-M:
per ogni mezza giornata, `covered[s] = before[s] AND after[s]` dice se la
fascia sta fra la prima e l'ultima occupata, e i minuti di buco sono
`slot_minutes * somma(covered[s] - occ[s])` — ogni termine non negativo perché
`occ[s]` implica `covered[s]`.

I buchi non si contano mai a cavallo del pranzo: le due mezze giornate sono
separate, come in `_halves` del checker.

Semplificazione dichiarata: questo builder non distingue le firme di settimana
e tratta tutte le attività come co-attive. È conservativo — può vincolare di
più, mai di meno — quindi non può produrre una soluzione che l'oracolo
rifiuta."""

from domain.models import ResourceTimeConstraint
from domain.solver.registry import Builder, register

T = ResourceTimeConstraint.Type


@register(T.MAX_GAP_HOURS)
class MaxGapBuilder(Builder):
    def build(self, ctx, model):
        grid = ctx.grid
        halves = [range(0, grid.morning_end_slot),
                  range(grid.morning_end_slot, grid.slots_per_day)]
        for row in ctx.time_rows:
            if row.type != T.MAX_GAP_HOURS:
                continue
            key = row.resource_id
            if not any(ctx.has_free(key, day, slot)
                       for day in range(grid.days_per_cycle)
                       for slot in range(grid.slots_per_day)):
                continue   # nessuna decisione da prendere su questa risorsa
            terms = []
            for day in range(grid.days_per_cycle):
                for half in halves:
                    occ = {s: ctx.occupied(model, key, day, s) for s in half}
                    for s in half:
                        before = model.NewBoolVar(f"before_{key}_{day}_{s}")
                        model.AddMaxEquality(before, [occ[i] for i in half if i <= s])
                        after = model.NewBoolVar(f"after_{key}_{day}_{s}")
                        model.AddMaxEquality(after, [occ[j] for j in half if j >= s])
                        covered = model.NewBoolVar(f"covered_{key}_{day}_{s}")
                        model.AddMinEquality(covered, [before, after])
                        terms.append(covered - occ[s])
            if terms:
                model.Add(grid.slot_minutes * sum(terms)
                          <= row.params["max_gap_minutes"])
```

- [ ] **Step 4: Registrare il modulo**

`domain/solver/builders/__init__.py`:

```python
"""L'import registra i builder nel BUILDERS. Esteso dai task successivi."""
from . import grid, occupation, time_constraints, unavailability  # noqa: F401
```

- [ ] **Step 5: Eseguire i test del task**

Run: `venv/bin/pytest tests/test_solver_max_gap.py -v`
Atteso: 5 passed.

- [ ] **Step 6: Eseguire la suite intera**

Run: `venv/bin/pytest -q`
Atteso: 159 passed.

- [ ] **Step 7: Commit**

```bash
git add domain/solver/builders tests/test_solver_max_gap.py
git commit -m "feat(solver): il D.T.B. come budget settimanale di buchi

Il checker somma i minuti di buco su tutte le mezze giornate della
settimana e confronta una volta sola: non e' una soglia per singolo buco.
La traduzione usa covered = before AND after, lineare e senza big-M, e ha
un test che distingue le due semantiche (due buchi da un'ora contro un
budget di un'ora).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: `SAME_DAY_INCOMPATIBLE`

**Files:**
- Create: `domain/solver/builders/subject_constraints.py`
- Modify: `domain/solver/builders/__init__.py`
- Test: `tests/test_solver_same_day.py`

**Interfaces:**
- Consumes: `ctx.subject_rows` (già espanse in `unit_keys` da `ScheduleState`), `ctx.tokens`, `ctx.cells`, `ctx.x`
- Produces: `SameDayBuilder` sotto `SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE`

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_solver_same_day.py`:

```python
"""Incompatibilita' nella giornata: A = B e' il caso dominante nei dati EDT."""
import pytest

from domain.models import ClassPart, ClassPartition, Subject, SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = SubjectConstraint.Type


def _riga(materia_a, materia_b, **unita):
    return SubjectConstraint.objects.create(
        subject_a=materia_a, subject_b=materia_b,
        type=T.SAME_DAY_INCOMPATIBLE, **unita)


def test_la_materia_con_se_stessa_una_volta_al_giorno():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[env["klass"]])
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_sei_ore_della_stessa_materia_in_cinque_giorni_e_infattibile():
    env = mini_school()
    for _ in range(6):
        make_activity(env["subject"], classes=[env["klass"]])
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    assert solve(env["schedule"]).status == "INFEASIBLE"


def test_due_materie_diverse_non_coesistono_nella_giornata():
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(matematica, classes=[env["klass"]])
    _riga(env["subject"], matematica, school_class=env["klass"])
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_la_riga_su_una_parte_vincola_solo_quella_parte():
    """Sei ore su TED sarebbero infattibili se il vincolo di ING la toccasse:
    sei giorni non ci sono. Che l'istanza resti fattibile e' la prova che il
    vincolo non e' tracimato sull'altra parte."""
    env = mini_school()
    partizione = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=partizione)
    ted = ClassPart.objects.create(name="1A_TED", partition=partizione)
    a = make_activity(env["subject"], parts=[ing])
    b = make_activity(env["subject"], parts=[ing])
    for _ in range(6):
        make_activity(env["subject"], parts=[ted])
    _riga(env["subject"], env["subject"], class_part=ing)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_same_day.py -v`
Atteso: FAIL sui primi tre (nessun vincolo esiste: il solver mette tutto lo stesso giorno).

- [ ] **Step 3: Implementare `domain/solver/builders/subject_constraints.py`**

```python
"""SAME_DAY_INCOMPATIBLE — l'incompatibilità nella giornata.

Con A = B (il caso dominante osservato nei dati reali di EDT: non due ore
della stessa materia nello stesso giorno) è «al più un'occorrenza per unità e
giorno». Con A ≠ B è «le due materie non coesistono nella giornata».
L'attività si attribuisce al giorno della sua fascia di partenza, come nel
checker.

Semplificazione dichiarata: questo builder non distingue le firme di settimana
e tratta tutte le attività come co-attive. È conservativo — può vincolare di
più, mai di meno."""

from domain.models import SubjectConstraint
from domain.solver.registry import Builder, register

T = SubjectConstraint.Type


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayBuilder(Builder):
    def build(self, ctx, model):
        for row, keys in ctx.subject_rows:
            if row.type != T.SAME_DAY_INCOMPATIBLE:
                continue
            for day in range(ctx.grid.days_per_cycle):
                a = self._literals(ctx, keys, row.subject_a_id, day)
                if not any(aid in ctx.free for aid, _ in a):
                    continue
                if row.subject_a_id == row.subject_b_id:
                    if len(a) > 1:
                        model.Add(sum(lit for _, lit in a) <= 1)
                    continue
                b = self._literals(ctx, keys, row.subject_b_id, day)
                if not b:
                    continue
                ha_a = model.NewBoolVar(f"ha_{row.subject_a_id}_{row.pk}_{day}")
                model.AddMaxEquality(ha_a, [lit for _, lit in a])
                ha_b = model.NewBoolVar(f"ha_{row.subject_b_id}_{row.pk}_{day}")
                model.AddMaxEquality(ha_b, [lit for _, lit in b])
                model.Add(ha_a + ha_b <= 1)

    @staticmethod
    def _literals(ctx, keys, subject_id, day):
        out = []
        for aid, act in ctx.activities.items():
            if act.subject_id != subject_id or not (ctx.tokens[aid] & keys):
                continue
            for (d, s) in sorted(ctx.cells[aid]):
                if d == day:
                    out.append((aid, ctx.x[(aid, d, s)]))
        return out
```

- [ ] **Step 4: Registrare il modulo**

`domain/solver/builders/__init__.py`:

```python
"""L'import registra i builder nel BUILDERS."""
from . import (grid, occupation, subject_constraints,  # noqa: F401
               time_constraints, unavailability)
```

- [ ] **Step 5: Eseguire i test del task**

Run: `venv/bin/pytest tests/test_solver_same_day.py -v`
Atteso: 5 passed.

- [ ] **Step 6: Eseguire la suite intera, e con essa il registro**

Run: `venv/bin/pytest -q`
Atteso: 164 passed. In particolare `tests/test_solver_registry.py` ora ha cinque chiavi vere da controllare: se una di esse non fosse una chiave del registro dei checker, `test_le_chiavi_dei_builder_sono_chiavi_del_registro_dei_checker` fallirebbe.

- [ ] **Step 7: Commit**

```bash
git add domain/solver/builders tests/test_solver_same_day.py
git commit -m "feat(solver): l'incompatibilita' di materia nella giornata

A = B e' il caso dominante nei dati reali di EDT (non due ore della stessa
materia nello stesso giorno) ed e' una somma <= 1; A != B diventa la non
coesistenza di due indicatori di giornata.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: L'oracolo

Il criterio di riuscita dello spike, e l'unico. Una soluzione del solver, riscritta nei `Placement` e riletta da `check_schedule`, non deve generare **alcun finding `HARD` nelle cinque famiglie modellate**. Il registro dei predicati è il test: non se ne scrive un altro.

**Files:**
- Create: `tests/test_solver_oracle.py`
- Modify: `tests/test_solver_registry.py`
- Test: entrambi

**Interfaces:**
- Consumes: `solve`, `apply`, `check_schedule`, `tests.fermi.build`
- Produces: le misure (stato, tempo, variabili, constraint) da riportare nel Task 10

- [ ] **Step 1: Scrivere il test dell'oracolo**

Creare `tests/test_solver_oracle.py`:

```python
"""Il criterio di riuscita: solve → apply → check_schedule → zero HARD nelle
cinque famiglie modellate. Il registro dei predicati e' l'oracolo del solver:
le due facce sono state scritte dai lati opposti dello stesso dato."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (
    Break, ClassPart, ClassPartition, Extraction, ResourceTimeConstraint,
    ResourceUnavailability, SchoolClass, Subject, SubjectConstraint, Teacher,
)
from domain.solver.model import apply, solve
from tests import fermi
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db

# le causali delle cinque famiglie modellate, e solo quelle
CODICI = {
    "resource_occupied", "resource_occupied_locked", "resource_peak",   # occupazione
    "unavailability",                                                   # indisponibilita'
    "slot_out_of_grid", "break_straddled", "holiday",                   # griglia
    "max_gap",                                                          # D.T.B.
    "subject_same_day",                                                 # materia
}


def violazioni(schedule):
    return [f for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in CODICI]


def _scuola_media():
    """Tre classi, tre docenti, tutte e cinque le famiglie attive. Dimensionata
    con margine: se risulta infattibile, il bug e' nella traduzione, non
    nell'istanza."""
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=4)
    italiano = env["subject"]
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    storia = Subject.objects.create(
        code="STO", name="Storia", discipline=env["discipline"])

    classi = [env["klass"]]
    for nome in ("1B", "1C"):
        classi.append(SchoolClass.objects.create(
            name=nome, study_plan=env["plan"], year=1))

    docenti = {"ITA": env["teacher"]}
    for codice, cognome, nome in (("MAT", "Bruni", "Ivo"), ("STO", "Sala", "Rita")):
        docenti[codice] = Teacher.objects.create(
            name=f"{cognome} {nome}", last_name=cognome, first_name=nome)

    # due partizioni su 1A: gli atomi di ADR-017 entrano nel modello
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)

    for classe in classi:
        for codice, materia in (("ITA", italiano), ("MAT", matematica), ("STO", storia)):
            for _ in range(2):
                make_activity(materia, teachers=[docenti[codice]], classes=[classe])
    make_activity(matematica, teachers=[docenti["MAT"]], classes=[classi[1]],
                  slots=2, respects_breaks=True)
    make_activity(italiano, parts=[rel])
    make_activity(italiano, parts=[ing])

    for fascia in range(6):
        ResourceUnavailability.objects.create(
            resource=docenti["STO"], day=4, slot=fascia, level="hard")
    for fascia in (1, 2):
        ResourceUnavailability.objects.create(
            resource=docenti["ITA"], day=0, slot=fascia, level="hard")
    ResourceTimeConstraint.objects.create(
        resource=docenti["ITA"], type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 240})
    SubjectConstraint.objects.create(
        subject_a=italiano, subject_b=italiano, school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    return env


def test_oracolo_sulla_scuola_media():
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"]) == []


def test_oracolo_sul_fermi_per_una_classe():
    """Le attivita' di 2A libere, tutto il resto fuori dal modello. 2A e' la
    classe che passa dal docente D09, indisponibile tre giorni su cinque."""
    dataset = fermi.build()
    classe = dataset["classes"]["2A"]
    estrazione = Extraction.objects.create(name="2A")
    estrazione.activities.set(classe.activities.all())
    soluzione = solve(dataset["schedule"], extraction=estrazione, time_limit=60)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert len(soluzione.placements) == classe.activities.count()
    apply(soluzione, dataset["schedule"])
    assert violazioni(dataset["schedule"]) == []


def test_fermi_intero_misurato():
    """Il Fermi ha le classi del triennio a 30 ore su una griglia di 30 fasce:
    non e' noto se sia fattibile. Qualunque cosa il solver restituisca, deve
    essere corretta — e le misure vanno riportate."""
    dataset = fermi.build()
    soluzione = solve(dataset["schedule"], time_limit=120)
    print("\nFermi intero:", soluzione.status, soluzione.stats)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    if soluzione.placements:
        apply(soluzione, dataset["schedule"])
        assert violazioni(dataset["schedule"]) == []
```

- [ ] **Step 2: Aggiungere l'elenco esplicito dei cinque al test del registro**

In fondo a `tests/test_solver_registry.py`:

```python
def test_i_cinque_builder_dello_spike():
    from domain.models import ResourceTimeConstraint, SubjectConstraint
    all_builders()
    assert set(BUILDERS) == {
        "structural:grid",
        "structural:unavailability",
        "structural:occupation",
        ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE,
    }
```

- [ ] **Step 3: Eseguire i test dell'oracolo, con l'output visibile**

Run: `venv/bin/pytest tests/test_solver_oracle.py tests/test_solver_registry.py -v -s`

Atteso: 3 + 6 passed, e nella cattura la riga `Fermi intero: … {...}`.

**Se un test dell'oracolo fallisce, non è l'oracolo a essere sbagliato.** Il finding che compare dice quale delle cinque traduzioni diverge dal proprio checker: si legge la causale, si apre il checker corrispondente, si corregge il *builder*. Non si allarga `CODICI`, non si allenta l'asserzione, non si tocca il checker.

- [ ] **Step 4: Annotare le misure**

Trascrivere in un file di lavoro (verrà usato nel Task 10) i numeri stampati dal terzo test: `status`, `attivita`, `libere`, `variabili`, `constraint`, `secondi`. Sono la fotografia dello spike con cinque vincoli, da confrontare quando saranno ventisette.

```bash
venv/bin/pytest tests/test_solver_oracle.py::test_fermi_intero_misurato -q -s | tee /tmp/misure-spike.txt
```

- [ ] **Step 5: Eseguire la suite intera**

Run: `venv/bin/pytest -q`
Atteso: 168 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/test_solver_oracle.py tests/test_solver_registry.py
git commit -m "test: l'oracolo, il criterio di riuscita dello spike

Una soluzione del solver riscritta nei Placement e riletta da
check_schedule non deve produrre alcun finding HARD nelle cinque famiglie
modellate. Il registro dei predicati e' il test del solver: le due facce
sono state scritte dai lati opposti dello stesso dato, quindi un accordo
non e' una tautologia.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Documentazione

**Files:**
- Modify: `CLAUDE.md`, `docs/decisioni.md`

**Interfaces:**
- Consumes: le misure annotate nel Task 9
- Produces: niente codice

- [ ] **Step 1: Marcare ADR-017 come implementato**

In `docs/decisioni.md`, nella voce ADR-017, sostituire la frase che rimanda l'implementazione al piano 3 con:

```markdown
**Implementato** il 2026-08-09 nello spike CP-SAT: gli **atomi**, cioè le celle
del prodotto delle partizioni, calcolate in `domain/analysis/state.py`
(`AtomMap`). Le parti della stessa partizione restano disgiunte, quelle di
partizioni diverse condividono almeno un atomo. Nessun campo nuovo, nessuna
migrazione, e nessun effetto sulle classi con meno di due partizioni.
```

- [ ] **Step 2: Aggiornare la struttura dei documenti in `CLAUDE.md`**

Nel blocco della struttura, sotto `domain/`, aggiungere la riga:

```
  solver/               lo spike CP-SAT: registro dei builder, contesto, modello, cinque vincoli
```

- [ ] **Step 3: Aggiornare lo stato del progetto in `CLAUDE.md`**

Nella nota sullo stato, sostituire «il piano successivo è il **modello CP-SAT** (piano 3)» con:

```markdown
> lo **spike CP-SAT è implementato** (`domain/solver/`): cinque vincoli su
> ventisette, scelti per attraversare i tre pattern di traduzione, e l'oracolo
> tiene — una soluzione del solver riletta da `check_schedule` non produce
> alcun finding `HARD` nelle famiglie modellate. Il passo successivo è la spec
> del **modello completo**: i ventidue vincoli restanti, gli alleggerimenti a
> quota, l'ottimizzazione lessicografica, l'assegnazione delle aule e il
> violatore di Hall.
```

Se la frase citata non è più letteralmente quella, adattare mantenendo il senso: non aggiungere una variante accanto alla vecchia, correggerla.

- [ ] **Step 4: Scrivere la voce di changelog**

In cima al changelog di `CLAUDE.md`, aggiungere una voce datata **2026-08-09** che riporti, con i numeri veri annotati nel Task 9:

1. **ADR-017 chiuso.** Gli atomi: perché un insieme di token non sapeva esprimere la regola, e perché il prodotto delle partizioni la esprime senza toccare l'architettura. Le tre vie con cui una parte entra nelle chiavi.
2. **Lo spike.** Cinque vincoli su ventisette, scelti per attraversare i tre pattern di traduzione. Package separato, chiavi condivise, `domain/analysis` ancora senza ortools.
3. **La correzione sul `D.T.B.`** — il vincolo era stato tradotto come soglia per singolo buco, mentre il checker somma su tutta la settimana. Vale la pena scriverla: è il tipo di errore che l'oracolo esiste per intercettare, e qui è stato intercettato in fase di design.
4. **Le misure** sul Fermi: stato, attività, variabili, constraint, secondi.
5. **Cosa resta fuori**, con l'elenco della spec.

- [ ] **Step 5: Verificare che la suite sia ancora verde**

Run: `venv/bin/pytest -q`
Atteso: 168 passed.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md docs/decisioni.md
git commit -m "docs: lo spike CP-SAT e la chiusura di ADR-017

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Fuori da questo piano

Dalla spec, e da non reintrodurre di soppiatto:

- gli **altri ventidue vincoli** del registro;
- **alleggerimenti e quote** (`RelaxationQuota` resta a schema, inutilizzato);
- **ottimizzazione lessicografica** e criteri di qualità: `solve()` si ferma al primo `FEASIBLE`;
- **assegnazione delle aule** come seconda fase;
- **violatore di Hall**;
- un comando `manage.py solve`: lo spike è API e test;
- qualunque **deroga dichiarata** alla regola di conflitto fra partizioni.
