"""Conflitto di risorsa e capacità cumulativa, per firma di settimana."""
import pytest

from domain import weeks
from domain.models import ClassPart, ClassPartition, Material, Room
from domain.models.activities import ActivityMaterialRequirement
from domain.solver.model import solve
from tests.analysis_helpers import FULL, make_activity, mini_school


pytestmark = pytest.mark.django_db


def _stessa_cella(soluzione, a, b):
    return soluzione.placements[a.id] == soluzione.placements[b.id]


def test_due_attivita_dello_stesso_docente_non_coincidono():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert not _stessa_cella(soluzione, a, b)


def test_il_docente_con_troppe_ore_e_infattibile():
    env = mini_school()
    for _ in range(31):   # la griglia ha 30 fasce
        make_activity(env["subject"], teachers=[env["teacher"]])
    assert solve(env["schedule"]).status == "INFEASIBLE"


def test_la_capacita_simultanea_dell_aula_ammette_due_attivita():
    env = mini_school()
    palestra = Room.objects.create(name="PALESTRA", simultaneous_capacity=2)
    a = make_activity(env["subject"], rooms=[palestra])
    b = make_activity(env["subject"], rooms=[palestra])
    c = make_activity(env["subject"], rooms=[palestra])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    celle = [soluzione.placements[x.id] for x in (a, b, c)]
    assert max(celle.count(cella) for cella in celle) <= 2


def test_la_quantita_di_materiale_e_un_vincolo():
    env = mini_school()
    carrello = Material.objects.create(name="Carrello tablet", simultaneous_capacity=3)
    a = make_activity(env["subject"])
    b = make_activity(env["subject"])
    ActivityMaterialRequirement.objects.create(activity=a, material=carrello, quantity=2)
    ActivityMaterialRequirement.objects.create(activity=b, material=carrello, quantity=2)
    soluzione = solve(env["schedule"])
    assert not _stessa_cella(soluzione, a, b)   # 2 + 2 > 3


def test_maschere_disgiunte_condividono_la_cella():
    env = mini_school()
    prima = weeks.single_week(0) | weeks.single_week(1)
    dopo = weeks.single_week(2) | weeks.single_week(3)
    a = make_activity(env["subject"], teachers=[env["teacher"]], mask=prima)
    b = make_activity(env["subject"], teachers=[env["teacher"]], mask=dopo)
    for _ in range(29):
        make_activity(env["subject"], teachers=[env["teacher"]], mask=FULL)
    # 29 annuali + 2 semestrali in 30 fasce: fattibile solo se a e b coincidono
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert _stessa_cella(soluzione, a, b)


def test_parti_di_partizioni_diverse_non_coincidono():
    env = mini_school()
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[ing])
    soluzione = solve(env["schedule"])
    assert not _stessa_cella(soluzione, a, b)   # ADR-017, dentro il solver


def test_parti_della_stessa_partizione_possono_coincidere():
    env = mini_school()
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    alt = ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    for _ in range(29):
        make_activity(env["subject"], classes=[env["klass"]])
    # 29 attivita' a classe intera + le due parti: stanno in 30 fasce solo se
    # le due parti condividono la cella
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert _stessa_cella(soluzione, a, b)
