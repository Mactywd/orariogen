"""I due livelli della seconda fase, e la scrittura."""
import pytest

from domain.models import Placement, Room
from domain.solver.rooms import apply_rooms, solve_rooms
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_l1_preferisce_lasciare_fuori_l_ora_singola():
    """L1 conta i **minuti**: un blocco da 2h che resta senza spazio fa piu'
    danno di un'ora singola, quindi a parita' di celle e' la singola a
    rinunciare."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    lungo = make_activity(env["subject"], rooms=[lab], slots=2)
    corto = make_activity(env["subject"], rooms=[lab], slots=1)
    place(env["schedule"], lungo, 0, 0)
    place(env["schedule"], corto, 0, 1)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == (corto.id,)
    assert soluzione.stats["minuti_senza_aula"] == 60


def test_l2_conserva_l_assegnazione_precedente():
    env = mini_school()
    p1 = Room.objects.create(name="PAL 1")
    p2 = Room.objects.create(name="PAL 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    place(env["schedule"], a, 0, 0, room=p2)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.assignments == {a.id: p2.pk}
    assert soluzione.stats["livelli"][1]["valore"] == 0


def test_la_stabilita_non_vale_una_rinuncia():
    """L1 prima di L2: conservare una collocazione non vale un'aula in meno.
    L'aula di prima e' contesa, quindi tenerla costerebbe una rinuncia."""
    env = mini_school()
    conteso = Room.objects.create(name="LAB", simultaneous_capacity=1)
    libero = Room.objects.create(name="ALTRO", simultaneous_capacity=1)
    vecchia = make_activity(env["subject"], rooms=[conteso, libero])
    nuova = make_activity(env["subject"], rooms=[conteso])
    place(env["schedule"], vecchia, 0, 0, room=conteso)
    place(env["schedule"], nuova, 0, 0)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == ()
    assert soluzione.assignments[vecchia.id] == libero.pk
    assert soluzione.stats["livelli"][1]["valore"] == 1


def test_apply_scrive_l_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    apply_rooms(solve_rooms(env["schedule"]), env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id == lab.pk


def test_apply_cancella_l_aula_di_chi_resta_senza():
    """⚠ La mutazione che nel pezzo 3 era passata inosservata: senza la
    cancellazione, l'aula di ieri resterebbe scritta e `check_schedule`
    leggerebbe un orario che il solver non ha deciso."""
    env = mini_school()
    from domain.models import ResourceUnavailability
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    soluzione = solve_rooms(env["schedule"])
    assert soluzione.unassigned == (a.id,)
    apply_rooms(soluzione, env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id is None
