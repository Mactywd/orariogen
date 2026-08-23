"""MAX_GAP_HOURS — il D.T.B., «durata tollerata dei buchi».

⚠ È un **budget settimanale**, non una soglia per singolo buco: il checker
somma i minuti di buco su tutte le mezze giornate della settimana e confronta
il totale una volta sola. Qui la stessa cosa, in forma lineare e senza big-M:
per ogni mezza giornata, `covered[s] = before[s] AND after[s]` dice se la
fascia sta fra la prima e l'ultima occupata, e i minuti di buco sono
`slot_minutes * somma(covered[s] - occ[s])` — ogni termine non negativo perché
`occ[s]` implica `covered[s]`.

I buchi non si contano mai a cavallo del pranzo: le due mezze giornate sono
separate, come in `_halves` del checker.

Semplificazione dichiarata: questo builder non distingue le firme di settimana
e tratta tutte le attività come co-attive. È conservativo — può vincolare di
più, mai di meno — quindi non può produrre una soluzione che l'oracolo
rifiuta."""

from domain.models import ResourceTimeConstraint
from domain.solver.registry import Builder, register

T = ResourceTimeConstraint.Type


@register(T.MAX_GAP_HOURS)
class MaxGapBuilder(Builder):
    def build(self, ctx, model):
        grid = ctx.grid
        halves = [range(0, grid.morning_end_slot),
                  range(grid.morning_end_slot, grid.slots_per_day)]
        for row in ctx.time_rows:
            if row.type != T.MAX_GAP_HOURS:
                continue
            key = row.resource_id
            if not any(ctx.has_free(key, day, slot)
                       for day in range(grid.days_per_cycle)
                       for slot in range(grid.slots_per_day)):
                continue   # nessuna decisione da prendere su questa risorsa
            terms = []
            for day in range(grid.days_per_cycle):
                for half in halves:
                    occ = {s: ctx.occupied(model, key, day, s) for s in half}
                    for s in half:
                        before = model.NewBoolVar(f"before_{key}_{day}_{s}")
                        model.AddMaxEquality(before, [occ[i] for i in half if i <= s])
                        after = model.NewBoolVar(f"after_{key}_{day}_{s}")
                        model.AddMaxEquality(after, [occ[j] for j in half if j >= s])
                        covered = model.NewBoolVar(f"covered_{key}_{day}_{s}")
                        model.AddMinEquality(covered, [before, after])
                        terms.append(covered - occ[s])
            if terms:
                model.Add(grid.slot_minutes * sum(terms)
                          <= row.params["max_gap_minutes"])
