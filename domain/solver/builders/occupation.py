"""Risorsa occupata e capacità cumulativa: un solo meccanismo per le aule con
capacità simultanea > 1 e per i materiali con quantità, esattamente come nel
checker. Qui entrano gli atomi di ADR-017, che sono chiavi come le altre.

È l'unico builder che distingue le firme di settimana: due attività le cui
maschere non si intersecano possono condividere una cella."""

from domain.solver.registry import Builder, register


@register("structural:occupation")
class OccupationBuilder(Builder):
    def build(self, ctx, model):
        posted = set()
        for rep, _ in ctx.signatures:
            active = ctx.states[rep].activities
            for (key, day, slot), entries in ctx.by_cell.items():
                here = [(aid, lit) for aid, lit in entries if aid in active]
                if not any(aid in ctx.free for aid, _ in here):
                    continue   # un fatto, non una decisione
                capacity = ctx.capacity.get(key, 1)
                loads = [(ctx.material_quantity.get((aid, key), 1), lit)
                         for aid, lit in here]
                if sum(quantity for quantity, _ in loads) <= capacity:
                    continue   # non potrebbe superarla nemmeno tutte insieme
                signature = (key, day, slot, frozenset(aid for aid, _ in here))
                if signature in posted:
                    continue   # firme di settimana diverse, stesso constraint
                posted.add(signature)
                model.Add(sum(quantity * lit for quantity, lit in loads) <= capacity)
