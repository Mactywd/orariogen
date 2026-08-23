"""Incompatibilita' nella giornata: A = B e' il caso dominante nei dati EDT."""
import pytest

from domain.models import ClassPart, ClassPartition, Subject, SubjectConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = SubjectConstraint.Type


def _riga(materia_a, materia_b, **unita):
    return SubjectConstraint.objects.create(
        subject_a=materia_a, subject_b=materia_b,
        type=T.SAME_DAY_INCOMPATIBLE, **unita)


def test_la_materia_con_se_stessa_una_volta_al_giorno():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[env["klass"]])
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_sei_ore_della_stessa_materia_in_cinque_giorni_e_infattibile():
    env = mini_school()
    for _ in range(6):
        make_activity(env["subject"], classes=[env["klass"]])
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    assert solve(env["schedule"]).status == "INFEASIBLE"


def test_due_materie_diverse_non_coesistono_nella_giornata():
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(matematica, classes=[env["klass"]])
    _riga(env["subject"], matematica, school_class=env["klass"])
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_la_riga_su_una_parte_vincola_solo_quella_parte():
    """Sei ore su TED sarebbero infattibili se il vincolo di ING la toccasse:
    sei giorni non ci sono. Che l'istanza resti fattibile e' la prova che il
    vincolo non e' tracimato sull'altra parte."""
    env = mini_school()
    partizione = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=partizione)
    ted = ClassPart.objects.create(name="1A_TED", partition=partizione)
    a = make_activity(env["subject"], parts=[ing])
    b = make_activity(env["subject"], parts=[ing])
    for _ in range(6):
        make_activity(env["subject"], parts=[ted])
    _riga(env["subject"], env["subject"], class_part=ing)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert soluzione.placements[a.id][0] != soluzione.placements[b.id][0]


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    _riga(env["subject"], env["subject"], school_class=env["klass"])
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")
