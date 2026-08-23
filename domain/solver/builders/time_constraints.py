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

⚠ Questo builder **distingue le firme di settimana**: posta un budget per
ogni `(rep, _)` di `ctx.signatures`, con i letterali `occ` filtrati alle sole
attività attive in quella firma. La semplificazione «tutte le attività
co-attive» — usata altrove nello spike (`subject_constraints.py`) — qui
**non è conservativa**, ed è il difetto trovato in review: il buco è
`ultima − prima + 1 − conteggio`. Un'occupazione che cade *dentro* il buco ma
viene da un'attività di un'**altra** firma di settimana alza il `conteggio`
senza toccare `prima` né `ultima` — quindi **riempie** il buco nel modello
unione, mentre nelle settimane reali quel buco resta scoperto. Trattare tutto
come co-attivo vincola quindi **di meno**, non di più: può accettare
piazzamenti che il checker, valutando ogni firma per conto proprio, rifiuta.
(Per `subject_constraints.py` la stessa semplificazione resta genuinamente
conservativa: più letterali significano una somma più vincolata, mai il
contrario — lì il caso pessimo è perdere qualche soluzione, mai accettarne di
illegali.)

Le firme diverse con lo stesso insieme di attività attive sulla risorsa
producono lo stesso vincolo: deduplicate con `posted`, come fa
`OccupationBuilder`."""

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
            posted = set()
            for rep, _ in ctx.signatures:
                active = ctx.states[rep].activities
                touching = frozenset(
                    aid
                    for day in range(grid.days_per_cycle)
                    for slot in range(grid.slots_per_day)
                    for aid, _ in ctx.by_cell.get((key, day, slot), ())
                    if aid in active
                )
                if not any(aid in ctx.free for aid in touching):
                    continue   # nessuna decisione da prendere in questa firma
                if touching in posted:
                    continue   # firma diversa, stesso insieme di attivita' attive
                posted.add(touching)
                terms = []
                for day in range(grid.days_per_cycle):
                    for half in halves:
                        occ = {s: ctx.occupied(model, key, day, s, signature=rep)
                               for s in half}
                        for s in half:
                            before = model.NewBoolVar(f"before_{key}_{rep}_{day}_{s}")
                            model.AddMaxEquality(before, [occ[i] for i in half if i <= s])
                            after = model.NewBoolVar(f"after_{key}_{rep}_{day}_{s}")
                            model.AddMaxEquality(after, [occ[j] for j in half if j >= s])
                            covered = model.NewBoolVar(f"covered_{key}_{rep}_{day}_{s}")
                            model.AddMinEquality(covered, [before, after])
                            terms.append(covered - occ[s])
                if terms:
                    model.Add(grid.slot_minutes * sum(terms)
                              <= row.params["max_gap_minutes"])
