# tests/test_fermi_constraints.py
"""L'analisi sul Fermi: capienza pulita per costruzione, l'inversione STO/SCI
rilevata dalla copertura, le indisponibilità dei part-time attive."""
import time

import pytest

from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.domain_size import residual_domain
from domain.analysis.state import ScheduleState
from domain.models import Activity, Placement, Service
from tests import fermi

pytestmark = pytest.mark.django_db


def test_capienza_del_fermi_pulita():
    """Il dataset è risolvibile per costruzione: nessun verdetto negativo."""
    fermi.build()
    assert analyze_capacity() == []


def test_conformita_su_schedule_vuoto_e_solo_attivita_non_piazzate():
    """Senza piazzamenti, l'unico checker che potrebbe scattare sui **dati** è
    la copertura, e sul Fermi corretto non scatta.

    ⚠ Sull'**orario**, invece, scatta `structural:placement`: 284 attività
    tutte «Non piazzata», che è letteralmente lo stato in cui EDT le crea. È
    la ragione per cui il checker esiste — senza, «scarta tutto» sarebbe un
    orario pulito."""
    env = fermi.build()
    findings = check_schedule(env["schedule"])
    assert {f.code for f in findings} == {"activity_unplaced"}
    assert len(findings) == Activity.objects.count() == 284


def test_inversione_sto_sci_rilevata():
    """Il caso reale del 2026-07-09: STO e SCI invertite (3h/2h) nei servizi
    del triennio; i totali quadrano lo stesso, la copertura per materia no."""
    env = fermi.build()
    for year in (3, 4, 5):
        plan = env["plans"][f"SCI{year}"]
        sto = Service.objects.get(study_plan=plan, subject=env["subjects"]["STO"])
        sci = Service.objects.get(study_plan=plan, subject=env["subjects"]["SCI"])
        sto.class_minutes, sci.class_minutes = sci.class_minutes, sto.class_minutes
        sto.save(); sci.save()
    findings = [f for f in check_schedule(env["schedule"])
                if f.code != "activity_unplaced"]   # nessun piazzamento: vedi sopra
    assert all(f.code == "coverage_mismatch" for f in findings)
    assert len(findings) == 12  # 6 classi del triennio × 2 materie


def test_indisponibilita_di_d06_attiva():
    env = fermi.build()
    activity = Activity.objects.filter(teachers=env["teachers"]["D06"]).first()
    Placement.objects.create(schedule=env["schedule"], activity=activity,
                             day=2, start_slot=0)  # giorno indisponibile
    codes = [f.code for f in check_schedule(env["schedule"])]
    assert "unavailability" in codes


def test_sp_su_una_classe_sotto_il_secondo():
    """Prestazioni del dominio residuo: la colonna S.P. di una classe intera
    (26 attività, orario riempito alla buona) in meno di un secondo."""
    env = fermi.build()
    klass = env["classes"]["1A"]
    acts = list(Activity.objects.filter(classes=klass)
                .order_by("-duration_slots", "id"))
    day, slot = 0, 0
    for a in acts:
        if slot + a.duration_slots > 6:
            day, slot = day + 1, 0
        Placement.objects.create(schedule=env["schedule"], activity=a,
                                 day=day, start_slot=slot)
        slot += a.duration_slots
    state = ScheduleState.build(env["schedule"])
    start = time.perf_counter()
    for a in acts:
        residual_domain(a, state)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"colonna S.P. di 1A in {elapsed:.2f}s"
