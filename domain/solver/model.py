"""Il modello CP-SAT: variabili booleane x[a][d][s], esecuzione, scrittura dei
piazzamenti. L'ordine è obbligato: contesto → restrict() di tutti i builder →
creazione delle variabili sulle celle sopravvissute → build() di tutti."""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from domain.models import Placement
from domain.solver.context import SolverContext
from domain.solver.registry import all_builders
from domain.solver.vocabulary import Vocabulary

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
    unplaced: tuple = ()   # id delle attività scartate, nominate dal checker
                           # structural:placement una volta scritte


def build_model(schedule, extraction=None, allow_unplaced=True):
    """`allow_unplaced=False` pretende il piazzamento di ogni attività libera:
    è il modello di prima dello scarto, e resta il modo di chiedere «questo
    vincolo morde?». Con lo scarto ammesso la risposta a una violazione forzata
    non è più l'infattibilità ma la **rinuncia**, che è un'altra domanda."""
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
        if aid not in ctx.free:
            # congelata: dominio di cardinalità uno, e il suo letterale vale 1
            # a tempo di costruzione. È la premessa su cui poggia ADR-018.
            model.AddExactlyOne(lits)
            continue
        # Il modello ha smesso di pretendere il piazzamento: un'attività può
        # restare **scartata**, com'è in EDT. `piazzata` è la variabile che lo
        # dice, e la somma dei letterali di cella le è uguale — con dominio
        # vuoto (nessuna cella sopravvive ai pre-filtri) vale zero, cioè
        # l'attività è scartata invece di rendere infattibile tutto il modello.
        if not allow_unplaced:
            if lits:
                model.AddExactlyOne(lits)
            else:
                # dominio vuoto e piazzamento preteso: il modello è infattibile,
                # e va detto in modo esplicito.
                vuoto = model.NewBoolVar(f"dominio_vuoto_{aid}")
                model.Add(vuoto == 1)
                model.Add(vuoto == 0)
            continue
        piazzata = model.NewBoolVar(f"piazzata_{aid}")
        ctx.placed_var[aid] = piazzata
        model.Add(sum(lits) == piazzata)

    ctx.index_cells()
    ctx.vocab = Vocabulary(ctx, model)
    for builder in builders:
        builder.build(ctx, model)
    return model, ctx


def solve(schedule, extraction=None, time_limit=None, allow_unplaced=True,
          workers=None):
    """`workers=1` rende la ricerca **riproducibile**. Serve ai test che
    osservano *quale* ottimo torna e non solo che ne torni uno: con più
    lavoratori CP-SAT restituisce l'ottimo che il primo thread trova, e due
    esecuzioni della stessa istanza possono dare due orari diversi — entrambi
    ottimi, ma con fenomeni diversi da osservare."""
    started = time.monotonic()
    model, ctx = build_model(schedule, extraction=extraction,
                             allow_unplaced=allow_unplaced)
    # L1 — si minimizzano le **ore** scartate, non il numero di attività (D1
    # della spec): uno scarto da 3h fa più danno al monte ore di una classe di
    # tre da 1h. Senza questo obiettivo «scarta tutto» è ammissibile, e CP-SAT
    # la restituisce in un millisecondo.
    if ctx.placed_var:
        totale = sum(ctx.activities[aid].duration_minutes for aid in ctx.placed_var)
        scarti = model.NewIntVar(0, totale, "minuti_scartati")
        model.Add(scarti == sum(ctx.activities[aid].duration_minutes * (1 - piazzata)
                                for aid, piazzata in ctx.placed_var.items()))
        model.Minimize(scarti)
    solver = cp_model.CpSolver()
    if workers is not None:
        solver.parameters.num_workers = int(workers)
    if ctx.placed_var:
        # ⚠ Misurato, e non è un dettaglio di prestazioni: senza questo, la
        # presolve **espande l'obiettivo** («objective: expanded via tight
        # equality», 36 volte su un testimone da 32 attività). I booleani
        # `piazzata` spariscono, al loro posto entrano nell'obiettivo 723
        # letterali di cella, e il dominio iniziale passa da [0, 660] a
        # [-35460, 2040]. Il solver trova `best:0` in un decimo di secondo e
        # poi spende **sessanta secondi** a dimostrare che non esiste un ottimo
        # negativo — che è vero per costruzione, ma non lo è più per lui.
        # Con la sostituzione spenta: `OPTIMAL` in 0,09 s.
        # ⚠ Il dominio dichiarato dell'IntVar da solo **non basta**: anche lui
        # viene sostituito. Misurato: bound -720, sempre 15 s pieni.
        solver.parameters.presolve_substitution_level = 0
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.Solve(model)

    placements, unplaced = {}, ()
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (aid, day, slot), var in ctx.x.items():
            if solver.Value(var):
                placements[aid] = (day, slot)
        unplaced = tuple(sorted(aid for aid in ctx.activities
                                if aid not in placements))

    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return Solution(
        status=_STATUS.get(status, str(status)),
        placements=placements,
        unplaced=unplaced,
        stats={
            "attivita": len(ctx.activities),
            "libere": len(ctx.free),
            "scartate": len(unplaced),
            "minuti_scartati": sum(ctx.activities[aid].duration_minutes
                                   for aid in unplaced),
            "variabili": len(proto.variables),
            "constraint": len(proto.constraints),
            "secondi": round(time.monotonic() - started, 3),
        },
    )


def apply(solution, schedule):
    """Scrive i piazzamenti. Il piazzamento è output, mai un campo
    dell'attività: si sovrascrive la riga, non si duplica. Se lo stato non è
    fattibile non fa nulla: nessun Placement scritto né toccato.

    ⚠ E **cancella** la riga delle attività che la soluzione lascia scartate.
    Senza, un'attività piazzata ieri e scartata oggi resterebbe piazzata nel
    database: l'orario che `check_schedule` legge non sarebbe quello che il
    solver ha deciso, e l'oracolo misurerebbe un orario che non esiste."""
    if solution.status not in ("OPTIMAL", "FEASIBLE"):
        return
    for aid, (day, slot) in solution.placements.items():
        Placement.objects.update_or_create(
            schedule=schedule, activity_id=aid,
            defaults={"day": day, "start_slot": slot})
    if solution.unplaced:
        Placement.objects.filter(schedule=schedule,
                                 activity_id__in=solution.unplaced).delete()
