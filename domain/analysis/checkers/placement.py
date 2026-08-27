"""L'attività non piazzata — lo stato che EDT mostra di suo (le 284 attività
del Fermi nascono tutte «Non piazzata») e che il nostro registro non nominava.

Serve perché il solver ha smesso di pretendere il piazzamento: `AddExactlyOne`
è diventato `somma(celle) == piazzata`, quindi un'attività può restare
**scartata**. Senza un finding che lo dica, «scarta tutto» sarebbe una
soluzione perfettamente pulita per l'oracolo differenziale — zero piazzamenti,
zero occupazioni, zero findings, verde.

⚠ Il finding descrive un orario **incompleto**, non illegale (D2 della spec):
`HARD` perché è ciò che va risolto, non perché la lezione sia in violazione."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.analysis.state import resource_sort_key


@register("structural:placement")
class PlacementChecker(Checker):
    # ⚠ Non monotono per la definizione stessa di `PLACEMENT_MONOTONE`:
    # piazzare **ripara** la violazione, e la ripara sempre. Sotto il criterio
    # `chiavi_nuove = dopo - baseline` un checker che sa solo togliere chiavi
    # non ne produce mai di nuove, quindi la marcatura non cambia il verdetto
    # di nessuna cella — cambia il **costo**: senza, `admissible_starts` scorre
    # tutte le attivita' non piazzate per ogni cella di prova, e sul Fermi la
    # fase 5 passa da 0,4s a 1,9s. La regola dichiarata in `domain_size.py`
    # dice comunque di marcare non monotona una famiglia dubbia, non monotona.
    PLACEMENT_MONOTONE = False

    def check(self, state, resources=None):
        for aid, act in state.activities.items():
            if aid in state.placed:
                continue
            keys = state.tokens[aid]
            if resources is not None and not (keys & set(resources)):
                continue
            yield Finding(
                "activity_unplaced",
                causali.message("activity_unplaced",
                                subject=state.subject_names[act.subject_id]),
                Severity.HARD,
                resources=tuple(sorted(keys, key=resource_sort_key)),
                activities=(aid,),
                quantities={"minutes": act.duration_minutes},
            )
