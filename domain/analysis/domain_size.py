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


def admissible_starts(activity, state):
    """Gli avvii ammissibili: (giorno, fascia) dove il piazzamento di prova non
    introduce violazioni hard nuove rispetto alla baseline. Le violazioni
    preesistenti non squalificano (l'orario invalido è uno stato ammesso).
    S.P. ne è il conteggio; il violatore di Hall ne usa la lista."""
    # I checker "placement-independent" (es. CoverageChecker) producono
    # finding che dipendono solo dai dati anagrafici, mai dal piazzamento di
    # prova: compaiono identici nella baseline e in ogni tentativo, quindi il
    # loro delta è sempre vuoto. Escluderli dal loop di prova non cambia il
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
