"""Il modello CP-SAT: variabili booleane x[a][d][s], esecuzione, scrittura dei
piazzamenti. L'ordine è obbligato: contesto → restrict() di tutti i builder →
creazione delle variabili sulle celle sopravvissute → build() di tutti."""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from domain.models import Placement
from domain.solver.context import SolverContext
from domain.solver.registry import all_builders

_STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


@dataclass(frozen=True)
class Solution:
    status: str
    placements: dict   # id attività → (giorno, fascia di inizio)
    stats: dict


def build_model(schedule, extraction=None):
    ctx = SolverContext.build(schedule, extraction=extraction)
    builders = all_builders()
    for builder in builders:
        builder.restrict(ctx)

    model = cp_model.CpModel()
    for aid in sorted(ctx.activities):
        lits = []
        for (day, slot) in sorted(ctx.cells[aid]):
            var = model.NewBoolVar(f"x_{aid}_{day}_{slot}")
            ctx.x[(aid, day, slot)] = var
            lits.append(var)
        if lits:
            model.AddExactlyOne(lits)
        else:
            # dominio vuoto: nessuna collocazione sopravvive ai pre-filtri.
            # Il modello è infattibile, e va detto in modo esplicito.
            vuoto = model.NewBoolVar(f"dominio_vuoto_{aid}")
            model.Add(vuoto == 1)
            model.Add(vuoto == 0)

    ctx.index_cells()
    for builder in builders:
        builder.build(ctx, model)
    return model, ctx


def solve(schedule, extraction=None, time_limit=None):
    started = time.monotonic()
    model, ctx = build_model(schedule, extraction=extraction)
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.Solve(model)

    placements = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (aid, day, slot), var in ctx.x.items():
            if solver.Value(var):
                placements[aid] = (day, slot)

    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return Solution(
        status=_STATUS.get(status, str(status)),
        placements=placements,
        stats={
            "attivita": len(ctx.activities),
            "libere": len(ctx.free),
            "variabili": len(proto.variables),
            "constraint": len(proto.constraints),
            "secondi": round(time.monotonic() - started, 3),
        },
    )


def apply(solution, schedule):
    """Scrive i piazzamenti. Il piazzamento è output, mai un campo
    dell'attività: si sovrascrive la riga, non si duplica."""
    for aid, (day, slot) in solution.placements.items():
        Placement.objects.update_or_create(
            schedule=schedule, activity_id=aid,
            defaults={"day": day, "start_slot": slot})
