"""Conformità: occupazione, indisponibilità e la fusione per firme di settimana."""
import pytest

from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.models import Material, ResourceUnavailability
from domain.models.activities import ActivityMaterialRequirement
from tests.analysis_helpers import FULL, make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_orario_pulito_nessun_finding():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    assert check_schedule(env["schedule"]) == []


def test_doppia_occupazione_del_docente():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["resource_occupied"]
    f = findings[0]
    assert f.severity == Severity.HARD
    assert f.resources == (env["teacher"].pk,)
    assert set(f.activities) == {a.id, b.id}
    assert f.quantities["load"] == 2 and f.quantities["capacity"] == 1
    assert f.weeks == (0, 1, 2, 3)  # annuale: la violazione vale ogni settimana


def test_occupante_bloccato_cambia_causale():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], immobility="fixed")
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert check_schedule(env["schedule"])[0].code == "resource_occupied_locked"


def test_maschere_disgiunte_non_confliggono():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b0011)
    b = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b1100)
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert check_schedule(env["schedule"]) == []


def test_picco_materiale_oltre_capacita():
    env = mini_school()
    carrello = Material.objects.create(name="Portatili", simultaneous_capacity=10)
    a = make_activity(env["subject"])
    b = make_activity(env["subject"])
    ActivityMaterialRequirement.objects.create(activity=a, material=carrello, quantity=6)
    ActivityMaterialRequirement.objects.create(activity=b, material=carrello, quantity=6)
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["resource_peak"]
    assert findings[0].quantities["load"] == 12


def test_indisponibilita_tre_livelli():
    env = mini_school()
    for day, level in [(0, "hard"), (1, "optional"), (2, "preference")]:
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=day, slot=0, level=level)
        act = make_activity(env["subject"], teachers=[env["teacher"]])
        place(env["schedule"], act, day=day, slot=0)
    by_code = {f.code: f for f in check_schedule(env["schedule"])}
    assert by_code["unavailability"].severity == Severity.HARD
    assert by_code["unavailability_optional"].severity == Severity.OPTIONAL
    assert by_code["preference"].severity == Severity.PREFERENCE


def test_firme_di_settimana():
    env = mini_school()
    annuale = make_activity(env["subject"], teachers=[env["teacher"]], mask=FULL)
    una_tantum = make_activity(env["subject"], teachers=[env["teacher"]], mask=0b0100)
    place(env["schedule"], annuale, day=0, slot=0)
    place(env["schedule"], una_tantum, day=0, slot=1)
    sigs = week_signatures(env["schedule"])
    reps = sorted(wks for _, wks in sigs)
    assert reps == [(0, 1, 3), (2,)]


# --- Task 4: griglia e sedi ---
import datetime as dt

from domain.models import Break, Holiday, Site


def test_blocco_a_cavallo_dell_intervallo():
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=2)
    rispetta = make_activity(env["subject"], classes=[env["klass"]], slots=2,
                             respects_breaks=True)
    ignora = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    place(env["schedule"], rispetta, day=0, slot=1)   # fasce 1-2: a cavallo
    place(env["schedule"], ignora, day=1, slot=1)
    codes = [f.code for f in check_schedule(env["schedule"])]
    assert codes == ["break_straddled"]


def test_fuori_griglia():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)
    place(env["schedule"], a, day=0, slot=4)  # 4+3 > 6 fasce
    assert [f.code for f in check_schedule(env["schedule"])] == ["slot_out_of_grid"]


def test_giorno_festivo():
    env = mini_school()
    Holiday.objects.create(school_year=env["year"], date=dt.date(2026, 9, 16))  # mer, sett. 0
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=2, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["holiday"]
    assert findings[0].weeks == (0,)  # solo la settimana del festivo


def test_transizione_di_sede_troppo_stretta():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)  # nessuna fascia libera fra le due
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["site_transition"]
    assert findings[0].resources == (env["teacher"].pk,)


def test_transizione_di_sede_con_fascia_libera_ok():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=2)  # una fascia libera = default
    assert check_schedule(env["schedule"]) == []
