"""Il modello CP-SAT: variabili booleane x[a][d][s], esecuzione, scrittura dei
piazzamenti. L'ordine è obbligato: contesto → restrict() di tutti i builder →
creazione delle variabili sulle celle sopravvissute → build() di tutti."""

import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from domain.models import Placement
from domain.solver.context import SolverContext
from domain.solver.objective import STATUS_NAME, livelli, solve_chain
from domain.solver.registry import all_builders
from domain.solver.vocabulary import Vocabulary


@dataclass(frozen=True)
class Solution:
    status: str
    placements: dict   # id attività → (giorno, fascia di inizio)
    stats: dict
    unplaced: tuple = ()   # id delle attività scartate, nominate dal checker
                           # structural:placement una volta scritte


def build_model(schedule, extraction=None, allow_unplaced=True,
                ignora_opzionali=(), pinned=None):
    """`allow_unplaced=False` pretende il piazzamento di ogni attività libera:
    è il modello di prima dello scarto, e resta il modo di chiedere «questo
    vincolo morde?». Con lo scarto ammesso la risposta a una violazione forzata
    non è più l'infattibilità ma la **rinuncia**, che è un'altra domanda.

    `ignora_opzionali` porta i `Resource.Kind` per cui le indisponibilità
    **gialle** non si rispettano: è l'opzione di calcolo di EDT «Piazza le
    attività anche sulle fasce con indisponibilità opzionali», che si dichiara
    per categoria di risorsa e non per la singola.

    `pinned` — `{id attività: (giorno, fascia)}` — impone una collocazione e
    lascia al resto del modello il compito di sistemarsi attorno: è `Piazza e
    sistema` di EDT. ⚠ Una cella che i pre-filtri hanno tolto rende il modello
    **infattibile** invece di essere ignorata in silenzio: un pin che non
    vincola sarebbe la peggiore delle risposte, perché l'utente vedrebbe
    l'attività altrove senza sapere perché."""
    ctx = SolverContext.build(schedule, extraction=extraction,
                              ignora_opzionali=ignora_opzionali)
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
            # ⚠ Anche con `lits` vuoto: `AddExactlyOne([])` è già INFEASIBLE
            # (verificato), che è precisamente ciò che «dominio vuoto e
            # piazzamento preteso» deve significare. Qui c'erano un ramo e un
            # booleano contraddittorio a riprodurlo a mano.
            model.AddExactlyOne(lits)
            continue
        piazzata = model.NewBoolVar(f"piazzata_{aid}")
        ctx.placed_var[aid] = piazzata
        model.Add(sum(lits) == piazzata)

    for aid, (day, slot) in sorted((pinned or {}).items()):
        lit = ctx.x.get((aid, day, slot))
        if lit is None:
            ctx.pin_fuori_dominio.append((aid, day, slot))
            model.AddBoolOr([])     # clausola vuota: falsa, quindi INFEASIBLE
        else:
            model.Add(lit == 1)

    ctx.index_cells()
    ctx.vocab = Vocabulary(ctx, model)
    for builder in builders:
        builder.build(ctx, model)
    # Le quote si postano dopo: nessun builder le conosce, ognuno ha solo
    # chiesto il proprio letterale di violazione (domain/solver/relaxation.py).
    ctx.relax.post_caps(model)
    return model, ctx


def solve(schedule, extraction=None, time_limit=None, allow_unplaced=True,
          workers=None, ignora_opzionali=(), arbitrato=None, pinned=None):
    """`workers=1` rende la ricerca **riproducibile**. Serve ai test che
    osservano *quale* ottimo torna e non solo che ne torni uno: con più
    lavoratori CP-SAT restituisce l'ottimo che il primo thread trova, e due
    esecuzioni della stessa istanza possono dare due orari diversi — entrambi
    ottimi, ma con fenomeni diversi da osservare.

    ⚠ `time_limit` è **per livello** della catena lessicografica, non per la
    chiamata: vedi `solve_chain`.

    `arbitrato` è la separazione per popolazione di EDT: si ottimizza una
    popolazione e si dichiara quanto si è disposti a peggiorare l'altra. Senza,
    catena unica su tutte le righe — che non è ciò che fa EDT, ma è ciò che
    serve a costruire un orario **da zero**, dove non c'è ancora niente da
    peggiorare. Vedi `domain/solver/quality.Arbitrato`."""
    started = time.monotonic()
    model, ctx = build_model(schedule, extraction=extraction,
                             allow_unplaced=allow_unplaced,
                             ignora_opzionali=ignora_opzionali, pinned=pinned)
    catena = livelli(ctx, model, arbitrato)

    atterraggi = {}

    def estrai(solver):
        # ⚠ Si fotografa **insieme** ai piazzamenti, e per la stessa ragione:
        # l'ultimo livello concluso è lo stato che verrà restituito, e leggere
        # i tetti da un altro solver darebbe numeri di un orario diverso.
        atterraggi.update({nome: solver.Value(var)
                           for nome, var in ctx.arbitraggi_var.items()})
        return {aid: (day, slot) for (aid, day, slot), var in ctx.x.items()
                if solver.Value(var)}

    def suggerisci(model, solver):
        """La soluzione appena trovata diventa il suggerimento del livello
        successivo. ⚠ I suggerimenti si **sostituiscono**, non si accumulano:
        `ClearHints` prima, o il proto cresce di una copia per livello."""
        model.ClearHints()
        for var in ctx.x.values():
            model.AddHint(var, solver.Value(var))

    stato, placements, esiti = solve_chain(
        model, catena, estrai=estrai, suggerisci=suggerisci,
        time_limit=time_limit, workers=workers)

    # ⚠ La distinzione è fra «nessuna soluzione» e «una soluzione senza
    # piazzamenti»: un'istanza la cui unica attività è impiazzabile ha
    # `placements` vuoto **ed** è una risposta. Guardare il dizionario invece
    # del `None` fa sparire proprio lo scarto che si voleva nominare.
    trovata = placements is not None
    placements = placements or {}
    unplaced = tuple(sorted(aid for aid in ctx.activities
                            if aid not in placements)) if trovata else ()

    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return Solution(
        status=STATUS_NAME.get(stato, str(stato)),
        placements=placements,
        unplaced=unplaced,
        stats={
            "attivita": len(ctx.activities),
            "libere": len(ctx.free),
            "scartate": len(unplaced),
            "minuti_scartati": sum(ctx.activities[aid].duration_minutes
                                   for aid in unplaced),
            "livelli": tuple(e.as_dict() for e in esiti),
            "arbitraggi": tuple(dict(a, valore=atterraggi.get(a["nome"]))
                                for a in ctx.arbitraggi),
            "pin_fuori_dominio": tuple(ctx.pin_fuori_dominio),
            "lavoratori": workers,
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
