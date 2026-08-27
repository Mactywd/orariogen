"""La richiesta d'aula insoddisfatta, e l'occupazione a candidata unica."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.state import ScheduleState, activity_tokens
from domain.models import Room
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _codici(schedule):
    return [f.code for f in check_schedule(schedule)]


def test_l_attivita_piazzata_che_chiede_un_aula_senza_assegnazione_e_nominata():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert "room_unassigned" in _codici(env["schedule"])


def test_con_l_aula_assegnata_la_richiesta_e_chiusa():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    assert "room_unassigned" not in _codici(env["schedule"])


def test_l_attivita_non_piazzata_non_chiede_nessuna_aula():
    """Senza collocazione non c'e' nessuna cella da occupare: la richiesta non
    esiste ancora, e nominarla sarebbe rumore su ogni orario vuoto."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    assert "room_unassigned" not in _codici(env["schedule"])


def test_chi_non_chiede_aule_non_e_mai_nominato():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    assert "room_unassigned" not in _codici(env["schedule"])


def test_due_candidate_non_occupano_finche_nessuna_e_assegnata():
    """Sovrastimare inventerebbe conflitti che l'assegnazione risolverebbe:
    e' il falso positivo per cui il violatore di Hall e' stato riscritto."""
    env = mini_school()
    p1 = Room.objects.create(name="PALESTRA 1")
    p2 = Room.objects.create(name="PALESTRA 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    keys, _ = activity_tokens(a)
    assert p1.pk not in keys and p2.pk not in keys


def test_la_candidata_unica_occupa_anche_senza_assegnazione():
    """A cardinalita' uno la scelta e' determinata, quindi occupare e' esatto —
    ed e' il prodotto: un'attivita' porta il conto di tutte e cinque le
    risorse, aula compresa."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], rooms=[lab])
    keys, _ = activity_tokens(a)
    assert lab.pk in keys


def test_l_assegnazione_vince_sulle_candidate():
    env = mini_school()
    p1 = Room.objects.create(name="PALESTRA 1")
    p2 = Room.objects.create(name="PALESTRA 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    keys, _ = activity_tokens(a, assigned_room_id=p2.pk)
    assert p2.pk in keys and p1.pk not in keys


def test_lo_stato_registra_l_aula_assegnata():
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0, room=lab)
    state = ScheduleState.build(env["schedule"])
    assert state.assigned_room == {a.id: lab.pk}
