"""Il modello della seconda fase: capienza, firme di settimana, ADR-018."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Activity, Room
from domain.solver.rooms import build_room_model
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _risolvi(schedule, **kw):
    model, ctx = build_room_model(schedule, **kw)
    solver = cp_model.CpSolver()
    return solver.Solve(model), solver, ctx


def test_due_attivita_nella_stessa_cella_non_stanno_in_un_aula_da_uno():
    """La regola della casa: si **forza** la violazione e si attende
    INFEASIBLE, invece di risolvere e guardare dove e' finita."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE


def test_la_capienza_due_ne_ammette_due():
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=2)
    a = make_activity(env["subject"], rooms=[pal])
    b = make_activity(env["subject"], rooms=[pal])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_con_la_rinuncia_ammessa_una_resta_senza_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assegnate = sum(solver.Value(v) for v in ctx.assigned.values())
    assert assegnate == 1


def test_settimane_disgiunte_non_competono():
    """Due attivita' nella stessa cella su settimane disgiunte condividono
    un'aula a capienza 1: le firme sono una dimensione, non un dettaglio."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    pari = make_activity(env["subject"], rooms=[lab], mask=0b0101)
    dispari = make_activity(env["subject"], rooms=[lab], mask=0b1010)
    place(env["schedule"], pari, 0, 0)
    place(env["schedule"], dispari, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_adr018_due_immobili_che_saturano_non_bloccano_il_modello():
    """`INFEASIBLE` che nasce dal vietare un peggioramento e' ammesso; quello
    che nasce dal **pretendere una riparazione** no. Due immobili che saturano
    da sole una palestra sono una violazione gia' scritta: la fase assegna il
    resto e il checker la nomina."""
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=1)
    altra = Room.objects.create(name="ALTRA", simultaneous_capacity=1)
    for _ in range(2):
        bloccata = make_activity(env["subject"], rooms=[pal],
                                 immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], bloccata, 0, 0, room=pal)
    libera = make_activity(env["subject"], rooms=[altra])
    place(env["schedule"], libera, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(ctx.assigned[libera.id]) == 1


def test_il_dominio_vuoto_con_la_rinuncia_vietata_e_infattibile():
    env = mini_school()
    from domain.models import ResourceUnavailability
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE
