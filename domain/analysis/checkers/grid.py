"""Vincoli della griglia: fuori griglia, intervalli (respects_breaks), festivi."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:grid")
class GridChecker(Checker):
    def check(self, state, resources=None):
        g = state.grid
        boundaries = [b.boundary_slot for b in g.breaks.all()]
        for aid, pl in sorted(state.placed.items()):
            act = state.activities[aid]
            if resources is not None and not (state.tokens[aid] & resources):
                continue
            if pl.day >= g.days_per_cycle or pl.start_slot + act.duration_slots > g.slots_per_day:
                yield Finding("slot_out_of_grid", causali.message("slot_out_of_grid"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day, "slot": pl.start_slot})
            if act.respects_breaks and any(
                    pl.start_slot < b < pl.start_slot + act.duration_slots
                    for b in boundaries):
                yield Finding("break_straddled", causali.message("break_straddled"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day, "slot": pl.start_slot})
            if pl.day in state.holidays:
                yield Finding("holiday", causali.message("holiday"),
                              Severity.HARD, activities=(aid,),
                              quantities={"day": pl.day})
