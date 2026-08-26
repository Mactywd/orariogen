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


def admissible_starts(activity, state, relaxed=False):
    """Gli avvii ammissibili: (giorno, fascia) dove il piazzamento di prova non
    introduce violazioni hard nuove rispetto alla baseline. Le violazioni
    preesistenti non squalificano (l'orario invalido è uno stato ammesso).
    S.P. ne è il conteggio; il violatore di Hall ne usa la lista.

    ⚠ `relaxed=True` esclude dal loop di prova i checker **non monotoni**
    (`PLACEMENT_MONOTONE = False`), e lo fa perché il criterio «chiave nuova ⇒
    cella inammissibile» *su quelle famiglie è falso*: la loro violazione può
    essere **riparata** da un piazzamento, oppure la loro chiave si sposta
    senza che la situazione peggiori. In entrambi i casi ogni cella produce
    una chiave diversa dalla baseline, il dominio si svuota e la fase 5
    inventa una deficienza — falso positivo dimostrato nella review finale del
    violatore di Hall (Critical 1).

    Il default resta `relaxed=False`: S.P. (`residual_domain`) è una **stima
    di difficoltà** mostrata all'utente in una colonna ordinabile, non una
    dimostrazione, e per lui un dominio più stretto è informazione, non un
    bug. Il violatore di Hall è l'opposto — il suo verdetto negativo è una
    dimostrazione, e ogni approssimazione deve **sovrastimare** la capienza —
    quindi `hall.py` passa `relaxed=True`.

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
                if not fresh:
                    out.append((day, start))
    finally:
        if was is not None and activity.id not in state.placed:
            state.place(activity, was.day, was.start_slot)
    return out


def residual_domain(activity, state):
    starts = admissible_starts(activity, state)
    return DomainSize(len(starts), len({day for day, _ in starts}))
