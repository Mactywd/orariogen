"""Risorsa occupata e capacità cumulativa: un solo meccanismo per le aule con
capacità simultanea > 1 e per i materiali con quantità, esattamente come nel
checker. Qui entrano gli atomi di ADR-017, che sono chiavi come le altre.

È l'unico builder che distingue le firme di settimana: due attività le cui
maschere non si intersecano possono condividere una cella.

⚠ **ADR-018 qui è la capienza residua, non il gate** (correzione del
2026-08-26, review della PR #1). Il `continue` su `any_free` qui sotto è la
regola dell'implicazione — «c'è qualcosa di **libero** che tocca la cella?» —
e non basta, esattamente come non bastava a `SiteTransitionBuilder`: due
congelate già in conflitto su una cella che una libera può toccare facevano
`model.Add(costante + libere <= capienza)` con la sola costante oltre il
tetto, cioè `INFEASIBLE` per colpa del solo passato. Il checker quello stato
lo prevede e lo nomina (`resource_occupied_locked`, HARD), e ADR-018 dice
testualmente che il solver non è mai infattibile per una violazione
preesistente. Il trattamento è quello di tutti gli altri tetti: `residual_cap`,
clamp a zero, mai un salto del vincolo — se le congelate hanno già saturato la
cella, il residuo è zero e nessuna libera può aggiungersi lì.

⚠ È il difetto che il banco che congela **non poteva trovare**: `sporca()` in
`tests/solver_harness.py` ripacka solo in celle libere da conflitti di
occupazione, e lo asserisce. La famiglia esclusa per costruzione dal banco è
proprio quella in cui lo stesso difetto è sopravvissuto — vedi §9.7 della
spec."""

from domain.solver.registry import Builder, register
from domain.solver.residual import residual_cap


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
                termini = [(ctx.material_quantity.get((aid, key), 1), aid, lit)
                           for aid, lit in here]
                if sum(quantity for quantity, _a, _l in termini) <= capacity:
                    continue   # non potrebbe superarla nemmeno tutte insieme
                signature = (key, day, slot, frozenset(aid for aid, _ in here))
                if signature in posted:
                    continue   # firme di settimana diverse, stesso constraint
                posted.add(signature)
                # ADR-018: il tetto è la capienza **residua**, clampata a zero.
                # A congelate sotto il tetto è identico al vincolo nominale
                # (`costante + libere <= capienza`); cambia solo quando le
                # congelate lo hanno già superato, ed è lì che il vincolo
                # nominale era infattibile per colpa del passato.
                liberi, residuo = residual_cap(ctx, termini, capacity)
                model.Add(sum(quantity * lit for quantity, lit in liberi)
                          <= residuo)
