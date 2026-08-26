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


def test_subject_bucket_usa_la_fascia_di_partenza():
    """Un'attivita' di due fasce che inizia alle 3, con la linea di meta'
    giornata a 4, appartiene alla MATTINA per intero: i vincoli di materia
    attribuiscono l'attivita' al secchio della fascia di partenza."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=2)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 3)] == 1)
    keys = frozenset({env["klass"].pk})
    mattina = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 0)
    pomeriggio = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(mattina) == 1
    assert solver.Value(pomeriggio) == 0


def test_subject_bucket_ignora_le_altre_materie_e_le_altre_unita():
    env = mini_school()
    from domain.models import SchoolClass, Subject
    altra_materia = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    altra_classe = SchoolClass.objects.create(
        name="1B", study_plan=env["plan"], year=1)
    a = make_activity(altra_materia, teachers=[env["teacher"]], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[altra_classe])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 0)] == 1)
    giorno = vocab.subject_bucket(
        frozenset({env["klass"].pk}), env["subject"].pk, "day", 0)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(giorno) == 0


def test_pos_canalizza_giorno_e_fascia():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 2, 3)] == 1)
    p = vocab.pos(a.id)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(p) == 2 * env["grid"].slots_per_day + 3


def test_site_occupied_distingue_le_sedi():
    env = mini_school()
    from domain.models import Site
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=centrale)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    key = env["klass"].pk
    qui = vocab.site_occupied(key, 0, 0, centrale.pk)
    altrove = vocab.site_occupied(key, 0, 0, succursale.pk)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(qui) == 1
    assert solver.Value(altrove) == 0
