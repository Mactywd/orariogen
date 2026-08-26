# Il violatore di Hall — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** implementare la fase 5 dell'`Analisi dei vincoli` — dato uno
`Schedule`, trovare e nominare i sottoinsiemi di attività che non entrano nella
finestra di disponibilità comune delle loro risorse.

**Architecture:** flusso massimo bipartito per (firma di settimana × risorsa)
sopra i domini che `residual_domain` calcola già; il taglio minimo è
l'insieme di Hall deficitario, verificato aritmeticamente e poi ridotto a
irriducibile. Nessun solver: `domain/analysis` resta senza `ortools`.

**Tech Stack:** Python 3, Django ORM, `pytest` (`venv/bin/pytest`). Nessuna
dipendenza nuova — Dinic si scrive a mano in ~70 righe.

**Spec:** `docs/superpowers/specs/2026-08-26-violatore-di-hall-design.md`

## Global Constraints

- **`domain/analysis` non importa `ortools`.** È la ragione per cui
  `domain/solver` è un package separato. L'oracolo differenziale vive in
  `tests/`, che importa entrambi.
- **Terminologia in italiano** nei doc e nei commenti; **codice e
  identificatori in inglese**. È la convenzione di `CLAUDE.md`.
- **Un verdetto negativo è una dimostrazione, mai una stima.** Ogni
  semplificazione ammessa deve *sovrastimare* la capienza. Una che la
  sottostima produce falsi positivi ed è un bug, non un compromesso.
- **Niente numero di richiamo promesso**: la fase 5 è incompleta per
  costruzione (§3.4 della spec).
- **Baseline della suite prima di iniziare: 450 passed, 16 skipped** in ~62 s,
  misurata con `venv/bin/pytest` su `528cebe`. Ogni task la lascia verde.
- **Ordine di iterazione deterministico** ovunque si scorrano risorse o celle:
  `sorted(..., key=resource_sort_key)` per le chiavi, `sorted()` per le celle.
  Due tie-break artefatti dell'ordine d'inserimento sono già debiti aperti in
  `CLAUDE.md`: non se ne aggiunge un terzo.

---

### Task 1: Il flusso massimo, da solo

**Files:**
- Create: `domain/analysis/flow.py`
- Test: `tests/test_analysis_flow.py`

**Interfaces:**
- Consumes: niente.
- Produces: `MaxFlow(n)` con `add_edge(u, v, cap)`, `max_flow(s, t) -> int`,
  `source_side(s) -> set[int]`; la costante `INF = 10 ** 9`.

- [ ] **Step 1: Write the failing test**

`tests/test_analysis_flow.py`:

```python
"""Il flusso massimo e il taglio minimo, su grafi minuscoli scritti a mano.
Nessuna nozione di orario qui: se questi test sono verdi e hall.py sbaglia,
l'errore e' nella semantica del dominio, non nell'algoritmo."""

from domain.analysis.flow import INF, MaxFlow


def test_catena_semplice():
    f = MaxFlow(4)
    f.add_edge(0, 1, 3)
    f.add_edge(1, 2, 2)
    f.add_edge(2, 3, 5)
    assert f.max_flow(0, 3) == 2


def test_bipartito_saturo():
    # 2 attivita' da 1 unita', 2 celle da 1: entra tutto.
    f = MaxFlow(6)
    src, snk = 4, 5
    for a in (0, 1):
        f.add_edge(src, a, 1)
        for c in (2, 3):
            f.add_edge(a, c, INF)
    for c in (2, 3):
        f.add_edge(c, snk, 1)
    assert f.max_flow(src, snk) == 2


def test_deficienza_e_lato_sorgente():
    # 3 attivita' da 1 unita', 2 celle da 1: una resta fuori, e il lato
    # sorgente del taglio nomina tutte e tre le attivita' piu' le due celle.
    f = MaxFlow(7)
    src, snk = 5, 6
    for a in (0, 1, 2):
        f.add_edge(src, a, 1)
        for c in (3, 4):
            f.add_edge(a, c, INF)
    for c in (3, 4):
        f.add_edge(c, snk, 1)
    assert f.max_flow(src, snk) == 2
    side = f.source_side(src)
    assert {0, 1, 2, 3, 4} <= side
    assert snk not in side


def test_lato_sorgente_esclude_le_celle_irraggiungibili():
    # L'attivita' 0 e' saturata e non risale; la cella 3 non entra nel taglio.
    f = MaxFlow(6)
    src, snk = 4, 5
    f.add_edge(src, 0, 1)
    f.add_edge(0, 2, INF)
    f.add_edge(src, 1, 2)
    f.add_edge(1, 3, INF)
    f.add_edge(2, snk, 1)
    f.add_edge(3, snk, 1)
    assert f.max_flow(src, snk) == 2
    side = f.source_side(src)
    assert 1 in side and 3 in side   # l'attivita' 1 non entra tutta
    assert 0 not in side             # l'attivita' 0 e' servita
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analysis_flow.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.flow'`.

- [ ] **Step 3: Write minimal implementation**

`domain/analysis/flow.py`:

```python
"""Flusso massimo bipartito (Dinic) e lato sorgente del taglio minimo, senza
dipendenze. Serve al violatore di Hall: in una rete con gli archi centrali
infiniti, il taglio minimo *e'* l'insieme di Hall deficitario (hall.py, §3.2
della spec). Algoritmo generico — non sa niente di orari."""

from collections import deque

INF = 10 ** 9


class MaxFlow:
    def __init__(self, n):
        self.n = n
        self.graph = [[] for _ in range(n)]   # nodo → [[dest, capacita', indice inverso]]

    def add_edge(self, u, v, cap):
        self.graph[u].append([v, cap, len(self.graph[v])])
        self.graph[v].append([u, 0, len(self.graph[u]) - 1])

    def _levels(self, s, t):
        self.level = [-1] * self.n
        self.level[s] = 0
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v, cap, _ in self.graph[u]:
                if cap > 0 and self.level[v] < 0:
                    self.level[v] = self.level[u] + 1
                    queue.append(v)
        return self.level[t] >= 0

    def _augment(self, u, t, limit):
        if u == t:
            return limit
        while self.seen[u] < len(self.graph[u]):
            edge = self.graph[u][self.seen[u]]
            v, cap, rev = edge
            if cap > 0 and self.level[v] == self.level[u] + 1:
                pushed = self._augment(v, t, min(limit, cap))
                if pushed > 0:
                    edge[1] -= pushed
                    self.graph[v][rev][1] += pushed
                    return pushed
            self.seen[u] += 1
        return 0

    def max_flow(self, s, t):
        total = 0
        while self._levels(s, t):
            self.seen = [0] * self.n
            while True:
                pushed = self._augment(s, t, INF)
                if pushed == 0:
                    break
                total += pushed
        return total

    def source_side(self, s):
        """I nodi raggiungibili dalla sorgente nel grafo residuo, dopo il
        flusso massimo: il lato sorgente del taglio minimo."""
        seen = {s}
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v, cap, _ in self.graph[u]:
                if cap > 0 and v not in seen:
                    seen.add(v)
                    queue.append(v)
        return seen
```

- [ ] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/test_analysis_flow.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/flow.py tests/test_analysis_flow.py
git commit -m "feat(analysis): il flusso massimo e il lato sorgente del taglio"
```

---

### Task 2: `admissible_starts`, estratto da `residual_domain`

**Files:**
- Modify: `domain/analysis/domain_size.py`
- Test: `tests/test_analysis_domain_size.py` (aggiunta)

**Interfaces:**
- Consumes: `ScheduleState` (già esistente).
- Produces: `admissible_starts(activity, state) -> list[tuple[int, int]]`,
  ordinata per `(giorno, fascia)`. `residual_domain` continua a restituire
  `DomainSize(placements, days)` e ne è ora il conteggio.

- [ ] **Step 1: Write the failing test**

Da aggiungere in coda a `tests/test_analysis_domain_size.py`:

```python
def test_admissible_starts_e_la_lista_di_cui_sp_e_il_conteggio():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=1)
    state = ScheduleState.build(env["schedule"])
    starts = admissible_starts(a, state)
    size = residual_domain(a, state)
    assert size.placements == len(starts)
    assert size.days == len({day for day, _ in starts})
    assert starts == sorted(starts)


def test_admissible_starts_non_lascia_l_attivita_spiazzata():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=1)
    place(env["schedule"], a, day=2, slot=3)
    state = ScheduleState.build(env["schedule"])
    admissible_starts(a, state)
    assert state.placed[a.id].day == 2
    assert state.placed[a.id].start_slot == 3
```

L'import in testa al file diventa:

```python
from domain.analysis.domain_size import admissible_starts, residual_domain
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analysis_domain_size.py -v
```

Expected: FAIL con `ImportError: cannot import name 'admissible_starts'`.

- [ ] **Step 3: Write minimal implementation**

In `domain/analysis/domain_size.py`, sostituire il corpo di `residual_domain`
con due funzioni. Il commento sui checker `PLACEMENT_INDEPENDENT` si sposta
dentro `admissible_starts` insieme al codice che spiega:

```python
def admissible_starts(activity, state):
    """Gli avvii ammissibili: (giorno, fascia) dove il piazzamento di prova non
    introduce violazioni hard nuove rispetto alla baseline. Le violazioni
    preesistenti non squalificano (l'orario invalido e' uno stato ammesso).
    S.P. ne e' il conteggio; il violatore di Hall ne usa la lista."""
    # I checker "placement-independent" (es. CoverageChecker) producono
    # finding che dipendono solo dai dati anagrafici, mai dal piazzamento di
    # prova: compaiono identici nella baseline e in ogni tentativo, quindi il
    # loro delta e' sempre vuoto. Escluderli dal loop di prova non cambia il
    # risultato ed evita di ripetere il loro lavoro per ogni cella.
    checkers = [c for c in all_checkers() if not c.PLACEMENT_INDEPENDENT]
    was = state.placed.get(activity.id)
    if was is not None:
        state.unplace(activity.id)
    resources = state.tokens[activity.id]
    baseline = _hard_keys(state, resources, checkers)
    grid = state.grid
    out = []
    try:
        for day in range(grid.days_per_cycle):
            for start in range(grid.slots_per_day - activity.duration_slots + 1):
                state.place(activity, day, start)
                fresh = _hard_keys(state, resources, checkers) - baseline
                state.unplace(activity.id)
                if not fresh:
                    out.append((day, start))
    finally:
        if was is not None and activity.id not in state.placed:
            state.place(activity, was.day, was.start_slot)
    return out


def residual_domain(activity, state):
    starts = admissible_starts(activity, state)
    return DomainSize(len(starts), len({day for day, _ in starts}))
```

- [ ] **Step 4: Run the whole suite**

```bash
venv/bin/pytest -q
```

Expected: 456 passed, 16 skipped. Il conteggio sale di 2 rispetto ai 454
lasciati dal Task 1 e **nessun test
esistente cambia esito**: l'estrazione è a comportamento identico, e se
`test_analysis_domain_size.py` o `test_analyze_command.py` diventano rossi
l'estrazione ha cambiato semantica.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/domain_size.py tests/test_analysis_domain_size.py
git commit -m "refactor(analysis): admissible_starts, di cui S.P. e' il conteggio"
```

---

### Task 3: Il motore su una firma sola

Il cuore. Costruisce la rete, verifica il certificato, emette il finding. Il
ciclo sulle firme arriva al Task 4, la riduzione al Task 5.

**Files:**
- Create: `domain/analysis/hall.py`
- Test: `tests/test_analysis_hall.py`

**Interfaces:**
- Consumes: `MaxFlow`, `INF` (Task 1); `admissible_starts` (Task 2);
  `ScheduleState`, `resource_sort_key` da `domain.analysis.state`.
- Produces: `HallFinding` (dataclass, campi in §5 della spec);
  `analyze_hall(schedule) -> list[HallFinding]`.

- [ ] **Step 1: Write the failing test**

`tests/test_analysis_hall.py`:

```python
"""La fase 5: il sottoinsieme infattibile. Meta' dei casi sono negativi, e
contano di piu' — il difetto temuto e' il falso positivo, che manda l'utente a
smontare vincoli sani."""
import pytest

from domain.analysis.hall import STATEMENT_SINGOLA, analyze_hall
from domain.models import Activity, ResourceUnavailability, Teacher
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _blocca(resource, giorni=(), celle=()):
    """Indisponibilita' hard: giornate intere e/o singole (giorno, fascia)."""
    for day in giorni:
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=resource, day=day, slot=slot, level="hard")
    for day, slot in celle:
        ResourceUnavailability.objects.create(
            resource=resource, day=day, slot=slot, level="hard")


def test_sette_lezioni_in_sei_fasce():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))       # resta il solo giorno 0
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 1
    f = findings[0]
    assert f.n_activities == 7
    assert f.required_minutes == 7 * 60
    assert f.placeable_minutes == 6 * 60
    assert env["teacher"].name in f.resource_labels


def test_sette_lezioni_in_sette_fasce_non_e_un_problema():
    env = mini_school()
    _blocca(env["teacher"], giorni=(2, 3, 4),
            celle=[(1, s) for s in range(1, 6)])       # giorno 0 intero + (1,0)
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []


def test_l_impronta_e_fatta_di_fasce_occupate_non_di_avvii():
    # Due blocchi da 3 ore in un giorno da 6 fasce: entrano (0-2 e 3-5).
    # Contando gli avvii invece delle fasce occupate l'impronta sarebbe di 4
    # celle e uscirebbe un falso positivo.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=3)

    assert analyze_hall(env["schedule"]) == []


def test_l_immobile_consuma_capienza():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(3, 6)])       # restano (0,0) (0,1) (0,2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []         # 3 attivita', 3 fasce

    bloccata = make_activity(
        env["subject"], teachers=[env["teacher"]], slots=1,
        immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], bloccata, day=0, slot=0)

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 3               # l'immobile non e' colpevole
    assert findings[0].placeable_minutes == 2 * 60


def test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio():
    # Trappola §4.1: se si spiazza solo l'attivita' in prova, il blocco B
    # copre entrambe le fasce ammesse ad A, il dominio di A risulta vuoto e
    # esce un falso positivo. Spiazzando tutte le candidate, entra tutto.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(4, 6)])       # docente: (0,0)..(0,3)
    _blocca(env["klass"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(2, 6)])       # classe:  (0,0) (0,1)

    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=1)
    b = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    place(env["schedule"], b, day=0, slot=0)           # copre (0,0) e (0,1)
    place(env["schedule"], a, day=0, slot=2)           # fuori dalla finestra di classe

    assert analyze_hall(env["schedule"]) == []
```

⚠ `ResourceUnavailability.resource` è una FK a `Resource`, e docenti, classi e
aule sono tutti `Resource` nello schema generico: `resource=env["teacher"]`
funziona così com'è (stessa forma di `tests/test_analysis_time_constraints.py`).

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analysis_hall.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'domain.analysis.hall'`.

- [ ] **Step 3: Write minimal implementation**

`domain/analysis/hall.py`:

```python
"""Fase 5 dell'Analisi dei vincoli (diagnostica.md): l'insieme di attivita'
che non entra nella finestra di disponibilita' comune delle sue risorse, anche
quando nessuna di esse e' impossibile da sola.

Non usa il solver: e' un conteggio di capienza. Il metodo e' il teorema di
Hall in forma deficitaria — flusso massimo su (risorsa × firma di settimana),
e il taglio minimo *e'* l'insieme colpevole.

⚠ Il rilassamento ignora la contiguita' dei blocchi e le interazioni fra le
attivita' dentro l'insieme: entrambe *aggiungono* liberta', quindi il flusso
sovrastima il vero massimo piazzabile e una deficienza trovata e' una
dimostrazione di infattibilita'. Il verso opposto non vale: il solver puo'
rispondere INFEASIBLE senza che nessun insieme sia deficiente."""

from collections import defaultdict
from dataclasses import dataclass

from domain.analysis.domain_size import admissible_starts
from domain.analysis.flow import INF, MaxFlow
from domain.analysis.state import ScheduleState, resource_sort_key
from domain.models import Activity, TimeGrid

STATEMENT = ("La fascia di disponibilità comune delle attività e delle "
             "rispettive risorse non permette di piazzare tutte le attività.")
STATEMENT_SINGOLA = "L'attività non ha nessuna collocazione ammissibile."
REMEDIES = (
    "Diminuire la durata delle attività",
    "Diminuire le indisponibilità delle risorse",
    "Diminuire le indisponibilità delle risorse comuni",
)
FROZEN = {Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE}


@dataclass(frozen=True)
class HallFinding:
    statement: str
    binding_label: str
    resource_labels: tuple
    n_activities: int
    required_minutes: int
    placeable_minutes: int
    window: tuple
    activities: tuple
    remedies: tuple


def analyze_hall(schedule):
    if TimeGrid.objects.first() is None:
        return []
    state = ScheduleState.build(schedule)
    return _analyze_state(state, seen=set())


def _split(state):
    """Le immobili gia' piazzate consumano capienza; tutte le altre sono
    candidate — incluse le piazzate mobili, perche' la fase 5 chiede «entra
    tutto?», non «l'orario di adesso e' valido».

    ⚠ Le candidate si spiazzano TUTTE prima di calcolare i domini: se restano
    piazzate si tolgono il dominio a vicenda, la capienza risulta piu' bassa
    del vero ed escono falsi positivi (§4.1 della spec). Questo difetto non si
    vedrebbe da nessun caso positivo."""
    free = []
    for aid in sorted(state.activities):
        a = state.activities[aid]
        if a.immobility in FROZEN and aid in state.placed:
            continue
        free.append(a)
    for a in free:
        if a.id in state.placed:
            state.unplace(a.id)
    return free


def _footprint(activity, starts):
    """Le fasce che l'attivita' occuperebbe, non i suoi avvii: un blocco da 3
    ore avviato in 0 occupa 0, 1 e 2."""
    return {(day, s)
            for day, start in starts
            for s in range(start, start + activity.duration_slots)}


def _cell_capacity(state, key, cell):
    day, slot = cell
    base = state.capacity.get(key, 1)
    used = len(state.occupancy.get((key, day, slot), ()))
    return max(0, base - used)


def _demand(state, activity, key):
    """In slot, non in minuti (§3.1): la conversione avviene solo nel finding.
    Per i materiali cumulativi la domanda e' pesata dalla quantita' richiesta."""
    quantity = state.material_quantity.get((activity.id, key), 1)
    return activity.duration_slots * quantity


def _certificate(state, key, group, cells_of, demand_of):
    """Il conto di Hall, rifatto a mano sull'insieme dato. Il taglio minimo lo
    *suggerisce*; questa funzione lo *verifica*, ed e' l'unica cosa che decide
    se un finding esce."""
    window = set()
    for a in group:
        window |= cells_of[a.id]
    window = tuple(sorted(window))
    capacity = sum(_cell_capacity(state, key, c) for c in window)
    required = sum(demand_of[a.id] for a in group)
    return window, required, capacity


def _deficient_set(state, key, group, cells_of, demand_of):
    """Il lato sorgente del taglio minimo. None se entra tutto."""
    cells = sorted(set().union(*(cells_of[a.id] for a in group)) or set())
    index = {c: i for i, c in enumerate(cells)}
    n_acts = len(group)
    source, sink = n_acts + len(cells), n_acts + len(cells) + 1
    net = MaxFlow(sink + 1)
    for i, a in enumerate(group):
        net.add_edge(source, i, demand_of[a.id])
        for c in cells_of[a.id]:
            net.add_edge(i, n_acts + index[c], INF)
    for c in cells:
        net.add_edge(n_acts + index[c], sink, _cell_capacity(state, key, c))
    required = sum(demand_of[a.id] for a in group)
    if net.max_flow(source, sink) >= required:
        return None
    side = net.source_side(source)
    return [a for i, a in enumerate(group) if i in side]


def _labels(state, group):
    keys = set()
    for a in group:
        keys |= state.tokens[a.id]
    return tuple(state.resource_names.get(k, str(k))
                 for k in sorted(keys, key=resource_sort_key))


def _analyze_state(state, seen):
    grid = state.grid
    free = _split(state)
    starts = {a.id: admissible_starts(a, state) for a in free}
    cells_of = {a.id: _footprint(a, starts[a.id]) for a in free}

    by_key = defaultdict(list)
    for a in free:
        for key in state.tokens[a.id]:
            by_key[key].append(a)

    findings = []
    for key in sorted(by_key, key=resource_sort_key):
        group = by_key[key]
        demand_of = {a.id: _demand(state, a, key) for a in group}
        culprits = _deficient_set(state, key, group, cells_of, demand_of)
        if not culprits:
            continue
        window, required, capacity = _certificate(
            state, key, culprits, cells_of, demand_of)
        if required <= capacity:
            continue   # il taglio non regge il conto: non si emette nulla
        signature = frozenset(a.id for a in culprits)
        if signature in seen:
            continue
        seen.add(signature)
        findings.append(HallFinding(
            statement=STATEMENT if len(culprits) > 1 else STATEMENT_SINGOLA,
            binding_label=state.resource_names.get(key, str(key)),
            resource_labels=_labels(state, culprits),
            n_activities=len(culprits),
            required_minutes=required * grid.slot_minutes,
            placeable_minutes=capacity * grid.slot_minutes,
            window=window,
            activities=tuple(sorted(signature)),
            remedies=REMEDIES,
        ))
    return findings
```

- [ ] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/test_analysis_hall.py -v
```

Expected: 7 passed.

⚠ Se `test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio` è l'unico rosso,
il difetto è in `_split`: le candidate non vengono spiazzate tutte prima di
calcolare i domini. Non aggirarlo allargando la finestra nel test.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/hall.py tests/test_analysis_hall.py
git commit -m "feat(analysis): il violatore di Hall su una firma di settimana"
```

---

### Task 4: Il ciclo sulle firme di settimana

**Files:**
- Modify: `domain/analysis/hall.py`
- Test: `tests/test_analysis_hall.py` (aggiunta)

**Interfaces:**
- Consumes: `week_signatures(schedule)` da `domain.analysis.conformity`.
- Produces: nessuna firma nuova — `analyze_hall` continua a restituire
  `list[HallFinding]`.

- [ ] **Step 1: Write the failing test**

Da aggiungere a `tests/test_analysis_hall.py`:

```python
def test_le_settimane_disgiunte_non_competono():
    # Trappola §2: unendo le firme le due attivita' si contendono l'unica
    # fascia e esce un falso positivo. Per firma, ognuna entra da sola.
    from domain import weeks

    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(1, 6)])       # resta la sola (0,0)
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                  mask=weeks.single_week(0))
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                  mask=weeks.single_week(1))

    assert analyze_hall(env["schedule"]) == []


def test_una_deficienza_in_una_sola_settimana_esce_lo_stesso():
    from domain import weeks

    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(1, 6)])
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                      mask=weeks.single_week(0))

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analysis_hall.py -k settimane -v
```

Expected: `test_le_settimane_disgiunte_non_competono` FAIL — esce un finding
da 2 attività, perché `analyze_hall` costruisce un solo stato sulla settimana 0
e la maschera della seconda attività non viene consultata.

⚠ Nota: `ScheduleState.build(schedule)` usa `week=0` di default, quindi la
seconda attività oggi non è nemmeno nello stato. Il rosso può presentarsi come
"nessun finding dove ce ne vuole uno" nel secondo test invece che come falso
positivo nel primo. Entrambi devono essere verdi a fine task.

- [ ] **Step 3: Write minimal implementation**

In `domain/analysis/hall.py`, sostituire `analyze_hall` e aggiungere l'import:

```python
from domain.analysis.conformity import week_signatures
```

```python
def analyze_hall(schedule):
    """⚠ Le firme di settimana sono una dimensione, non un dettaglio: due
    attivita' di settimane disgiunte non competono per la stessa fascia, e
    trattarle come concorrenti produce falsi positivi.

    Si usa `week_signatures` — la primitiva gia' condivisa con `check_schedule`
    e `SolverContext` — e non `_week_groups` di capacity.py: la prima include
    nella firma anche le indisponibilita' datate e i festivi, ed e' la stessa
    firma su cui il modello CP-SAT posta i suoi vincoli. Usarne un'altra
    disallineerebbe la fase 5 dall'oracolo che deve confermarla."""
    if TimeGrid.objects.first() is None:
        return []
    findings, seen = [], set()
    for representative, _weeks in week_signatures(schedule):
        state = ScheduleState.build(schedule, week=representative)
        findings += _analyze_state(state, seen)
    return findings
```

`seen` è condiviso fra le firme: lo stesso insieme colpevole trovato in due
settimane diverse è un problema solo, come già fa `check_schedule` fondendo i
findings identici.

- [ ] **Step 4: Run the whole suite**

```bash
venv/bin/pytest -q
```

Expected: 465 passed, 16 skipped.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/hall.py tests/test_analysis_hall.py
git commit -m "feat(analysis): la fase 5 gira per firma di settimana"
```

---

### Task 5: La riduzione a insieme irriducibile

**Files:**
- Modify: `domain/analysis/hall.py`
- Test: `tests/test_analysis_hall.py` (aggiunta)

**Interfaces:**
- Consumes: `_certificate` (Task 3).
- Produces: `_reduce(state, key, group, cells_of, demand_of) -> list` — interna
  al modulo, nessun consumatore esterno.

- [ ] **Step 1: Write the failing test**

Da aggiungere a `tests/test_analysis_hall.py`:

```python
def test_l_insieme_nominato_e_irriducibile():
    # Sul docente l'insieme massimale e' di 10 attivita' (7 legate al giorno 0
    # dalla classe + 3 libere su due giorni): la deficienza c'e', ma tre di
    # quelle attivita' non c'entrano nulla. La riduzione deve nominarne 7.
    env = mini_school()
    _blocca(env["teacher"], giorni=(2, 3, 4))          # docente: giorni 0 e 1
    _blocca(env["klass"], giorni=(1, 2, 3, 4))         # classe:  giorno 0

    legate = [make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]], slots=1) for _ in range(7)]
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 1                          # dedup fra classe e docente
    f = findings[0]
    assert f.n_activities == 7
    assert f.activities == tuple(sorted(a.id for a in legate))
    assert f.required_minutes == 7 * 60
    assert f.placeable_minutes == 6 * 60


def test_due_insiemi_indipendenti_sulla_stessa_risorsa_escono_entrambi():
    # Due attivita' senza nessuna collocazione, sullo stesso docente. Gli
    # insiemi irriducibili sono due, {A} e {B}: emetterne uno solo perche' la
    # risorsa e' la stessa nasconderebbe meta' del problema.
    env = mini_school()
    _blocca(env["teacher"], giorni=(0, 1, 2, 3, 4))
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1)
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 2
    assert all(f.n_activities == 1 for f in findings)
    assert len({f.activities for f in findings}) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analysis_hall.py -k "irriducibile or indipendenti" -v
```

Expected: due rossi. `test_l_insieme_nominato_e_irriducibile` dà
`len(findings) == 2` (l'insieme da 10 sul docente non coincide con quello da 7
sulla classe, quindi la deduplicazione non scatta) e `n_activities == 10` su
uno dei due; `test_due_insiemi_indipendenti…` dà `len(findings) == 1`, perché
oggi ogni risorsa produce al massimo un finding.

- [ ] **Step 3: Write minimal implementation**

In `domain/analysis/hall.py`, aggiungere `_reduce` e chiamarla in
`_analyze_state` fra `_deficient_set` e `_certificate`:

```python
def _reduce(state, key, group, cells_of, demand_of):
    """Toglie un'attivita' per volta finche' il certificato regge, fino a punto
    fisso. Cio' che resta e' **irriducibile**: ogni attivita' nominata e'
    necessaria alla contraddizione, e toglierne una qualsiasi la fa sparire.

    Non e' cosmesi. L'insieme che esce dal taglio minimo e' il massimale, e sul
    Fermi nominerebbe centinaia di attivita': una diagnosi che nessuno legge."""
    current = list(group)
    changed = True
    while changed and len(current) > 1:
        changed = False
        for a in list(current):
            if len(current) == 1:
                break
            trial = [x for x in current if x.id != a.id]
            _, required, capacity = _certificate(
                state, key, trial, cells_of, demand_of)
            if required > capacity:
                current = trial
                changed = True
    return current
```

In `_analyze_state`, il corpo del ciclo su `key` diventa un ciclo interno: si
emette un insieme irriducibile per volta e lo si **toglie** dal gruppo, finché
la risorsa smette di essere deficiente. Senza questo, due problemi indipendenti
sulla stessa risorsa ne mostrerebbero uno solo — e la riduzione, che serve a
rendere leggibile la diagnosi, finirebbe per nasconderne metà.

```python
    for key in sorted(by_key, key=resource_sort_key):
        group = by_key[key]
        demand_of = {a.id: _demand(state, a, key) for a in group}
        while group:
            culprits = _deficient_set(state, key, group, cells_of, demand_of)
            if not culprits:
                break
            culprits = _reduce(state, key, culprits, cells_of, demand_of)
            window, required, capacity = _certificate(
                state, key, culprits, cells_of, demand_of)
            if required <= capacity:
                break   # il taglio non regge il conto: non si emette nulla
            nominate = frozenset(a.id for a in culprits)
            group = [a for a in group if a.id not in nominate]
            if nominate in seen:
                continue
            seen.add(nominate)
            findings.append(HallFinding(
                statement=STATEMENT if len(culprits) > 1 else STATEMENT_SINGOLA,
                binding_label=state.resource_names.get(key, str(key)),
                resource_labels=_labels(state, culprits),
                n_activities=len(culprits),
                required_minutes=required * grid.slot_minutes,
                placeable_minutes=capacity * grid.slot_minutes,
                window=window,
                activities=tuple(sorted(nominate)),
                remedies=REMEDIES,
            ))
```

⚠ `group` si accorcia a ogni giro, quindi il ciclo termina. Il `break` sul
certificato che non regge è deliberato: se il taglio minimo smette di produrre
un conto valido, si ferma quella risorsa invece di riprovare all'infinito.

- [ ] **Step 4: Run test to verify it passes**

```bash
venv/bin/pytest tests/test_analysis_hall.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add domain/analysis/hall.py tests/test_analysis_hall.py
git commit -m "feat(analysis): l'insieme nominato e' irriducibile"
```

---

### Task 6: L'oracolo differenziale

**Files:**
- Create: `tests/test_hall_oracle.py`

**Interfaces:**
- Consumes: `analyze_hall` (Task 4), `solve` da `domain.solver.model`,
  `build_witness` da `tests.solver_harness`.
- Produces: niente — è il criterio di riuscita del pezzo.

- [ ] **Step 1: Write the failing test**

`tests/test_hall_oracle.py`:

```python
"""Il criterio di riuscita della fase 5, nelle due direzioni.

Direzione 1 — ogni finding dev'essere confermato: se la fase 5 dichiara un
insieme infattibile, il modello hard sulle stesse attivita' deve rispondere
INFEASIBLE. Un violatore inventato diventa un rosso.

Direzione 2, quella che vale di piu' — le istanze di `solver_harness` sono
**fattibili per costruzione**: hanno un testimone. Quindi la fase 5 su ognuna
di esse deve tacere. Qualunque finding e' un falso positivo *dimostrato*.

⚠ Questo misura la **precisione**, non il **richiamo**: la fase 5 e' incompleta
per costruzione (§3.4 della spec) e non c'e' un numero di richiamo da
promettere."""
import pytest

from domain.analysis.hall import analyze_hall
from domain.models import ResourceUnavailability
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import build_witness

pytestmark = pytest.mark.django_db


def test_un_finding_e_confermato_dal_solver():
    env = mini_school()
    for day in (1, 2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert len(analyze_hall(env["schedule"])) == 1
    assert solve(env["schedule"], time_limit=30).status == "INFEASIBLE"


def test_il_solver_conferma_anche_il_confine():
    # Una fascia in piu': la fase 5 tace, e il solver deve trovare una
    # soluzione. Senza questa meta', il test sopra passerebbe anche con una
    # fase 5 che dichiara infattibile qualunque cosa.
    env = mini_school()
    for day in (2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for slot in range(1, 6):
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=1, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_nessun_finding_su_un_istanza_fattibile_per_costruzione(seed):
    w = build_witness(seed)
    findings = analyze_hall(w.schedule)
    assert findings == [], (
        f"falso positivo dimostrato sul seed {seed}: esiste un testimone, "
        f"quindi nessun insieme puo' essere deficiente — "
        f"{[(f.binding_label, f.n_activities) for f in findings]}")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_hall_oracle.py -v
```

Expected: i primi due passano subito (il motore c'è dal Task 3); i cinque seed
sono la vera prova. Se uno diventa rosso, **non allentare l'assert**: c'è un
falso positivo, e il messaggio dice su quale risorsa.

- [ ] **Step 3: Diagnosticare gli eventuali rossi**

I tre sospetti, in ordine di probabilità, tutti già scritti in §9 della spec:

1. **Firme unite** — un finding che nomina attività di settimane diverse.
   Controllare che `analyze_hall` cicli su `week_signatures`.
2. **Sorelle non spiazzate** — un finding con `n_activities == 1` su
   un'attività che nel testimone è piazzata. Controllare `_split`.
3. **Capienza contata due volte** — `placeable_minutes` più basso del numero
   di celle × `slot_minutes` su una risorsa con `simultaneous_capacity == 1`
   e nessuna immobile.

- [ ] **Step 4: Run the whole suite**

```bash
venv/bin/pytest -q
```

Expected: 474 passed, 16 skipped.

- [ ] **Step 5: Commit**

```bash
git add tests/test_hall_oracle.py
git commit -m "test(analysis): l'oracolo della fase 5, nelle due direzioni"
```

---

### Task 7: Il comando, e la documentazione

**Files:**
- Modify: `domain/management/commands/analyze.py`
- Modify: `CLAUDE.md`
- Modify: `docs/edt/diagnostica.md`
- Test: `tests/test_analyze_command.py` (aggiunta)

**Interfaces:**
- Consumes: `analyze_hall` (Task 4).
- Produces: il flag `--no-hall` sul comando.

- [ ] **Step 1: Write the failing test**

Da aggiungere a `tests/test_analyze_command.py`, seguendo lo stile dei test già
presenti nel file (leggerli prima: usano `call_command` con `stdout` catturato):

Il file ha già l'helper `_run(*args)`, che cattura `stdout`. I tre test lo
usano, e il primo cattura l'eccezione perché il comando esce non-zero quando
restano incoerenze:

```python
def test_la_fase_5_esce_sotto_schedule():
    env = mini_school()
    for day in (1, 2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    testo = out.getvalue()
    assert "Insiemi non piazzabili" in testo
    assert "Durata piazzabile" in testo


def test_no_hall_spegne_la_fase_5():
    env = mini_school()
    out = _run("--schedule", str(env["schedule"].pk), "--no-hall")
    assert "Insiemi non piazzabili" not in out


def test_senza_schedule_la_fase_5_si_dichiara_saltata():
    mini_school()
    assert "richiede --schedule" in _run()
```

L'import in testa al file guadagna `ResourceUnavailability`.

- [ ] **Step 2: Run test to verify it fails**

```bash
venv/bin/pytest tests/test_analyze_command.py -v
```

Expected: FAIL — `unrecognized arguments: --no-hall`, e la stringa
`Insiemi non piazzabili` non compare.

- [ ] **Step 3: Write minimal implementation**

In `domain/management/commands/analyze.py`:

```python
from domain.analysis.hall import analyze_hall
```

In `add_arguments`:

```python
        parser.add_argument("--no-hall", action="store_true",
                            help="salta la fase 5 (insiemi non piazzabili)")
```

In `handle`, subito dopo il blocco della capienza e **prima** del blocco
`if options["schedule"]`, inizializzare `hall = []`; poi, dentro il blocco
`if options["schedule"]:` e dopo la stampa della conformità:

```python
            if not options["no_hall"]:
                hall = analyze_hall(schedule)
                self.stdout.write("\n== Insiemi non piazzabili (fase 5) ==")
                if not hall:
                    self.stdout.write("Nessun insieme deficiente.")
                for i, f in enumerate(hall, 1):
                    self.stdout.write(f"\n[{i}] {f.statement}")
                    self.stdout.write(
                        "    " + ", ".join(f.resource_labels))
                    self.stdout.write(f"    Risorsa satura: {f.binding_label}")
                    self.stdout.write(f"    Numero di attività: {f.n_activities}")
                    self.stdout.write(
                        f"    Durata da piazzare: {_hm(f.required_minutes)}")
                    self.stdout.write(
                        f"    Durata piazzabile:  {_hm(f.placeable_minutes)}")
                    gap = f.required_minutes - f.placeable_minutes
                    self.stdout.write(f"    » {_hm(gap)} non potrà essere piazzata")
                    self.stdout.write("    Azioni:")
                    for remedy in f.remedies:
                        self.stdout.write(f"      - {remedy}")
        elif not options["no_hall"]:
            self.stdout.write(
                "\n== Insiemi non piazzabili (fase 5) ==\n"
                "Saltata: richiede --schedule (legge lo stato, non solo l'anagrafica).")
```

E nel riepilogo:

```python
        self.stdout.write(f"  {len(capacity)} problemi di capienza, "
                          f"{len(hall)} insiemi non piazzabili, "
                          f"{hard} violazioni hard.")
        if capacity or hall or hard:
            raise CommandError("Rimangono delle incoerenze.")
```

- [ ] **Step 4: Run the whole suite**

```bash
venv/bin/pytest -q
```

Expected: 477 passed, 16 skipped.

- [ ] **Step 5: Misurare il costo sul Fermi**

La spec (§4.2) dichiara ~3,5 s sul Fermi intero, **estrapolati** dalla misura
del piano 2 (26 attività in ~0,3 s). È una previsione, non una misura: va
verificata prima di finire nel changelog come se fosse un dato.

```bash
venv/bin/python -c "
import django, os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
" && venv/bin/pytest tests/test_fermi_representation.py -q
```

Il modo pulito è un test marcato lento che costruisce la fixture Fermi, chiama
`analyze_hall` e stampa i secondi — seguire il pattern di
`test_fermi_intero_misurato` in `tests/test_solver_oracle.py`, che fa
esattamente questo per il modello CP-SAT. Se il numero misurato è di un ordine
di grandezza diverso dai 3,5 s previsti, **correggere la spec**, non il
changelog: la §4.2 è una previsione sbagliata e va detto.

⚠ E come per il modello hard, il Fermi qui misura il **costo**, mai la
**copertura**: non ha righe di vincolo, quindi i domini di `admissible_starts`
sono larghi e la fase 5 con ogni probabilità non trova nulla. Un «zero finding
sul Fermi» non è un risultato.

- [ ] **Step 6: Aggiornare la documentazione**

In `docs/edt/diagnostica.md`, sotto la sezione della fase 5, aggiungere una
riga che dichiara la fase **implementata** e rimanda a `domain/analysis/hall.py`
e alla spec.

In `CLAUDE.md`:

1. Nella struttura dei documenti, `domain/analysis/` guadagna la menzione del
   violatore di Hall.
2. Nella nota di stato, i **tre pezzi dichiarati fuori** diventano **due**
   (restano gli alleggerimenti a quota e l'assegnazione delle aule).
3. Nel changelog, una voce datata **2026-08-26** che dice:
   - cosa è stato implementato e con che metodo (Hall deficitario, flusso e
     taglio minimo, nessun solver);
   - le **due trappole** scritte nella spec *prima* di implementarle e i due
     test che le tengono ferme — è la prima volta su questo progetto che una
     semplificazione sbagliata viene prevista invece che scoperta dopo, e va
     detto;
   - che l'oracolo misura la **precisione** e non il richiamo, e perché;
   - il conteggio della suite **misurato**, non previsto: rilanciare
     `venv/bin/pytest -q` e copiare il numero vero.
4. ⚠ Correggere il numero di test dichiarato nella nota di stato: dice **436**,
   ma la baseline misurata su `528cebe` è **450 passed, 16 skipped** — il 436
   è anteriore ai due commit di review della PR #1.

- [ ] **Step 7: Commit**

```bash
git add domain/management/commands/analyze.py tests/test_analyze_command.py \
        CLAUDE.md docs/edt/diagnostica.md
git commit -m "feat(analysis): la fase 5 nel comando analyze, e la documentazione"
```

---

## Cosa questo piano non fa

Dichiarato, perché non venga scoperto come mancanza:

- **Il riquadro `Soluzione` operativo** di EDT (griglia delle indisponibilità
  modificabile sul posto, `Rilancia la verifica`): è UI, e qui non c'è UI.
  `HallFinding` porta già `activities` e `window`, i due dati che quella
  schermata consumerebbe.
- **L'aula come variabile di decisione**: resta un token fisso. La fase 5 la
  tratta come risorsa portante di capienza, non come scelta.
- **Il richiamo**: nessuna promessa di trovare *tutti* i sottoinsiemi
  infattibili — impossibile per costruzione.
- **Il Fermi come banco di misura**: come per il modello hard, il Fermi non ha
  righe di vincolo e misurerebbe il dataset, non la fase. Se si vuole un numero
  sul Fermi, va preso come **misura di costo** (secondi su 284 attività), mai
  come misura di copertura.
