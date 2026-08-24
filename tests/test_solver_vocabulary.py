"""Le primitive derivate condivise. Il test che conta e' quello su `covered`:
il parametro `span` distingue il D.T.B. (mezza giornata) da MAX_PRESENCE
(giornata intera), ed e' proprio la differenza che due copie separate del
codice avrebbero perso."""
import pytest
from ortools.sat.python import cp_model

from domain import weeks
from domain.solver.context import SolverContext
from domain.solver.vocabulary import Vocabulary
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _vocab(env):
    ctx = SolverContext.build(env["schedule"])
    model = cp_model.CpModel()
    for aid in sorted(ctx.activities):
        for (day, slot) in sorted(ctx.cells[aid]):
            ctx.x[(aid, day, slot)] = model.NewBoolVar(f"x_{aid}_{day}_{slot}")
        model.AddExactlyOne([ctx.x[(aid, d, s)] for (d, s) in sorted(ctx.cells[aid])])
    ctx.index_cells()
    return ctx, model, Vocabulary(ctx, model)


def test_halves_pomeriggio_puo_essere_vuoto():
    env = mini_school()
    env["grid"].morning_end_slot = env["grid"].slots_per_day
    env["grid"].save()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    _, _, vocab = _vocab(env)
    mattina, pomeriggio = vocab.halves()
    assert len(list(mattina)) == env["grid"].slots_per_day
    assert list(pomeriggio) == []


def test_half_active_su_meta_vuota_non_esplode():
    """AddMaxEquality con lista vuota e' invalido: la primitiva deve fissare
    la variabile a zero invece di costruire un vincolo malformato."""
    env = mini_school()
    env["grid"].morning_end_slot = env["grid"].slots_per_day
    env["grid"].save()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    _, model, vocab = _vocab(env)
    var = vocab.half_active(env["klass"].pk, 0, 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(var) == 0


def test_covered_span_mezza_giornata_contro_giornata_intera():
    """Due attivita' della stessa classe alle fasce 0 e 5, con la linea di
    meta' giornata a 4. Sulla giornata intera le fasce 1..4 sono 'coperte'
    (stanno fra la prima e l'ultima occupata); sulla sola mattina no, perche'
    li' l'ultima occupata e' la fascia 0."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 5)] == 1)
    key = env["klass"].pk
    giornata = vocab.covered(key, 0, range(0, 6))
    mattina = vocab.covered(key, 0, range(0, 4))
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert [solver.Value(giornata[s]) for s in range(6)] == [1, 1, 1, 1, 1, 1]
    assert [solver.Value(mattina[s]) for s in range(4)] == [1, 0, 0, 0]


def test_day_active_e_memoizzazione():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 2, 1)] == 1)
    key = env["klass"].pk
    attivo, di_nuovo = vocab.day_active(key, 2), vocab.day_active(key, 2)
    assert attivo is di_nuovo          # memoizzata: una variabile, non due
    vuoto = vocab.day_active(key, 3)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(attivo) == 1
    assert solver.Value(vuoto) == 0


def test_half_active_caso_positivo_in_mattina():
    """Il test della meta' vuota (sopra) copre solo il caso a zero. Manca il
    caso simmetrico: un'attivita' piazzata in mattina deve accendere
    half_active(..., 0)."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 1)] == 1)   # fascia 1 < morning_end_slot (4): mattina
    key = env["klass"].pk
    var = vocab.half_active(key, 0, 0)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(var) == 1


def test_day_active_distingue_le_firme():
    """Due attivita' su firme di settimana diverse (maschere a un solo bit,
    settimane 0 e 1): A e' attiva solo nella firma della settimana 0, B solo
    in quella della settimana 1. A e' piazzata al giorno 1, B al giorno 0.

    Con la firma passata, day_active(giorno 0, signature=rep_di_A) non deve
    essere alzata dall'occupazione di B — B non e' fra le attivita' attive in
    quella firma, anche se occupa una cella quel giorno. Senza firma, invece,
    la stessa interrogazione conta anche B: e' esattamente il modo in cui
    ometterla e' anti-conservativo su un aggregato per risorsa (il difetto
    gia' trovato in MaxGapBuilder, 2026-08-24)."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]],
                       mask=weeks.single_week(0))
    b = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]],
                       mask=weeks.single_week(1))
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 1, 0)] == 1)   # A: giorno 1, non il giorno 0
    model.Add(ctx.x[(b.id, 0, 4)] == 1)   # B: giorno 0

    rep_a = next(rep for rep, _ in ctx.signatures if a.id in ctx.states[rep].activities)
    assert b.id not in ctx.states[rep_a].activities   # la firma di A esclude B

    key = env["klass"].pk
    con_firma = vocab.day_active(key, 0, signature=rep_a)
    senza_firma = vocab.day_active(key, 0)

    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(con_firma) == 0     # A non e' al giorno 0: nella sua firma, non e' attivo
    assert solver.Value(senza_firma) == 1   # B occupa il giorno 0, e senza firma conta comunque
