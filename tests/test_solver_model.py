"""Variabili, esecuzione, scrittura dei piazzamenti. Nessun builder registrato
in questo task: qui si verifica solo l'ossatura."""
import pytest

from domain.models import Placement
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_una_variabile_per_cella_e_una_sola_collocazione():
    env = mini_school()
    a = make_activity(env["subject"], slots=2)
    model, ctx = build_model(env["schedule"])
    assert len(ctx.x) == 25
    assert all(chiave[0] == a.id for chiave in ctx.x)


def test_solve_piazza_ogni_attivita_dentro_il_suo_dominio():
    env = mini_school()
    a = make_activity(env["subject"])
    b = make_activity(env["subject"], slots=2)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert set(soluzione.placements) == {a.id, b.id}
    for aid, (giorno, fascia) in soluzione.placements.items():
        assert 0 <= giorno < 5
        assert (giorno, fascia) in build_model(env["schedule"])[1].cells[aid]


def test_apply_scrive_i_piazzamenti():
    env = mini_school()
    a = make_activity(env["subject"])
    soluzione = solve(env["schedule"])
    apply(soluzione, env["schedule"])
    riga = Placement.objects.get(schedule=env["schedule"], activity=a)
    assert (riga.day, riga.start_slot) == soluzione.placements[a.id]


def test_apply_sovrascrive_un_piazzamento_esistente():
    env = mini_school()
    a = make_activity(env["subject"])
    place(env["schedule"], a, day=4, slot=5)
    soluzione = solve(env["schedule"])
    apply(soluzione, env["schedule"])
    assert Placement.objects.filter(schedule=env["schedule"], activity=a).count() == 1


def test_attivita_congelata_resta_dove_sta():
    env = mini_school()
    a = make_activity(env["subject"], immobility="fixed")
    place(env["schedule"], a, day=3, slot=2)
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id] == (3, 2)


def test_dominio_vuoto_rende_il_modello_infattibile():
    env = mini_school()
    make_activity(env["subject"], slots=7)   # la griglia ne ha 6
    soluzione = solve(env["schedule"])
    assert soluzione.status == "INFEASIBLE"


def test_le_statistiche_ci_sono():
    env = mini_school()
    make_activity(env["subject"])
    stats = solve(env["schedule"]).stats
    assert stats["attivita"] == 1 and stats["libere"] == 1
    assert stats["variabili"] > 0 and stats["secondi"] >= 0
