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
