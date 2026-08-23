"""Il contesto: celle ammissibili, congelamento, indice per cella."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Extraction
from domain.solver.context import SolverContext
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_celle_iniziali_secondo_la_durata():
    env = mini_school()
    a = make_activity(env["subject"], slots=1)
    b = make_activity(env["subject"], slots=2)
    ctx = SolverContext.build(env["schedule"])
    assert len(ctx.cells[a.id]) == 30   # 5 giorni x 6 fasce
    assert len(ctx.cells[b.id]) == 25   # 5 giorni x 5 partenze possibili
    assert ctx.free == {a.id, b.id}


def test_attivita_fissa_congelata_alla_sua_cella():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    place(env["schedule"], a, day=2, slot=3)
    ctx = SolverContext.build(env["schedule"])
    assert ctx.cells[a.id] == {(2, 3)}
    assert a.id not in ctx.free


def test_attivita_fissa_mai_piazzata_esce_dal_modello():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    ctx = SolverContext.build(env["schedule"])
    assert a.id not in ctx.activities


def test_estrazione_libera_solo_le_sue_attivita():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], b, day=1, slot=1)
    estrazione = Extraction.objects.create(name="lavoro")
    estrazione.activities.add(a)
    ctx = SolverContext.build(env["schedule"], extraction=estrazione)
    assert ctx.free == {a.id}
    assert ctx.cells[b.id] == {(1, 1)}   # il resto e' dato


def test_token_e_capacita_arrivano_dallo_stato():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx = SolverContext.build(env["schedule"])
    assert env["teacher"].pk in ctx.tokens[a.id]
    assert env["klass"].pk in ctx.tokens[a.id]
    assert ctx.capacity[env["teacher"].pk] == 1


def test_indice_per_cella_e_canalizzazione():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    ctx = SolverContext.build(env["schedule"])
    model = cp_model.CpModel()
    for (d, s) in sorted(ctx.cells[a.id]):
        ctx.x[(a.id, d, s)] = model.NewBoolVar(f"x_{d}_{s}")
    ctx.index_cells()
    key = env["teacher"].pk
    # durata 2: partendo da (0, 0) copre le fasce 0 e 1
    assert (a.id, ctx.x[(a.id, 0, 0)]) in ctx.by_cell[(key, 0, 1)]
    assert ctx.has_free(key, 0, 1) is True
    assert ctx.has_free(key, 0, 99) is False
    occ = ctx.occupied(model, key, 0, 0)
    assert ctx.occupied(model, key, 0, 0) is occ   # memoizzato
