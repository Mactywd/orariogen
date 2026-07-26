"""Gli otto tipi di ResourceTimeConstraint, uno scenario minimo ciascuno."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import ResourceTimeConstraint, Site
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = ResourceTimeConstraint.Type


def _constraint(env, type_, params):
    return ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=type_, params=params)


def _teach(env, day, slot, slots=1):
    a = make_activity(env["subject"], teachers=[env["teacher"]], slots=slots)
    place(env["schedule"], a, day=day, slot=slot)
    return a


def _codes(env):
    return [f.code for f in check_schedule(env["schedule"])]


def test_min_distribution():
    env = mini_school()
    _constraint(env, T.MIN_DISTRIBUTION, {"min_days": 2, "min_minutes_per_day": 120})
    _teach(env, day=0, slot=0, slots=2)   # un solo giorno qualificante
    _teach(env, day=1, slot=0)            # 60' < 120'
    assert _codes(env) == ["min_distribution"]


def test_max_hours_giornata_e_mattina():
    env = mini_school()
    _constraint(env, T.MAX_HOURS, {"day_minutes": 240, "morning_minutes": 120})
    for slot in range(5):                  # 5h nello stesso giorno, 4 di mattina
        _teach(env, day=0, slot=slot)
    assert sorted(_codes(env)) == ["max_hours_day", "max_hours_morning"]


def test_max_presence_span_con_buco():
    env = mini_school()
    _constraint(env, T.MAX_PRESENCE, {"days": 5, "max_minutes": 180})
    _teach(env, day=0, slot=0)
    _teach(env, day=0, slot=4)             # presenza = fasce 0..4 = 300' > 180'
    assert _codes(env) == ["max_presence"]


def test_max_presence_giorni():
    env = mini_school()
    _constraint(env, T.MAX_PRESENCE, {"days": 2, "max_minutes": 360})
    for day in range(3):
        _teach(env, day=day, slot=0)
    assert _codes(env) == ["max_presence_days"]


def test_arrival_departure():
    env = mini_school()
    _constraint(env, T.ARRIVAL_DEPARTURE, {"days": 5, "not_before_slot": 1})
    _teach(env, day=0, slot=0)             # inizia alla fascia 0: giorno non conforme
    assert _codes(env) == ["arrival_departure"]


def test_free_guaranteed():
    env = mini_school()
    _constraint(env, T.FREE_GUARANTEED, {"free_days": 2, "free_half_days": 0})
    for day in range(4):                   # lavora 4 giorni su 5: 1 libero < 2
        _teach(env, day=day, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["free_guaranteed"]
    assert findings[0].quantities["free_days"] == 1


def test_max_half_days_e_solo_mezza_giornata():
    env = mini_school()
    _constraint(env, T.MAX_HALF_DAYS,
                {"max_half_days": 1, "only_half_day_per_day": True})
    _teach(env, day=0, slot=0)             # mattina
    _teach(env, day=0, slot=5)             # pomeriggio: 2 mezze giornate, stesso giorno
    assert sorted(_codes(env)) == ["max_half_days", "only_half_day"]


def test_max_site_changes():
    env = mini_school()
    sede_a = Site.objects.create(name="Centrale")
    sede_b = Site.objects.create(name="Succursale")
    _constraint(env, T.MAX_SITE_CHANGES, {"per_day": 0})
    a = _teach(env, day=0, slot=0)
    b = _teach(env, day=0, slot=3)         # fascia libera sufficiente (default 1)
    a.site, b.site = sede_a, sede_b
    a.save(); b.save()
    assert _codes(env) == ["max_site_changes"]


def test_max_gap_per_mezza_giornata():
    env = mini_school()
    _constraint(env, T.MAX_GAP_HOURS, {"max_gap_minutes": 60})
    _teach(env, day=0, slot=0)
    _teach(env, day=0, slot=3)             # buco di 2 fasce in mattinata = 120'
    _teach(env, day=1, slot=3)
    _teach(env, day=1, slot=4)             # pausa pranzo fra le fasce 3 e 4: non è un buco
    assert _codes(env) == ["max_gap"]
