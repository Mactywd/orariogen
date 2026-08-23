"""Griglia: la durata sta nella giornata, l'intervallo non si attraversa, il
giorno festivo non esiste. Pre-filtro del dominio, non constraint.

Un'attività ha **una** collocazione per tutte le sue settimane: un giorno
festivo anche in una sola delle settimane in cui l'attività è attiva esce dal
dominio. È la stessa lettura del checker, che segnalerebbe quella settimana."""

from domain.solver.registry import Builder, register


@register("structural:grid")
class GridBuilder(Builder):
    def restrict(self, ctx):
        grid = ctx.grid
        boundaries = ctx.states[ctx.signatures[0][0]].break_boundaries
        for aid in ctx.free:
            act = ctx.activities[aid]
            holidays = set()
            for rep, _ in ctx.signatures:
                if aid in ctx.states[rep].activities:
                    holidays |= ctx.states[rep].holidays
            ctx.cells[aid] = {
                (day, slot) for (day, slot) in ctx.cells[aid]
                if day < grid.days_per_cycle
                and day not in holidays
                and slot + act.duration_slots <= grid.slots_per_day
                and not (act.respects_breaks and any(
                    slot < b < slot + act.duration_slots for b in boundaries))
            }
