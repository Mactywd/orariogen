"""Indisponibilità rossa: pre-filtro del dominio, su **tutta** la durata
dell'attività. Il checker itera su tutte le fasce del piazzamento, quindi un
filtro che guardasse solo la cella di partenza lascerebbe passare un'attività
di durata ≥ 2 con la coda sull'indisponibilità.

Giallo e verde non restringono nulla: sono violabili, e il loro trattamento
(override globale, preferenze) è fuori da questo spike."""

from collections import defaultdict

from domain.solver.registry import Builder, register


@register("structural:unavailability")
class UnavailabilityBuilder(Builder):
    def restrict(self, ctx):
        blocked = {}
        for rep, _ in ctx.signatures:
            per_key = defaultdict(set)
            for (key, day, slot), level in ctx.states[rep].unavailability.items():
                if level == "hard":
                    per_key[key].add((day, slot))
            blocked[rep] = per_key

        for aid in ctx.free:
            act = ctx.activities[aid]
            forbidden = set()
            for rep, _ in ctx.signatures:
                if aid not in ctx.states[rep].activities:
                    continue
                per_key = blocked[rep]
                for key in ctx.tokens[aid]:
                    forbidden |= per_key.get(key, set())
            if not forbidden:
                continue
            ctx.cells[aid] = {
                (day, slot) for (day, slot) in ctx.cells[aid]
                if not any((day, s) in forbidden
                           for s in range(slot, slot + act.duration_slots))
            }
