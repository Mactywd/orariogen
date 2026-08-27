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


def test_il_giallo_restringe_come_il_rosso_il_verde_no():
    """⚠ Correzione del 2026-08-26, e il test si chiamava «giallo e verde non
    restringono». La documentazione dice il contrario: *«Indisponibilità
    opzionali (giallo): rispettata come una rossa, ma l'utente può autorizzare
    il motore a ignorarle»* (inventario-vincoli.md, A2). Il solver era più
    permissivo di EDT su una famiglia intera, e nessun test lo diceva perché il
    test affermava il comportamento sbagliato.

    Il verde resta fuori: è una preferenza, e il suo posto è un livello di
    qualità della catena lessicografica, non un pre-filtro."""
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="optional")
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=1, slot=3, level="preference")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    _, ctx = build_model(env["schedule"])
    assert (0, 3) not in ctx.cells[a.id], "il giallo si rispetta"
    assert (1, 3) in ctx.cells[a.id], "il verde no"


def test_l_override_delle_gialle_e_per_tipo_di_risorsa():
    """L'opzione di calcolo di EDT: «Piazza le attività anche sulle fasce con
    indisponibilità opzionali», dichiarata **per categoria** di risorsa e non
    per la singola (A4: l'override non è selettivo).

    Qui il docente è ignorato e la classe no: la cella gialla del docente torna
    disponibile, quella della classe resta vietata."""
    from domain.models import Resource

    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=3, level="optional")
    ResourceUnavailability.objects.create(
        resource=env["klass"], day=1, slot=3, level="optional")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    _, ctx = build_model(env["schedule"],
                         ignora_opzionali=[Resource.Kind.TEACHER])
    assert (0, 3) in ctx.cells[a.id], "la gialla del docente è ignorata"
    assert (1, 3) not in ctx.cells[a.id], "quella della classe no"


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
