# L'assegnazione delle aule — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** assegnare a ogni attività piazzata che chiede un'aula una delle aule
candidate, in una **seconda fase** distinta dal piazzamento, scrivendo
`Placement.assigned_room`.

**Architecture:** un secondo modello CP-SAT, piccolo e separato
(`domain/solver/rooms.py`): un booleano per coppia (attività, aula candidata),
pre-filtri su sede e indisponibilità, capienza simultanea per (aula, giorno,
fascia, firma di settimana) con il residuo di ADR-018, e la **catena
lessicografica che esiste già** (`solve_chain`) su due livelli — i minuti senza
aula, poi i cambi rispetto alla ripartizione precedente. La rinuncia è ammessa e
**nominata** da un checker nuovo, come lo scarto del pezzo 3.

**Tech Stack:** Django 5 + `ortools` CP-SAT + pytest. Il virtualenv è `venv/`:
ogni comando va lanciato come `venv/bin/pytest` / `venv/bin/python`.

**Spec:** [`docs/superpowers/specs/2026-08-27-assegnazione-aule-design.md`](../specs/2026-08-27-assegnazione-aule-design.md)

## Global Constraints

Copiati dalla spec e dalle convenzioni di `CLAUDE.md`. Valgono per ogni task.

- **Documenti in italiano, codice e identificatori in inglese.** I nomi dei
  test sono in italiano (`test_l_aula_indisponibile_esce_dalle_candidate`), come
  tutta la suite esistente.
- **Niente query ORM dentro un `check()` di checker**: lo stato si materializza
  una volta in `ScheduleState`. Lo stesso contratto vale per il contesto della
  fase aule: le query stanno in `RoomContext.build`, mai nel modello.
- **ADR-018**: `INFEASIBLE` che nasce dal *vietare un peggioramento* è ammesso;
  `INFEASIBLE` che nasce dal *pretendere una riparazione* no. Tutti i tetti si
  postano sul residuo `max(0, capienza − carico congelato)`.
- **La regola della casa sui test**: il test che dimostra che un vincolo morde
  **forza la violazione e attende `INFEASIBLE`** (qui con
  `allow_unassigned=False`), mai «risolvi e guarda dove è finita».
- **Verifica per mutazione**: ogni task si chiude spegnendo il codice appena
  scritto e contando i rossi. Un test che resta verde quando il codice che
  afferma sparisce non sta affermando niente, e va riscritto prima di committare.
- **Le firme di settimana sono una dimensione**: ogni vincolo si posta per
  `(rep, _) in ctx.signatures`, mai una volta sola sull'unione.
- **Suite verde a fine task**: `venv/bin/pytest -q`. Baseline all'inizio del
  piano: **612 passed, 16 skipped**.

---

### Task 1: Il checker della richiesta insoddisfatta, e l'occupazione a candidata unica

Chiude la §1 e la §1.1 della spec. Non tocca il solver: dopo questo task
l'analisi sa **dire** che una richiesta d'aula è aperta, e nessuno la soddisfa
ancora.

**Files:**
- Create: `domain/analysis/checkers/room_assignment.py`
- Modify: `domain/analysis/state.py` (il dizionario `assigned_room` e il ramo
  `else` di `activity_tokens`)
- Modify: `domain/analysis/causali.py` (la causale nuova)
- Modify: `tests/test_solver_registry_completo.py` (28 → 29 checker, terza
  assenza dichiarata)
- Test: `tests/test_analysis_room_assignment.py`

**Interfaces:**
- Consumes: `ScheduleState` (`activities`, `placed`, `tokens`, `subject_names`),
  `Checker`/`register` da `domain.analysis.registry`, `Finding`/`Severity`.
- Produces:
  - `ScheduleState.assigned_room: dict` — `activity_id → room_id`, presente solo
    per le attività con un `Placement` che porta `assigned_room`. I task 2 e 3
    lo leggono per distinguere le decisioni dalle congelate.
  - la chiave di registro `"structural:room_assignment"` e il codice di causale
    `"room_unassigned"`.

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_analysis_room_assignment.py`:

```python
"""La richiesta d'aula insoddisfatta, e l'occupazione a candidata unica."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.state import ScheduleState, activity_tokens
from domain.models import Room
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _codici(schedule):
    return [f.code for f in check_schedule(schedule)]


def test_l_attivita_piazzata_che_chiede_un_aula_senza_assegnazione_e_nominata():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert "room_unassigned" in _codici(env["schedule"])


def test_con_l_aula_assegnata_la_richiesta_e_chiusa():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    assert "room_unassigned" not in _codici(env["schedule"])


def test_l_attivita_non_piazzata_non_chiede_nessuna_aula():
    """Senza collocazione non c'e' nessuna cella da occupare: la richiesta non
    esiste ancora, e nominarla sarebbe rumore su ogni orario vuoto."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    assert "room_unassigned" not in _codici(env["schedule"])


def test_chi_non_chiede_aule_non_e_mai_nominato():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    assert "room_unassigned" not in _codici(env["schedule"])


def test_due_candidate_non_occupano_finche_nessuna_e_assegnata():
    """Sovrastimare inventerebbe conflitti che l'assegnazione risolverebbe:
    e' il falso positivo per cui il violatore di Hall e' stato riscritto."""
    env = mini_school()
    p1 = Room.objects.create(name="PALESTRA 1")
    p2 = Room.objects.create(name="PALESTRA 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    keys, _ = activity_tokens(a)
    assert p1.pk not in keys and p2.pk not in keys


def test_la_candidata_unica_occupa_anche_senza_assegnazione():
    """A cardinalita' uno la scelta e' determinata, quindi occupare e' esatto —
    ed e' il prodotto: un'attivita' porta il conto di tutte e cinque le
    risorse, aula compresa."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], rooms=[lab])
    keys, _ = activity_tokens(a)
    assert lab.pk in keys


def test_l_assegnazione_vince_sulle_candidate():
    env = mini_school()
    p1 = Room.objects.create(name="PALESTRA 1")
    p2 = Room.objects.create(name="PALESTRA 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    keys, _ = activity_tokens(a, assigned_room_id=p2.pk)
    assert p2.pk in keys and p1.pk not in keys


def test_lo_stato_registra_l_aula_assegnata():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    state = ScheduleState.build(env["schedule"])
    assert state.assigned_room == {a.id: lab.pk}
```

- [ ] **Step 2: Esegui e verifica che falliscano**

Run: `venv/bin/pytest tests/test_analysis_room_assignment.py -q`
Expected: FAIL — `AttributeError: 'ScheduleState' object has no attribute
'assigned_room'` e i `room_unassigned` assenti dai codici.

- [ ] **Step 3: Aggiungi `assigned_room` allo stato**

In `domain/analysis/state.py`, dentro `ScheduleState.__init__`, accanto a
`self.placed = {}`:

```python
        self.assigned_room = {}       # id → room_id assegnata (solo se piazzata)
```

e in `ScheduleState.build`, nel ramo che già chiama `state.place(...)`:

```python
            if pl is not None:
                state.place(a, pl.day, pl.start_slot)
                if pl.assigned_room_id is not None:
                    state.assigned_room[a.id] = pl.assigned_room_id
```

- [ ] **Step 4: Restringi il ramo `else` di `activity_tokens`**

Nello stesso file, sostituisci il ramo delle aule dichiarate:

```python
    if assigned_room_id is not None:
        keys.add(assigned_room_id)
    else:
        # ⚠ Solo a **candidata unica**: le aule dichiarate sono l'insieme fra
        # cui la seconda fase sceglie (spec §1). Con due o piu' candidate
        # occuparle tutte inventerebbe conflitti che l'assegnazione
        # risolverebbe da sola; con una sola la scelta e' determinata, quindi
        # occupare non e' una stima, e' esatto.
        rooms = list(activity.rooms.all())
        if len(rooms) == 1:
            keys.add(rooms[0].pk)
```

- [ ] **Step 5: Aggiungi la causale**

In `domain/analysis/causali.py`, dentro `CAUSALI`, sotto il blocco
dell'occupazione:

```python
    # assegnazione delle aule (seconda fase)
    "room_unassigned": "{subject}, nessuna aula assegnata",
```

- [ ] **Step 6: Scrivi il checker**

Crea `domain/analysis/checkers/room_assignment.py`:

```python
"""La richiesta d'aula insoddisfatta: l'attivita' dichiara le aule fra cui
sceglie e nessuna le e' stata assegnata.

Serve perche' la seconda fase puo' **rinunciare**, come il piazzamento puo'
scartare: senza un finding che lo dica, «non assegnare niente» sarebbe una
soluzione pulita per l'oracolo differenziale — zero occupazioni d'aula, zero
findings, verde. E' la stessa vacuita' che `structural:placement` ha chiuso per
lo scarto.

⚠ Il finding descrive un orario **incompleto**, non illegale: `HARD` perche' e'
cio' che va risolto, non perche' la lezione sia in violazione.

⚠ Nessuna eccezione per la candidata unica. Finche' `assigned_room` e' NULL la
richiesta e' aperta; che la scelta sia forzata riguarda `activity_tokens`, non
il catalogo delle causali. La fase la chiudera' e il finding sparira'."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.analysis.state import resource_sort_key


@register("structural:room_assignment")
class RoomAssignmentChecker(Checker):
    def check(self, state, resources=None):
        for aid, act in state.activities.items():
            if aid not in state.placed or aid in state.assigned_room:
                continue
            # `rooms` e' nel prefetch di ScheduleState.build: nessuna query qui.
            candidate = sorted(r.pk for r in act.rooms.all())
            if not candidate:
                continue
            if resources is not None and not (set(candidate) & set(resources)):
                continue
            yield Finding(
                "room_unassigned",
                causali.message("room_unassigned",
                                subject=state.subject_names[act.subject_id]),
                Severity.HARD,
                resources=tuple(sorted(candidate, key=resource_sort_key)),
                activities=(aid,),
                quantities={"minutes": act.duration_minutes,
                            "candidates": len(candidate)},
            )
```

Poi registralo in `domain/analysis/checkers/__init__.py`, seguendo la forma
delle righe già presenti (import del modulo perché il decoratore giri).

- [ ] **Step 7: Aggiorna il test di completezza del registro**

In `tests/test_solver_registry_completo.py`: porta `len(CHECKERS)` a **29**,
lascia `len(BUILDERS)` a **26**, aggiungi `"structural:room_assignment"`
all'insieme `senza_builder` di `test_il_registro_dei_builder_e_completo`, e
aggiungi il test che **dichiara** la terza assenza:

```python
def test_structural_room_assignment_non_ha_un_builder_ed_e_voluto():
    """`RoomAssignmentChecker` ha una traduzione, ma vive in un **altro
    modello**: la seconda fase (`domain/solver/rooms.py`), che gira sui
    piazzamenti gia' scritti. I builder di questo registro postano sul modello
    del **piazzamento**, dove l'aula non e' ancora una decisione.

    Come per `structural:coverage` e `structural:placement`, l'assenza e'
    dichiarata qui perche' non sembri una dimenticanza."""
    assert "structural:room_assignment" in CHECKERS
    assert "structural:room_assignment" not in BUILDERS
```

- [ ] **Step 8: Esegui i test del task**

Run: `venv/bin/pytest tests/test_analysis_room_assignment.py tests/test_solver_registry_completo.py -q`
Expected: PASS.

- [ ] **Step 9: Esegui la suite intera**

Run: `venv/bin/pytest -q`
Expected: **612 passed** più i test nuovi, 16 skipped. ⚠ Se
`tests/test_solver_occupation.py` o `tests/test_solver_sites.py` diventano
rossi, il ramo `else` è stato ristretto **troppo**: quei tre test dichiarano
una sola aula e devono continuare a vincolare il piazzamento.

- [ ] **Step 10: Verifica per mutazione**

Sostituisci il corpo di `RoomAssignmentChecker.check` con `return; yield` e
riesegui `venv/bin/pytest tests/test_analysis_room_assignment.py -q`: devono
diventare rossi **due** test (quello della richiesta nominata e nessun altro
dei tre negativi). Poi rimetti `len(rooms) == 1` a `len(rooms) >= 1` in
`activity_tokens` e verifica che diventi rosso
`test_due_candidate_non_occupano_finche_nessuna_e_assegnata` e **nessun altro**.
Ripristina entrambe.

- [ ] **Step 11: Commit**

```bash
git add domain/analysis tests/test_analysis_room_assignment.py tests/test_solver_registry_completo.py
git commit -m "feat(analysis): la richiesta d'aula insoddisfatta, e l'occupazione a candidata unica"
```

---

### Task 2: Il contesto della fase e i pre-filtri

Chiude §2.1 e §2.2. Nessun modello ancora: si costruisce ciò che il modello
leggerà, e i pre-filtri si provano **guardando le candidate**, non risolvendo.

**Files:**
- Create: `domain/solver/rooms.py`
- Test: `tests/test_solver_rooms_context.py`

**Interfaces:**
- Consumes: `week_signatures` da `domain.analysis.conformity`, `ScheduleState`,
  `ScheduleState.assigned_room` (Task 1), `Resource.Kind`, `Room`.
- Produces:
  - `RoomContext` con i campi: `schedule`, `signatures`, `states`, `requests`
    (`aid → Activity`), `candidates` (`aid → set(room_id)`), `previous`
    (`aid → room_id`), `held` (`aid → room_id`, le non-decisioni),
    `ignora_opzionali` (`frozenset`).
  - `RoomContext.build(schedule, ignora_opzionali=()) -> RoomContext`.

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_solver_rooms_context.py`:

```python
"""Il contesto della seconda fase: chi chiede un'aula, e quali restano."""
import datetime as dt

import pytest

from domain.models import Activity, Resource, ResourceUnavailability, Room, Site
from domain.solver.rooms import RoomContext
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_chiede_un_aula_solo_chi_e_piazzato_e_dichiara_candidate():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    chiede = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], chiede, 0, 0)
    make_activity(env["subject"], rooms=[lab])          # non piazzata
    senza = make_activity(env["subject"])               # non chiede aule
    place(env["schedule"], senza, 1, 0)
    ctx = RoomContext.build(env["schedule"])
    assert set(ctx.requests) == {chiede.id}


def test_l_immobile_con_la_sua_aula_non_e_una_decisione():
    """Bloccare una lezione in EDT significa non toccarla: tiene l'aula che ha,
    e quell'aula consuma capienza senza essere una scelta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], a, 0, 0, room=lab)
    ctx = RoomContext.build(env["schedule"])
    assert a.id not in ctx.requests
    assert ctx.held == {a.id: lab.pk}


def test_l_immobile_senza_aula_resta_una_decisione():
    """Il blocco riguarda l'aula che ha, non quella che non ha (spec §2.4):
    un laboratorio fissato a mano in griglia dev'essere assegnabile."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert a.id in ctx.requests


def test_l_aula_di_un_altra_sede_esce_dalle_candidate():
    env = mini_school()
    principale = Site.objects.create(name="Principale")
    succursale = Site.objects.create(name="Succursale")
    qui = Room.objects.create(name="LAB QUI", site=principale)
    la = Room.objects.create(name="LAB LA", site=succursale)
    a = make_activity(env["subject"], rooms=[qui, la], site=principale)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {qui.pk}


def test_senza_sede_sull_attivita_non_si_filtra_per_sede():
    """La sede e' dichiarata sull'attivita' ed e' da li' che la legge
    `SiteTransitionChecker`: dedurla dall'aula creerebbe due sorgenti di
    verita' per la stessa cosa."""
    env = mini_school()
    succursale = Site.objects.create(name="Succursale")
    la = Room.objects.create(name="LAB LA", site=succursale)
    a = make_activity(env["subject"], rooms=[la])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {la.pk}


def test_l_aula_indisponibile_esce_dalle_candidate():
    env = mini_school()
    libero = Room.objects.create(name="LAB LIBERO")
    occupato = Room.objects.create(name="LAB CHIUSO")
    ResourceUnavailability.objects.create(
        resource=occupato, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[libero, occupato])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {libero.pk}


def test_l_indisponibilita_sulla_seconda_fascia_di_un_blocco_conta():
    """Il pre-filtro guarda **tutta** la durata: e' l'errore che
    `UnavailabilityBuilder` dichiara di aver gia' commesso una volta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=1, level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[lab], slots=2)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == set()


def test_la_gialla_si_rispetta_come_la_rossa():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.OPTIONAL)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert RoomContext.build(env["schedule"]).candidates[a.id] == set()


def test_l_override_delle_gialle_e_per_tipo_di_risorsa():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.OPTIONAL)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"],
                            ignora_opzionali=(Resource.Kind.ROOM,))
    assert ctx.candidates[a.id] == {lab.pk}


def test_il_verde_non_restringe():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.PREFERENCE)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert RoomContext.build(env["schedule"]).candidates[a.id] == {lab.pk}


def test_l_aula_di_prima_e_registrata_per_la_stabilita():
    env = mini_school()
    p1 = Room.objects.create(name="PAL 1")
    p2 = Room.objects.create(name="PAL 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    place(env["schedule"], a, 0, 0, room=p2)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.previous == {a.id: p2.pk}
```

- [ ] **Step 2: Esegui e verifica che falliscano**

Run: `venv/bin/pytest tests/test_solver_rooms_context.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'domain.solver.rooms'`.

- [ ] **Step 3: Scrivi il contesto**

Crea `domain/solver/rooms.py`:

```python
"""L'assegnazione delle aule: la **seconda fase**, un modello a se'.

In EDT non fa parte del piazzamento — ha criteri propri (`TypeChoixOptimSalle`),
un ottimizzatore dedicato (`FicheEdt_OptimiseurSalles`) e una `ripartizione
delle aule` distinta dal calcolo. Assegnare le aule *dopo* aver piazzato e'
quindi una semplificazione validata da un prodotto maturo, non una scorciatoia
(`docs/edt/motore-risoluzione.md`).

I vincoli veri sono tre, piu' la capienza: la finestra `Aule disponibili`
dichiara `Sedi distaccate`, `Indisponibilita' opzionali`, `Indisponibilita'` e
nient'altro. **Capienza in alunni, categoria e tipologie non vincolano.**"""

from collections import defaultdict
from dataclasses import dataclass, field

from domain.analysis.conformity import week_signatures
from domain.analysis.state import ScheduleState
from domain.models import Activity, Resource, Room

_IMMOBILE = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


@dataclass
class RoomContext:
    schedule: object
    signatures: list          # [(settimana rappresentante, tutte le settimane)]
    states: dict              # rappresentante → ScheduleState
    requests: dict            # id → Activity: le decisioni della fase
    candidates: dict          # id → set(room_id) sopravvissute ai pre-filtri
    previous: dict            # id → room_id assegnata prima del calcolo
    held: dict                # id → room_id delle **non** decisioni
    ignora_opzionali: frozenset = frozenset()
    y: dict = field(default_factory=dict)         # (id, room_id) → BoolVar
    assigned: dict = field(default_factory=dict)  # id → BoolVar «assegnata»

    @classmethod
    def build(cls, schedule, ignora_opzionali=()):
        signatures = week_signatures(schedule)
        states = {rep: ScheduleState.build(schedule, week=rep)
                  for rep, _ in signatures}
        ignora = frozenset(ignora_opzionali)

        requests, dichiarate, previous, held = {}, {}, {}, {}
        for state in states.values():
            for aid, act in state.activities.items():
                if aid in requests or aid in held or aid not in state.placed:
                    continue
                aula = state.assigned_room.get(aid)
                rooms = {r.pk for r in act.rooms.all()}
                # Il blocco riguarda l'aula che ha, non quella che non ha:
                # un'immobile senza assegnazione resta una decisione.
                if rooms and not (act.immobility in _IMMOBILE and aula is not None):
                    requests[aid] = act
                    dichiarate[aid] = rooms
                    if aula is not None:
                        previous[aid] = aula
                elif aula is not None:
                    held[aid] = aula

        room_sites = dict(Room.objects.values_list("pk", "site_id"))
        candidates = {
            aid: cls._filtra(aid, act, dichiarate[aid], room_sites,
                             states, ignora)
            for aid, act in requests.items()
        }
        return cls(schedule=schedule, signatures=signatures, states=states,
                   requests=requests, candidates=candidates,
                   previous=previous, held=held, ignora_opzionali=ignora)

    @staticmethod
    def _filtra(aid, act, dichiarate, room_sites, states, ignora):
        """Sede e indisponibilita', su **tutta** la durata del piazzamento."""
        gialla_ignorata = Resource.Kind.ROOM in ignora
        ok = set()
        for room_id in dichiarate:
            if act.site_id is not None and room_sites.get(room_id) != act.site_id:
                continue
            libera = True
            for state in states.values():
                collocazione = state.placed.get(aid)
                if collocazione is None:
                    continue
                for slot in collocazione.slots:
                    livello = state.unavailability.get(
                        (room_id, collocazione.day, slot))
                    if livello == "hard" or (livello == "optional"
                                             and not gialla_ignorata):
                        libera = False
                        break
                if not libera:
                    break
            if libera:
                ok.add(room_id)
        return ok

    def frozen_load(self):
        """(rappresentante, room_id, giorno, fascia) → carico non decisionale.
        Sono le attivita' che occupano un'aula senza essere una scelta di questa
        fase: le immobili che tengono la loro, e le assegnazioni a mano su
        attivita' che non dichiarano candidate."""
        load = defaultdict(int)
        for rep, _ in self.signatures:
            state = self.states[rep]
            for aid, room_id in self.held.items():
                collocazione = state.placed.get(aid)
                if collocazione is None:
                    continue
                for slot in collocazione.slots:
                    load[(rep, room_id, collocazione.day, slot)] += 1
        return dict(load)
```

- [ ] **Step 4: Esegui i test del task**

Run: `venv/bin/pytest tests/test_solver_rooms_context.py -q`
Expected: PASS (11 test).

- [ ] **Step 5: Verifica per mutazione**

Tre mutazioni, tre insiemi di rossi **distinti**:
1. togli il filtro di sede (`if act.site_id is not None ...`) →
   `test_l_aula_di_un_altra_sede_esce_dalle_candidate` rosso, e nessun altro;
2. fai guardare al pre-filtro la sola fascia iniziale (`for slot in
   collocazione.slots[:1]`) →
   `test_l_indisponibilita_sulla_seconda_fascia_di_un_blocco_conta` rosso;
3. tratta la gialla come il verde (togli il ramo `optional`) →
   `test_la_gialla_si_rispetta_come_la_rossa` rosso.

Se una mutazione ne rende rossi zero, il test corrispondente non afferma
niente e va riscritto prima di proseguire.

- [ ] **Step 6: Commit**

```bash
git add domain/solver/rooms.py tests/test_solver_rooms_context.py
git commit -m "feat(rooms): il contesto della seconda fase e i pre-filtri di sede e indisponibilita'"
```

---

### Task 3: Il modello — variabili, capienza per firma, ADR-018

Chiude §2.3, §2.4 e la prima metà di §3.1 (l'interruttore).

**Files:**
- Modify: `domain/solver/rooms.py`
- Test: `tests/test_solver_rooms_model.py`

**Interfaces:**
- Consumes: `RoomContext` (Task 2), `RoomContext.frozen_load()`.
- Produces:
  - `build_room_model(schedule, *, allow_unassigned=True, ignora_opzionali=()) -> (model, ctx)`
    — `model` è un `cp_model.CpModel`, `ctx` un `RoomContext` con `y` e
    `assigned` popolati.
  - Con `allow_unassigned=False` ogni richiesta deve avere un'aula
    (`AddExactlyOne`): è il modo di chiedere «questo vincolo morde?».

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_solver_rooms_model.py`:

```python
"""Il modello della seconda fase: capienza, firme di settimana, ADR-018."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Activity, Room
from domain.solver.rooms import build_room_model
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _risolvi(schedule, **kw):
    model, ctx = build_room_model(schedule, **kw)
    solver = cp_model.CpSolver()
    return solver.Solve(model), solver, ctx


def test_due_attivita_nella_stessa_cella_non_stanno_in_un_aula_da_uno():
    """La regola della casa: si **forza** la violazione e si attende
    INFEASIBLE, invece di risolvere e guardare dove e' finita."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE


def test_la_capienza_due_ne_ammette_due():
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=2)
    a = make_activity(env["subject"], rooms=[pal])
    b = make_activity(env["subject"], rooms=[pal])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_con_la_rinuncia_ammessa_una_resta_senza_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assegnate = sum(solver.Value(v) for v in ctx.assigned.values())
    assert assegnate == 1


def test_settimane_disgiunte_non_competono():
    """Due attivita' nella stessa cella su settimane disgiunte condividono
    un'aula a capienza 1: le firme sono una dimensione, non un dettaglio."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    pari = make_activity(env["subject"], rooms=[lab], mask=0b0101)
    dispari = make_activity(env["subject"], rooms=[lab], mask=0b1010)
    place(env["schedule"], pari, 0, 0)
    place(env["schedule"], dispari, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_adr018_due_immobili_che_saturano_non_bloccano_il_modello():
    """`INFEASIBLE` che nasce dal vietare un peggioramento e' ammesso; quello
    che nasce dal **pretendere una riparazione** no. Due immobili che saturano
    da sole una palestra sono una violazione gia' scritta: la fase assegna il
    resto e il checker la nomina."""
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=1)
    altra = Room.objects.create(name="ALTRA", simultaneous_capacity=1)
    for _ in range(2):
        bloccata = make_activity(env["subject"], rooms=[pal],
                                 immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], bloccata, 0, 0, room=pal)
    libera = make_activity(env["subject"], rooms=[altra])
    place(env["schedule"], libera, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(ctx.assigned[libera.id]) == 1


def test_il_dominio_vuoto_con_la_rinuncia_vietata_e_infattibile():
    env = mini_school()
    from domain.models import ResourceUnavailability
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE
```

- [ ] **Step 2: Esegui e verifica che falliscano**

Run: `venv/bin/pytest tests/test_solver_rooms_model.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_room_model'`.

- [ ] **Step 3: Scrivi il modello**

In `domain/solver/rooms.py`, aggiungi in testa `from ortools.sat.python import
cp_model` e in coda:

```python
def build_room_model(schedule, *, allow_unassigned=True, ignora_opzionali=()):
    """`allow_unassigned=False` pretende un'aula per ogni richiesta: e' il modo
    di chiedere «questo vincolo morde?». Con la rinuncia ammessa la risposta a
    un vincolo violato non e' l'infattibilita' ma la **rinuncia**, che e'
    un'altra domanda — la stessa cucitura che `build_model(allow_unplaced=...)`
    ha per lo scarto."""
    ctx = RoomContext.build(schedule, ignora_opzionali=ignora_opzionali)
    model = cp_model.CpModel()
    for aid in sorted(ctx.requests):
        lits = []
        for room_id in sorted(ctx.candidates[aid]):
            var = model.NewBoolVar(f"y_{aid}_{room_id}")
            ctx.y[(aid, room_id)] = var
            lits.append(var)
        if not allow_unassigned:
            # ⚠ Anche con `lits` vuoto: `AddExactlyOne([])` e' gia' INFEASIBLE,
            # che e' precisamente cio' che «nessuna candidata e assegnazione
            # pretesa» deve significare.
            model.AddExactlyOne(lits)
            continue
        assegnata = model.NewBoolVar(f"assegnata_{aid}")
        ctx.assigned[aid] = assegnata
        model.Add(sum(lits) == assegnata)
    _post_capacity(ctx, model)
    return model, ctx


def _post_capacity(ctx, model):
    """La capienza simultanea, per (aula, giorno, fascia, **firma**).

    ⚠ Il tetto e' il **residuo**: `max(0, capienza - carico congelato)`. Le
    immobili che tengono la loro aula consumano senza essere decisioni, e
    pretendere che le libere riparino il loro sovraccarico e' la meta' vietata
    di ADR-018."""
    carico = ctx.frozen_load()
    posted = set()
    for rep, _ in ctx.signatures:
        state = ctx.states[rep]
        per_cella = defaultdict(list)
        for aid in ctx.requests:
            collocazione = state.placed.get(aid)
            if collocazione is None:
                continue          # non attiva in questa firma: non compete
            for room_id in ctx.candidates[aid]:
                for slot in collocazione.slots:
                    per_cella[(room_id, collocazione.day, slot)].append(
                        ctx.y[(aid, room_id)])
        for (room_id, day, slot), lits in sorted(per_cella.items()):
            residuo = max(0, state.capacity.get(room_id, 1)
                          - carico.get((rep, room_id, day, slot), 0))
            if len(lits) <= residuo:
                continue          # non e' una decisione: e' un fatto
            firma = (room_id, day, slot, residuo,
                     tuple(sorted(lit.Index() for lit in lits)))
            if firma in posted:
                continue          # due firme con lo stesso insieme: un vincolo solo
            posted.add(firma)
            model.Add(sum(lits) <= residuo)
```

- [ ] **Step 4: Esegui i test del task**

Run: `venv/bin/pytest tests/test_solver_rooms_model.py -q`
Expected: PASS (6 test).

- [ ] **Step 5: Verifica per mutazione**

1. Togli il `_post_capacity` da `build_room_model` →
   `test_due_attivita_nella_stessa_cella_non_stanno_in_un_aula_da_uno` e
   `test_con_la_rinuncia_ammessa_una_resta_senza_aula` rossi.
2. Posta il tetto **grezzo** (`state.capacity.get(room_id, 1)` al posto del
   residuo) → `test_adr018_due_immobili_che_saturano_non_bloccano_il_modello`
   rosso, e nessun altro.
3. Ignora le firme (un solo `state`, quello di `ctx.signatures[0]`, per tutte
   le attività) → `test_settimane_disgiunte_non_competono` rosso.

- [ ] **Step 6: Suite intera e commit**

Run: `venv/bin/pytest -q` → verde.

```bash
git add domain/solver/rooms.py tests/test_solver_rooms_model.py
git commit -m "feat(rooms): il modello della seconda fase, con la capienza per firma e il residuo di ADR-018"
```

---

### Task 4: I due livelli, `solve_rooms` e `apply_rooms`

Chiude §3.2 e la seconda metà di §3.1.

**Files:**
- Modify: `domain/solver/rooms.py`
- Modify: `domain/solver/objective.py` (`_STATUS` → `STATUS_NAME`, pubblico)
- Modify: `domain/solver/model.py` (usa `STATUS_NAME`)
- Test: `tests/test_solver_rooms_catena.py`

**Interfaces:**
- Consumes: `Level`, `solve_chain` da `domain.solver.objective`;
  `build_room_model` (Task 3).
- Produces:
  - `RoomSolution(status: str, assignments: dict, unassigned: tuple, stats: dict)`
    — `assignments` è `activity_id → room_id`; `stats` porta `richieste`,
    `assegnate`, `minuti_senza_aula`, `livelli`, `variabili`, `constraint`,
    `secondi`.
  - `solve_rooms(schedule, *, time_limit=None, workers=None, allow_unassigned=True, ignora_opzionali=()) -> RoomSolution`
  - `apply_rooms(solution, schedule) -> None`
  - `STATUS_NAME: dict` in `domain/solver/objective.py`.

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_solver_rooms_catena.py`:

```python
"""I due livelli della seconda fase, e la scrittura."""
import pytest

from domain.models import Placement, Room
from domain.solver.rooms import apply_rooms, solve_rooms
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_l1_preferisce_lasciare_fuori_l_ora_singola():
    """L1 conta i **minuti**: un blocco da 2h che resta senza spazio fa piu'
    danno di un'ora singola, quindi a parita' di celle e' la singola a
    rinunciare."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    lungo = make_activity(env["subject"], rooms=[lab], slots=2)
    corto = make_activity(env["subject"], rooms=[lab], slots=1)
    place(env["schedule"], lungo, 0, 0)
    place(env["schedule"], corto, 0, 1)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == (corto.id,)
    assert soluzione.stats["minuti_senza_aula"] == 60


def test_l2_conserva_l_assegnazione_precedente():
    env = mini_school()
    p1 = Room.objects.create(name="PAL 1")
    p2 = Room.objects.create(name="PAL 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    place(env["schedule"], a, 0, 0, room=p2)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.assignments == {a.id: p2.pk}
    assert soluzione.stats["livelli"][1]["valore"] == 0


def test_la_stabilita_non_vale_una_rinuncia():
    """L1 prima di L2: conservare una collocazione non vale un'aula in meno.
    L'aula di prima e' contesa, quindi tenerla costerebbe una rinuncia."""
    env = mini_school()
    conteso = Room.objects.create(name="LAB", simultaneous_capacity=1)
    libero = Room.objects.create(name="ALTRO", simultaneous_capacity=1)
    vecchia = make_activity(env["subject"], rooms=[conteso, libero])
    nuova = make_activity(env["subject"], rooms=[conteso])
    place(env["schedule"], vecchia, 0, 0, room=conteso)
    place(env["schedule"], nuova, 0, 0)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == ()
    assert soluzione.assignments[vecchia.id] == libero.pk
    assert soluzione.stats["livelli"][1]["valore"] == 1


def test_apply_scrive_l_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    apply_rooms(solve_rooms(env["schedule"]), env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id == lab.pk


def test_apply_cancella_l_aula_di_chi_resta_senza():
    """⚠ La mutazione che nel pezzo 3 era passata inosservata: senza la
    cancellazione, l'aula di ieri resterebbe scritta e `check_schedule`
    leggerebbe un orario che il solver non ha deciso."""
    env = mini_school()
    from domain.models import ResourceUnavailability
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == (a.id,)
    apply_rooms(soluzione, env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id is None
```

- [ ] **Step 2: Esegui e verifica che falliscano**

Run: `venv/bin/pytest tests/test_solver_rooms_catena.py -q`
Expected: FAIL — `ImportError: cannot import name 'solve_rooms'`.

- [ ] **Step 3: Rendi pubblico il dizionario degli stati**

In `domain/solver/objective.py`, aggiungi accanto agli import:

```python
STATUS_NAME = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}
```

In `domain/solver/model.py` cancella `_STATUS` e importa quello:
`from domain.solver.objective import STATUS_NAME, livelli, solve_chain`,
sostituendo l'unico uso (`_STATUS.get(stato, str(stato))`).

- [ ] **Step 4: Scrivi i livelli e l'esecuzione**

In coda a `domain/solver/rooms.py` (e aggiungi `import time`,
`from dataclasses import dataclass` è già presente, più
`from domain.models import Placement` e
`from domain.solver.objective import STATUS_NAME, Level, solve_chain`):

```python
@dataclass(frozen=True)
class RoomSolution:
    status: str
    assignments: dict     # id attività → id aula
    unassigned: tuple     # le richieste rimaste senza aula, nominate dal
                          # checker structural:room_assignment una volta scritte
    stats: dict


def livelli_aule(ctx, model):
    """Due livelli, nell'ordine della spec §3.2.

    L1 conta i **minuti**, non le attivita': un laboratorio da 3h che resta
    senza spazio fa piu' danno di uno da 1h. L2 e' il criterio che EDT dichiara
    alla lettera — *«se possibile mantenendo le assegnazioni della precedente
    ripartizione»*."""
    totale = sum(a.duration_minutes for a in ctx.requests.values())
    minuti = model.NewIntVar(0, totale, "minuti_senza_aula")
    model.Add(minuti == sum(
        act.duration_minutes * (1 - ctx.assigned[aid])
        for aid, act in ctx.requests.items() if aid in ctx.assigned))

    termini, forzati = [], 0
    for aid, room_id in ctx.previous.items():
        var = ctx.y.get((aid, room_id))
        if var is None:
            # L'aula di prima non e' piu' candidata (sede cambiata,
            # indisponibilita' nuova): il cambio e' un fatto, non una scelta.
            forzati += 1
        else:
            termini.append(1 - var)
    cambi = model.NewIntVar(0, len(ctx.previous), "cambi_aula")
    model.Add(cambi == sum(termini) + forzati)
    return [Level("minuti_senza_aula", minuti), Level("cambi_aula", cambi)]


def solve_rooms(schedule, *, time_limit=None, workers=None,
                allow_unassigned=True, ignora_opzionali=()):
    """⚠ `time_limit` e' **per livello** della catena, non per la chiamata:
    e' la forma di `solve_chain`, e va detta."""
    started = time.monotonic()
    model, ctx = build_room_model(schedule, allow_unassigned=allow_unassigned,
                                  ignora_opzionali=ignora_opzionali)
    catena = livelli_aule(ctx, model)

    def estrai(solver):
        return {aid: room_id for (aid, room_id), var in ctx.y.items()
                if solver.Value(var)}

    def suggerisci(model, solver):
        model.ClearHints()
        for var in ctx.y.values():
            model.AddHint(var, solver.Value(var))

    stato, assegnazioni, esiti = solve_chain(
        model, catena, estrai=estrai, suggerisci=suggerisci,
        time_limit=time_limit, workers=workers)

    trovata = assegnazioni is not None
    assegnazioni = assegnazioni or {}
    unassigned = tuple(sorted(aid for aid in ctx.requests
                              if aid not in assegnazioni)) if trovata else ()
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return RoomSolution(
        status=STATUS_NAME.get(stato, str(stato)),
        assignments=assegnazioni,
        unassigned=unassigned,
        stats={
            "richieste": len(ctx.requests),
            "assegnate": len(assegnazioni),
            "minuti_senza_aula": sum(ctx.requests[aid].duration_minutes
                                     for aid in unassigned),
            "livelli": tuple(e.as_dict() for e in esiti),
            "variabili": len(proto.variables),
            "constraint": len(proto.constraints),
            "secondi": round(time.monotonic() - started, 3),
        },
    )


def apply_rooms(solution, schedule):
    """Scrive `Placement.assigned_room`. Non tocca mai giorno e fascia: il
    piazzamento e' l'input di questa fase.

    ⚠ E **cancella** l'aula di chi resta senza: un'attivita' con l'aula di ieri
    e la rinuncia di oggi lascerebbe nel database un orario che il solver non
    ha deciso, e l'oracolo misurerebbe quello."""
    if solution.status not in ("OPTIMAL", "FEASIBLE"):
        return
    for aid, room_id in solution.assignments.items():
        Placement.objects.filter(schedule=schedule, activity_id=aid).update(
            assigned_room_id=room_id)
    if solution.unassigned:
        Placement.objects.filter(
            schedule=schedule,
            activity_id__in=solution.unassigned).update(assigned_room=None)
```

- [ ] **Step 5: Esegui i test del task**

Run: `venv/bin/pytest tests/test_solver_rooms_catena.py -q`
Expected: PASS (5 test).

- [ ] **Step 6: Verifica per mutazione**

1. Inverti l'ordine dei livelli (`[cambi, minuti]`) →
   `test_la_stabilita_non_vale_una_rinuncia` rosso.
2. Conta le **attività** invece dei minuti in L1 (`1 - ctx.assigned[aid]`) →
   `test_l1_preferisce_lasciare_fuori_l_ora_singola` rosso.
3. Togli il ramo `if solution.unassigned` di `apply_rooms` →
   `test_apply_cancella_l_aula_di_chi_resta_senza` rosso.

- [ ] **Step 7: Suite intera e commit**

Run: `venv/bin/pytest -q` → verde (la modifica a `model.py` è un rename: se
qualcosa è rosso lì, è un uso di `_STATUS` rimasto).

```bash
git add domain/solver tests/test_solver_rooms_catena.py
git commit -m "feat(rooms): i due livelli della ripartizione e la scrittura delle aule"
```

---

### Task 5: Il comando `manage.py assign_rooms`

Chiude §4.

**Files:**
- Create: `domain/management/commands/assign_rooms.py`
- Test: `tests/test_assign_rooms_command.py`

**Interfaces:**
- Consumes: `solve_rooms`, `apply_rooms` (Task 4), `check_schedule`, `Severity`.
- Produces: il comando `assign_rooms` con `--schedule` (obbligatorio),
  `--limite`, `--lavoratori`, `--ignora-opzionali`, `--applica`.

- [ ] **Step 1: Scrivi i test che falliscono**

Crea `tests/test_assign_rooms_command.py`:

```python
"""Il comando della ripartizione: dichiara, e non scrive senza --applica."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import Placement, ResourceUnavailability, Room
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _esegui(schedule, **kw):
    out = StringIO()
    call_command("assign_rooms", schedule=schedule.pk, stdout=out, **kw)
    return out.getvalue()


def test_senza_applica_non_scrive_niente():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    testo = _esegui(env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id is None
    assert "--applica" in testo


def test_con_applica_scrive_l_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    _esegui(env["schedule"], applica=True)
    assert Placement.objects.get(activity=a).assigned_room_id == lab.pk


def test_il_rendiconto_nomina_i_livelli():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    testo = _esegui(env["schedule"])
    assert "minuti_senza_aula" in testo and "cambi_aula" in testo


def test_la_rinuncia_e_nominata_e_l_uscita_e_diversa_da_zero():
    """Un'assegnazione mancata deve dire **quale** laboratorio e' rimasto
    fuori e **dove**, o il comando non serve a chi lo lancia."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("assign_rooms", schedule=env["schedule"].pk, stdout=out)
    testo = out.getvalue()
    assert "LAB-FIS" in testo and env["klass"].name in testo
```

- [ ] **Step 2: Esegui e verifica che falliscano**

Run: `venv/bin/pytest tests/test_assign_rooms_command.py -q`
Expected: FAIL — `CommandError: Unknown command: 'assign_rooms'`.

- [ ] **Step 3: Scrivi il comando**

Crea `domain/management/commands/assign_rooms.py`:

```python
"""La ripartizione delle aule: la seconda fase, come comando.

⚠ Non scrive niente senza `--applica`: una ripartizione sovrascrive le aule di
una scuola intera, e il default non puo' essere scrivere.

⚠ `--limite` e' **per livello** della catena, non per l'esecuzione."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Activity, Room, Schedule
from domain.solver.rooms import apply_rooms, solve_rooms


def _hm(minuti):
    return f"{minuti // 60}h{minuti % 60:02d}"


class Command(BaseCommand):
    help = "Assegna le aule alle attività già piazzate di uno schedule."

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello schedule da ripartire")
        parser.add_argument("--limite", type=float, default=None,
                            help="limite di tempo in secondi, per livello")
        parser.add_argument("--lavoratori", type=int, default=None,
                            help="numero di thread CP-SAT (1 = riproducibile)")
        parser.add_argument("--ignora-opzionali", nargs="*", default=(),
                            dest="ignora_opzionali",
                            help="tipi di risorsa per cui le indisponibilità "
                                 "gialle non si rispettano (es. room)")
        parser.add_argument("--applica", action="store_true",
                            help="scrive le aule assegnate nel database")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        soluzione = solve_rooms(schedule, time_limit=options["limite"],
                                workers=options["lavoratori"],
                                ignora_opzionali=options["ignora_opzionali"])
        stats = soluzione.stats

        self.stdout.write(f"== Ripartizione delle aule (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Stato: {soluzione.status}")
        self.stdout.write(f"  Richieste d'aula: {stats['richieste']} "
                          f"({stats['assegnate']} assegnate)")
        self.stdout.write(f"  Modello: {stats['variabili']} variabili, "
                          f"{stats['constraint']} constraint")
        self.stdout.write(f"  Tempo totale: {stats['secondi']}s")

        if stats["livelli"]:
            self.stdout.write("\n== Criteri, in ordine di priorità ==")
            for i, livello in enumerate(stats["livelli"], 1):
                valore = livello["valore"]
                esito = ("non concluso" if valore is None
                         else f"{valore}" + ("" if livello["ottimo"]
                                             else " (ottimo non dimostrato)"))
                self.stdout.write(f"  [{i}] {livello['nome']}: {esito}"
                                  f"   {livello['secondi']}s")

        if soluzione.status not in ("OPTIMAL", "FEASIBLE"):
            raise CommandError(
                "Nessuna ripartizione: il modello è infattibile anche "
                "ammettendo le rinunce. A bloccare è un'aula tenuta da "
                "un'attività immobile o un dato incoerente.")

        if soluzione.unassigned:
            self.stdout.write(
                f"\n== Richieste senza aula ({len(soluzione.unassigned)}, "
                f"{_hm(stats['minuti_senza_aula'])}) ==")
            # ⚠ Si nominano dalle **attività**, non da `check_schedule`: prima
            # di `apply_rooms` le rinunce non sono nel database, e il checker
            # racconterebbe la ripartizione di ieri.
            for act in (Activity.objects.filter(pk__in=soluzione.unassigned)
                        .select_related("subject")
                        .prefetch_related("classes", "teachers", "rooms",
                                          "placements")):
                classi = ", ".join(sorted(c.name for c in act.classes.all()))
                docenti = ", ".join(sorted(t.name for t in act.teachers.all()))
                candidate = ", ".join(sorted(r.name for r in act.rooms.all()))
                dove = ", ".join(f"g{p.day} f{p.start_slot}"
                                 for p in act.placements.all()
                                 if p.schedule_id == schedule.pk)
                self.stdout.write(
                    f"  {act.subject.name} ({_hm(act.duration_minutes)})"
                    f"   classi: {classi or '—'}   docenti: {docenti or '—'}"
                    f"   quando: {dove or '—'}   chiedeva: {candidate}")

        if not options["applica"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--applica` per salvare le aule.")
        else:
            apply_rooms(soluzione, schedule)
            hard = [f for f in check_schedule(schedule)
                    if f.severity == Severity.HARD
                    and f.code not in ("activity_unplaced", "room_unassigned")]
            self.stdout.write("\nAule scritte.")
            if hard:
                self.stdout.write("\n== Violazioni residue ==")
                for f in hard:
                    self.stdout.write(f"  [{f.severity}] {f.message}")

        if soluzione.unassigned:
            raise CommandError(
                f"{len(soluzione.unassigned)} richieste d'aula senza risposta "
                f"({_hm(stats['minuti_senza_aula'])}).")
        self.stdout.write("\nRipartizione terminata: ogni richiesta ha la sua aula.")
```

⚠ Nota per chi implementa: `Room` è importato solo se serve al rendiconto; se
non lo usi, toglilo — un import inutile è rumore che il prossimo lettore deve
verificare.

- [ ] **Step 4: Esegui i test del task**

Run: `venv/bin/pytest tests/test_assign_rooms_command.py -q`
Expected: PASS (4 test).

- [ ] **Step 5: Verifica per mutazione**

1. Fai chiamare `apply_rooms` sempre, anche senza `--applica` →
   `test_senza_applica_non_scrive_niente` rosso.
2. Togli il `raise CommandError` finale →
   `test_la_rinuncia_e_nominata_e_l_uscita_e_diversa_da_zero` rosso.

- [ ] **Step 6: Suite intera e commit**

```bash
git add domain/management/commands/assign_rooms.py tests/test_assign_rooms_command.py
git commit -m "feat(rooms): manage.py assign_rooms, che dichiara le rinunce e non scrive senza --applica"
```

---

### Task 6: Il banco a testimone, l'oracolo differenziale e il Fermi

Chiude §6, §7 (i due casi non ancora coperti) e §8.

**Files:**
- Create: `tests/rooms_harness.py`
- Create: `tests/test_rooms_oracle.py`
- Modify: `tests/fermi.py` (le attività che chiedono un'aula)
- Modify: `CLAUDE.md` (stato, changelog, punti aperti)
- Modify: `docs/edt/aule.md` (nota: il nostro dataset ha le aule, l'osservazione
  in EDT no)

**Interfaces:**
- Consumes: `solve_rooms`, `apply_rooms`, `check_schedule`, `Severity`.
- Produces: `costruisci_testimone_aule(seed) -> dict` in
  `tests/rooms_harness.py`, che restituisce `{"schedule", "atteso": {aid: room_id}}`.

- [ ] **Step 1: Scrivi il banco**

Crea `tests/rooms_harness.py`:

```python
"""Il banco a testimone della ripartizione: si genera **prima**
un'assegnazione valida a caso, e solo dopo si chiede alla fase di ricostruirla.

Rende impossibile l'oracolo vacuo: una fase che non postasse nulla lascerebbe
passare un'assegnazione che il checker boccia, una che postasse `1 == 0` non
troverebbe il testimone.

⚠ Il generatore **dichiara il proprio potere vincolante**: se le aule generate
non stringono (capienza totale molto maggiore della domanda per cella), il seme
salta invece di spacciarsi per un successo verde."""

import random

import pytest

from domain.models import ResourceUnavailability, Room
from tests.analysis_helpers import make_activity, mini_school, place


def costruisci_testimone_aule(seed, n_attivita=12):
    rnd = random.Random(seed)
    env = mini_school(days=3, slots=4)
    aule = [Room.objects.create(name=f"AULA {i}",
                                simultaneous_capacity=rnd.choice([1, 1, 2]))
            for i in range(3)]

    atteso, per_cella = {}, {}
    for _ in range(n_attivita):
        day, slot = rnd.randrange(3), rnd.randrange(4)
        candidate = rnd.sample(aule, rnd.choice([1, 2, 3]))
        # Sceglie l'aula del testimone fra le candidate che hanno ancora posto:
        # e' l'assegnazione valida che la fase dovra' ritrovare.
        libere = [r for r in candidate
                  if per_cella.get((r.pk, day, slot), 0) < r.simultaneous_capacity]
        if not libere:
            continue
        scelta = rnd.choice(libere)
        act = make_activity(env["subject"], rooms=candidate)
        place(env["schedule"], act, day, slot)
        per_cella[(scelta.pk, day, slot)] = per_cella.get(
            (scelta.pk, day, slot), 0) + 1
        atteso[act.id] = scelta.pk

    # Indisponibilita' che il testimone rispetta: aggiungono potere vincolante
    # senza invalidarlo. ⚠ Si escludono le celle che il testimone occupa, o
    # l'assegnazione attesa diventerebbe illegale e il banco misurerebbe un
    # testimone che non esiste.
    occupate = set(per_cella)
    for aula in aule:
        for _ in range(2):
            day, slot = rnd.randrange(3), rnd.randrange(4)
            if (aula.pk, day, slot) in occupate:
                continue
            ResourceUnavailability.objects.create(
                resource=aula, day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)

    capienze = {r.pk: r.simultaneous_capacity for r in aule}
    stretto = sum(1 for (room_id, _, _), carico in per_cella.items()
                  if carico >= capienze[room_id])
    if len(atteso) < 6 or stretto == 0:
        pytest.skip(f"seed {seed}: il testimone non stringe "
                    f"({len(atteso)} attività, {stretto} celle sature)")
    return {"schedule": env["schedule"], "atteso": atteso, "aule": aule}
```

- [ ] **Step 2: Scrivi l'oracolo**

Crea `tests/test_rooms_oracle.py`:

```python
"""L'oracolo differenziale della ripartizione: assegna → scrivi → rileggi.

Il criterio e' **differenziale** e non «zero findings»: la premessa di ADR-018
e' che un orario gia' illegale resti uno stato ammesso."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Placement
from domain.solver.rooms import apply_rooms, solve_rooms
from tests.rooms_harness import costruisci_testimone_aule

pytestmark = pytest.mark.django_db


def _hard(schedule):
    return {f.key for f in check_schedule(schedule) if f.severity == Severity.HARD}


@pytest.mark.parametrize("seed", range(1, 11))
def test_l_oracolo_non_produce_finding_nuovi(seed):
    banco = costruisci_testimone_aule(seed)
    schedule = banco["schedule"]
    Placement.objects.filter(schedule=schedule).update(assigned_room=None)
    baseline = _hard(schedule)
    soluzione = solve_rooms(schedule, workers=1)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    apply_rooms(soluzione, schedule)
    assert _hard(schedule) - baseline == set()


@pytest.mark.parametrize("seed", range(1, 11))
def test_il_testimone_esiste_quindi_zero_rinunce(seed):
    """Il testimone e' un'assegnazione valida: l'ottimo e' zero rinunce. Senza
    questa pretesa una fase che rinuncia a tutto sarebbe «pulita» per qualunque
    checker, perche' un'attivita' senza aula non occupa niente."""
    banco = costruisci_testimone_aule(seed)
    Placement.objects.filter(schedule=banco["schedule"]).update(assigned_room=None)
    soluzione = solve_rooms(banco["schedule"], workers=1)
    assert soluzione.unassigned == ()
    assert soluzione.stats["minuti_senza_aula"] == 0
```

- [ ] **Step 3: Esegui i test del banco**

Run: `venv/bin/pytest tests/test_rooms_oracle.py -q`
Expected: PASS, con eventuali skip **dichiarati** (seed che non stringono).
⚠ Se gli skip sono più della metà, il generatore è troppo lasco: alza
`n_attivita` o abbassa le capienze, e riesegui — un banco che salta quasi
sempre non è un banco.

- [ ] **Step 4: Verifica per mutazione che il banco morda**

Sostituisci il corpo di `_post_capacity` con `return`: i test di
`test_rooms_oracle.py` devono diventare **rossi**. Se restano verdi, il banco
non esercita la capienza e va costruito con aule più contese prima di
proseguire. Ripristina.

- [ ] **Step 5: Arricchisci il Fermi**

In `tests/fermi.py`, dove le attività vengono create, aggiungi le aule chieste
dalle materie che le usano davvero — laboratori per FIS/SCI/INF, palestra per
MOT, aula disegno per ARTE — passando `rooms=[...]` alla creazione. Le aule
esistono già (`ROOMS`, riga 50).

⚠ Aggiungi anche l'assert che tiene fermo il fatto che il problema non è più
vuoto, in `tests/test_fermi_representation.py`:

```python
def test_il_fermi_chiede_almeno_un_aula(dataset):
    """Prima di questo pezzo nessuna attivita' del Fermi dichiarava aule,
    quindi la seconda fase aveva un problema **vuoto** — e una misura su un
    problema vuoto non e' una misura."""
    assert Activity.objects.exclude(rooms=None).count() > 0
```

(`dataset` è la fixture già definita in quel file: `return fermi.build()`.)

- [ ] **Step 6: Misura sul Fermi**

Aggiungi in `tests/test_rooms_oracle.py`:

```python
def test_fermi_ripartizione_misurata():
    """⚠ Misura il **costo**, mai la copertura: una firma di settimana sola,
    nessuna indisponibilita' d'aula, capienze che non stringono."""
    from domain.solver.model import apply, solve
    from tests import fermi
    schedule = fermi.build()["schedule"]
    # serve un orario: la ripartizione lavora sui piazzamenti gia' scritti
    apply(solve(schedule, workers=1), schedule)
    soluzione = solve_rooms(schedule, workers=1)
    assert soluzione.status == "OPTIMAL"
    assert soluzione.unassigned == ()
```

Esegui e **annota i numeri veri** (richieste, variabili, constraint, secondi):
serviranno al changelog. Run:
`venv/bin/pytest tests/test_rooms_oracle.py::test_fermi_ripartizione_misurata -q -s`

- [ ] **Step 7: Aggiorna i documenti**

In `CLAUDE.md`:
- la nota di stato: «resta **un solo pezzo dichiarato fuori** — l'assegnazione
  delle aule» diventa la dichiarazione che il pezzo **è implementato**, con i
  numeri misurati allo Step 6 e il numero di test della suite;
- l'indice della struttura: `domain/solver/rooms.py` e il comando;
- «Ancora aperto»: aggiungi `TypeIncompatibiliteSalle` (11 valori) e
  `TypeChoixOptimSalle` come punti **da osservare in EDT**, di cui conosciamo
  il nome e non i valori;
- una voce di changelog in cima, nello stile delle altre: cosa cambia, cosa ha
  trovato la mutazione, e ⚠ che il Fermi misura il costo e non la copertura.

In `docs/edt/aule.md`, sotto «Stato della fonte»: il nostro dataset ha ora le
aule e le attività che le chiedono; l'osservazione in EDT resta assente
(`NBSALLES = 0`).

- [ ] **Step 8: Suite intera**

Run: `venv/bin/pytest -q`
Expected: verde. Annota il totale (passed/skipped) per il changelog.

- [ ] **Step 9: Commit**

```bash
git add tests CLAUDE.md docs/edt/aule.md
git commit -m "test(rooms): il banco a testimone, l'oracolo differenziale e il Fermi che chiede le aule"
```

---

## Note per chi esegue

- **Non inventare campi.** Se durante l'implementazione sembra servire un
  attributo dell'aula che la spec non nomina (tipologia, categoria, capienza in
  alunni), la risposta è che **non è un vincolo**: §2.5 lo dichiara con la
  fonte. Fermati e chiedi invece di aggiungerlo.
- **Se un test resta verde dopo la mutazione, il difetto è nel test.** Questo
  repository ha pagato otto forme diverse di vacuità, tutte con la stessa
  firma: un verde incapace di fallire. Riscrivi il test prima di proseguire, e
  scrivi nel commit cosa non discriminava.
- **Se la spec si rivela falsa su un punto, correggi la spec** e dillo: è già
  successo due volte in questo pezzo (la candidata unica, l'immobile senza
  aula), ed è il modo in cui questo progetto lavora.
