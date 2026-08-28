"""S.P. / Nr G. — la dimensione del dominio residuo (motore-risoluzione.md):
«numero di fasce orarie possibili per il piazzamento dell'attività nel
rispetto di tutti i vincoli», ricalcolato contro lo stato corrente.
Calcolato, mai memorizzato (ADR-007)."""

from dataclasses import dataclass

from domain.analysis.findings import Severity
from domain.analysis.registry import all_checkers
from domain.models import Activity


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


def free_candidates(state, selected=None):
    """Le immobili già piazzate consumano capienza; tutte le altre sono
    candidate — incluse le piazzate mobili, perché la domanda è «entra
    tutto?», non «l'orario di adesso è valido».

    `selected` è l'estrazione, e vi entra come una **immobilità di
    esecuzione**: ciò che le sta fuori resta dov'è e continua a occupare, esatto
    come una congelata. È la stessa semantica di `SolverContext.build`, dove
    l'estrazione non toglie attività dal modello ma ne fissa il dominio alla
    collocazione corrente — un perimetro restringe ciò su cui si agisce, mai
    ciò che si conta.

    ⚠ Le candidate si spiazzano TUTTE prima di calcolare i domini: se restano
    piazzate si tolgono il dominio a vicenda, la capienza risulta più bassa
    del vero ed escono falsi positivi (§4.1 della spec del violatore di Hall).
    Questo difetto non si vedrebbe da nessun caso positivo.

    Vive qui e non in `hall.py` perché i due lettori di `trial_placements` —
    la fase 5 e la classifica dei vincoli — hanno bisogno della **stessa**
    preparazione dello stato: due copie divergerebbero, e la §4.1 è
    precisamente il tipo di precauzione che si perde in una copia."""
    frozen = {Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE}
    free = []
    for aid in sorted(state.activities):
        act = state.activities[aid]
        if selected is not None and aid not in selected:
            # ⚠ Fuori perimetro **sempre**, piazzata o no: una congelata mai
            # piazzata resta candidata perché non c'è niente a cui congelarla,
            # ma una fuori estrazione non è candidata per definizione — non è
            # il lavoro che si è chiesto di fare.
            continue
        if act.immobility in frozen and aid in state.placed:
            continue
        free.append(act)
    for a in free:
        if a.id in state.placed:
            state.unplace(a.id)
    return free


def trial_placements(activity, state, relaxed=False):
    """Il piazzamento di prova cella per cella: `[(giorno, fascia, causali)]`
    su **tutta** la griglia, dove `causali` è l'insieme delle coppie
    `(codice, risorse)` delle violazioni hard nuove rispetto alla baseline —
    vuoto se la cella è ammissibile.

    🔑 La coppia `(codice, risorse)` è la **chiave grossolana**: `Finding.key`
    porta anche attività e quantità, che identificano *quella* violazione ma
    non il vincolo che l'ha prodotta. Per l'ammissibilità serve la chiave
    intera — due violazioni della stessa famiglia sulla stessa risorsa sono
    due fatti distinti — quindi il confronto con la baseline resta su di essa
    e solo il risultato si sgrossa: `blame.py` la legge, e non costa un giro
    di checker in più.

    ⚠ `relaxed=True` esclude dal loop di prova i checker **non monotoni**
    (`PLACEMENT_MONOTONE = False`), e lo fa perché il criterio «chiave nuova ⇒
    cella inammissibile» *su quelle famiglie è falso*: la loro violazione può
    essere **riparata** da un piazzamento, oppure la loro chiave si sposta
    senza che la situazione peggiori. In entrambi i casi ogni cella produce
    una chiave diversa dalla baseline, il dominio si svuota e la fase 5
    inventa una deficienza — falso positivo dimostrato nella review finale del
    violatore di Hall (Critical 1).

    ⚠ **Fino al 2026-08-28 il default valeva anche per S.P., con l'argomento
    che «per l'utente un dominio più stretto è informazione, non un bug».
    L'argomento è stato falsificato da una misura**, ed è caduto insieme al
    default: `structural:room_assignment` non stringe il dominio, lo
    **azzera**. Il suo finding esiste solo per le attività *piazzate*, quindi
    ogni cella di prova produce una chiave che la baseline non ha, e
    un'attività con una sola aula candidata dà `S.P. = 0` su una griglia
    interamente libera (misurato: 6 → 0 su `mini_school(days=2, slots=3)`).
    Zero non è una stima più prudente: è la frase «nessuna collocazione
    ammissibile», che `manage.py analyze` stampa per prima perché ordina in
    senso crescente. Un numero che dice *impossibile* su qualcosa che il
    solver piazza senza fatica non è informazione, è la stessa diagnosi falsa
    che la fase 5 non ha il diritto di dare.

    Quindi `residual_domain` rilassa anche lui, e le tre letture di
    `trial_placements` — S.P., violatore di Hall, classifica dei vincoli —
    hanno ora la **stessa** regola. `relaxed=False` resta il default del
    parametro, perché è la lettura letterale del criterio e serve a chi vuole
    misurarne la differenza; nessun chiamante di produzione la usa.

    Rilassare fa perdere **richiamo**, mai precisione: un dominio più largo
    significa più capienza, quindi meno deficienze trovate. È il verso giusto
    in cui sbagliare, ed è il motivo per cui una famiglia dubbia va marcata
    non monotona invece che monotona."""
    # I checker "placement-independent" (es. CoverageChecker) producono
    # finding che dipendono solo dai dati anagrafici, mai dal piazzamento di
    # prova: compaiono identici nella baseline e in ogni tentativo, quindi il
    # loro delta è sempre vuoto. Escluderli dal loop di prova non cambia il
    # risultato ed evita di ripetere il loro lavoro per ogni cella.
    checkers = [c for c in all_checkers()
                if not c.PLACEMENT_INDEPENDENT
                and not (relaxed and not c.PLACEMENT_MONOTONE)]
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
                out.append((day, start, frozenset(k[:2] for k in fresh)))
    finally:
        if was is not None and activity.id not in state.placed:
            state.place(activity, was.day, was.start_slot)
    return out


def admissible_starts(activity, state, relaxed=False):
    """Gli avvii ammissibili: le celle di `trial_placements` che non
    introducono violazioni hard nuove. Le violazioni preesistenti non
    squalificano (l'orario invalido è uno stato ammesso). S.P. ne è il
    conteggio; il violatore di Hall ne usa la lista.

    L'insieme grossolano è vuoto esattamente quando lo è quello delle chiavi
    intere da cui deriva, quindi il filtro qui sotto è la condizione di
    sempre, non un'approssimazione."""
    return [(day, start)
            for day, start, causali in trial_placements(activity, state, relaxed)
            if not causali]


def residual_domain(activity, state, relaxed=True):
    """S.P. e Nr G.: quante fasce e quanti giorni restano legali.

    ⚠ `relaxed=True` di default — vedi l'argomento in `trial_placements`: con
    la lettura letterale un'attività che dichiara **una sola** aula candidata
    misura `0` su una griglia vuota, e S.P. è la colonna che l'utente ordina
    per sapere cosa sta per diventare impiazzabile."""
    starts = admissible_starts(activity, state, relaxed=relaxed)
    return DomainSize(len(starts), len({day for day, _ in starts}))
