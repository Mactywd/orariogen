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
    doveva evitare.

    ⚠ **Il `max(0, ...)` è irraggiungibile per costruzione, e resta lo
    stesso.** Misurato: togliendolo la suite resta verde, e una sonda che alza
    su `base - used < 0` non scatta su nessuno dei banchi. Non è fortuna. Le
    celle che arrivano qui vengono **solo** da `cells_of`, cioè dalle impronte
    degli avvii che `admissible_starts` ha dichiarato ammissibili per
    un'attività che ha `key` fra i propri token — e `structural:occupation` è
    **monotono**, quindi resta nel loop di prova anche col rilassamento. Una
    cella dove le immobili saturano o sforano la capienza produce lì una
    chiave nuova e viene scartata. Per ogni cella che arriva fin qui vale
    dunque `used ≤ base − quantità della candidata`, cioè `base - used ≥ 1`.

    Resta perché è l'ultima porta prima di Dinic, dove una capacità negativa
    non fallirebbe: produrrebbe un flusso massimo sbagliato, quindi un
    certificato che non torna, quindi un **falso positivo** — in silenzio."""
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
    """Il lato sorgente del taglio minimo. None se entra tutto.

    ⚠ **Gli archi centrali sono a capacità infinita** (§3.2 della spec), ed è
    la scelta che rende il taglio minimo fatto di soli archi di sorgente e di
    pozzo — cioè un insieme di *attività*, leggibile, invece di un insieme di
    archi. Non regala nulla di pericoloso: quanto entra in una cella resta
    limitato dall'arco verso il pozzo. L'unico allentamento è che una singola
    attività potrebbe occupare **due unità della stessa cella**, possibile solo
    con `simultaneous_capacity > 1` **e** durata > 1 — cioè solo su aule e
    materiali cumulativi. È un allentamento nel verso sicuro: **sovrastima** la
    capienza, e una sovrastima non inventa deficienze."""
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


def _labels(state, group):
    """I nomi delle risorse coinvolte, **deduplicati per nome**.

    ⚠ La deduplica non è cosmesi: gli atomi di ADR-017 sono chiavi distinte
    che portano tutte il nome della **classe**, e ogni `ClassPart` ne aggiunge
    un'altra copia. Senza deduplica una classe con due partizioni ripete il
    proprio nome una volta per atomo e una per parte, e la frase che l'utente
    legge — che è il punto di questa fase — diventa illeggibile su una scuola
    vera. L'ordine resta quello di `resource_sort_key`, quindi deterministico:
    si tiene la prima occorrenza."""
    keys = set()
    for a in group:
        keys |= state.tokens[a.id]
    out, visti = [], set()
    for k in sorted(keys, key=resource_sort_key):
        nome = state.resource_names.get(k, str(k))
        if nome not in visti:
            visti.add(nome)
            out.append(nome)
    return tuple(out)


def _analyze_state(state, seen):
    grid = state.grid
    free = _split(state)
    starts = {a.id: admissible_starts(a, state, relaxed=True) for a in free}
    cells_of = {a.id: _footprint(a, starts[a.id]) for a in free}

    by_key = defaultdict(list)
    for a in free:
        for key in state.tokens[a.id]:
            by_key[key].append(a)

    findings = []
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
                # ⚠ **Irraggiungibile per costruzione, e resta.** Misurato:
                # togliendolo la suite resta verde. Con gli archi centrali a
                # ∞ il lato sorgente `T` del taglio minimo soddisfa sempre
                # `domanda(T) > capienza(N(T))` — il taglio vale
                # `Σ domanda(a ∉ T) + Σ capienza(celle raggiungibili)`, ed è
                # minore della domanda totale ogni volta che il flusso non la
                # copre; `N(T)` è contenuto nelle celle raggiungibili, quindi
                # la disuguaglianza passa. E `_reduce` la preserva: accetta un
                # sottoinsieme solo dopo averla riverificata.
                #
                # Resta perché è la §3.3 della spec: un argomento sui grafi
                # residui è **esattamente** il genere di proprietà che su
                # questo progetto è stata dichiarata vera e si è rivelata
                # falsa — tre volte, contate in CLAUDE.md. Qui costa tre
                # righe trasformarla in una postcondizione controllata, e il
                # verso in cui cede è il solo accettabile: il finding **non
                # esce**, cioè si perde richiamo invece di inventare una
                # deficienza.
                break
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
    return findings
