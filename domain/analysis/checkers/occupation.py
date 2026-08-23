"""Risorsa occupata e capacità cumulativa: un solo meccanismo per aule con
Qtà > 1 e materiali con quantità (una risorsa cumulativa sola)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import Activity

_LOCKED = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


def _occupancy_sort_key(item):
    """Ordina le tuple (chiave, giorno, fascia) gestendo chiavi miste int/str.
    Le chiavi intere vengono prima delle stringhe."""
    (key, day, slot), _ = item
    if isinstance(key, int):
        return (0, key, day, slot)
    else:
        return (1, key, day, slot)


@register("structural:occupation")
class OccupationChecker(Checker):
    def check(self, state, resources=None):
        for (key, day, slot), acts in sorted(state.occupancy.items(), key=_occupancy_sort_key):
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
