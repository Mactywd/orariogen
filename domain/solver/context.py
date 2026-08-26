"""Lo stato del solver: costruito una volta sola, contiene tutto ciò che i
builder leggono. Nessuna query ORM dentro un builder — è lo stesso contratto
che ScheduleState impone ai checker."""

from collections import defaultdict
from dataclasses import dataclass, field

from domain.analysis.conformity import week_signatures
from domain.analysis.state import ScheduleState
from domain.models import Activity

_IMMOBILE = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


@dataclass
class SolverContext:
    schedule: object
    grid: object
    signatures: list          # [(settimana rappresentante, tutte le settimane)]
    states: dict              # settimana rappresentante → ScheduleState
    activities: dict          # id → Activity presenti nel modello
    free: set                 # id delle attività che il solver può muovere
    cells: dict               # id → set di (giorno, fascia di inizio) ammissibili
    tokens: dict              # id → frozenset di chiavi di occupazione
    capacity: dict            # chiave → capacità simultanea
    material_quantity: dict   # (id attività, chiave) → quantità
    time_rows: list           # righe ResourceTimeConstraint
    subject_rows: list        # [(riga SubjectConstraint, unit_keys precalcolate)]
    x: dict = field(default_factory=dict)        # (id, giorno, fascia) → BoolVar
    by_cell: dict = field(default_factory=dict)  # (chiave, giorno, fascia) → [(id, letterale)]
    vocab: object = None      # Vocabulary, assegnato da build_model

    @classmethod
    def build(cls, schedule, extraction=None):
        signatures = week_signatures(schedule)
        states = {rep: ScheduleState.build(schedule, week=rep) for rep, _ in signatures}
        base = states[signatures[0][0]]
        grid = base.grid
        placed = {p.activity_id: (p.day, p.start_slot)
                  for p in schedule.placements.all()}
        selected = (None if extraction is None
                    else set(extraction.activities.values_list("id", flat=True)))

        activities, free, cells, tokens = {}, set(), {}, {}
        for state in states.values():
            for aid, act in state.activities.items():
                if aid in activities:
                    continue
                movable = (act.immobility not in _IMMOBILE
                           and (selected is None or aid in selected))
                if movable:
                    free.add(aid)
                    cells[aid] = {
                        (d, s)
                        for d in range(grid.days_per_cycle)
                        for s in range(grid.slots_per_day - act.duration_slots + 1)
                    }
                elif aid in placed:
                    # congelata: il dominio è la sua collocazione attuale, e
                    # basta questo a rendere gratis il piazzamento incrementale
                    cells[aid] = {placed[aid]}
                else:
                    # non muovibile e mai piazzata: non c'è niente a cui
                    # congelarla, e nell'orario non occupa nulla. Fuori.
                    continue
                activities[aid] = act
                tokens[aid] = state.tokens[aid]

        material_quantity = {}
        for state in states.values():
            for (aid, key), quantity in state.material_quantity.items():
                if aid in activities:
                    material_quantity[(aid, key)] = quantity

        return cls(
            schedule=schedule, grid=grid, signatures=signatures, states=states,
            activities=activities, free=free, cells=cells, tokens=tokens,
            capacity=base.capacity, material_quantity=material_quantity,
            time_rows=base.time_rows, subject_rows=base.subject_rows,
        )

    def index_cells(self):
        """(chiave, giorno, fascia) → [(id attività, letterale)]. Costruito una
        volta sola dopo la creazione delle variabili: i builder lo leggono, non
        lo ricalcolano."""
        index = defaultdict(list)
        for aid, act in self.activities.items():
            for (d, s) in self.cells[aid]:
                lit = self.x[(aid, d, s)]
                for key in self.tokens[aid]:
                    for slot in range(s, s + act.duration_slots):
                        index[(key, d, slot)].append((aid, lit))
        self.by_cell = dict(index)

    def has_free(self, key, day, slot):
        """C'è almeno un'attività libera che può occupare quella cella? Se no,
        il constraint è un fatto e non una decisione: non si posta."""
        return any(aid in self.free
                   for aid, _ in self.by_cell.get((key, day, slot), ()))

