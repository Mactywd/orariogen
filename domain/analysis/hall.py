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

from domain.analysis.conformity import week_signatures
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
    """Stessa somma di `OccupationChecker.check` (checkers/occupation.py riga
    25): un materiale cumulativo consuma la sua *quantità*, non un'unità per
    attività. Contare le attività invece delle quantità sovrastimerebbe la
    capienza residua ogni volta che un'immobile già piazzata ne occupa più di
    una — divergere da lì di uno rende il residuo peggiore del difetto che
    doveva evitare."""
    day, slot = cell
    acts = state.occupancy.get((key, day, slot), ())
    used = sum(state.material_quantity.get((aid, key), 1) for aid in acts)
    base = state.capacity.get(key, 1)
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
