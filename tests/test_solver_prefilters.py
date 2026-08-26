"""Griglia e indisponibilità: pre-filtri del dominio, non constraint."""
import datetime as dt

import pytest

from domain.models import Break, Holiday, ResourceUnavailability
from domain.solver.model import build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_il_giorno_festivo_esce_dal_dominio():
    env = mini_school()
    Holiday.objects.create(school_year=env["year"], date=dt.date(2026, 9, 16))  # merc. sett. 0
    a = make_activity(env["subject"])
    _, ctx = build_model(env["schedule"])
    assert all(giorno != 2 for (giorno, _) in ctx.cells[a.id])
    assert len(ctx.cells[a.id]) == 24   # 4 giorni x 6 fasce


def test_l_intervallo_non_si_attraversa_se_l_attivita_lo_rispetta():
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=4)
    a = make_activity(env["subject"], slots=2, respects_breaks=True)
    b = make_activity(env["subject"], slots=2)   # non lo rispetta
    _, ctx = build_model(env["schedule"])
    assert (0, 3) not in ctx.cells[a.id]   # coprirebbe le fasce 3 e 4
    assert (0, 3) in ctx.cells[b.id]


def test_l_indisponibilita_rossa_toglie_la_cella():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    _, ctx = build_model(env["schedule"])
    assert (0, 3) not in ctx.cells[a.id]
    assert (0, 2) in ctx.cells[a.id]


def test_l_indisponibilita_vale_su_tutta_la_durata():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    _, ctx = build_model(env["schedule"])
    assert (0, 2) not in ctx.cells[a.id]   # coda sull'indisponibilita'
    assert (0, 3) not in ctx.cells[a.id]
    assert (0, 1) in ctx.cells[a.id]


def test_giallo_e_verde_non_restringono():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="optional")
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=1, slot=3, level="preference")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    _, ctx = build_model(env["schedule"])
    assert (0, 3) in ctx.cells[a.id] and (1, 3) in ctx.cells[a.id]


def test_l_attivita_congelata_non_viene_ripulita():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]], immobility="fixed")
    place(env["schedule"], a, day=0, slot=3)
    soluzione = solve(env["schedule"])
    assert soluzione.placements[a.id] == (0, 3)   # il piazzamento esistente e' un dato


def test_dominio_azzerato_dai_prefiltri_da_uno_scarto():
    """Un docente indisponibile tutta la settimana: nessuna cella sopravvive
    al pre-filtro. L'attivita' resta scartata, e con `allow_unplaced=False` —
    il modello che pretende il piazzamento — torna a essere infattibile."""
    env = mini_school()
    for giorno in range(5):
        for fascia in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=giorno, slot=fascia, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    soluzione = solve(env["schedule"])
    assert soluzione.unplaced == (a.id,), soluzione.stats
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"
