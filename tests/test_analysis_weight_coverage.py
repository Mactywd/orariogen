"""Peso didattico (per parte), copertura monte ore, completezza del registro."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.registry import REGISTRY, all_checkers
from domain.models import (
    ClassPart, ClassPartition, InstituteSettings, ResourceTimeConstraint,
    Service, SubjectConstraint,
)
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _institute(**caps):
    settings = InstituteSettings.load()
    for name, value in caps.items():
        setattr(settings, name, value)
    settings.save()


def test_peso_oltre_il_tetto_di_giornata():
    env = mini_school()
    _institute(max_weight_day=3)
    env["subject"].didactic_weight = 2
    env["subject"].save()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)  # 2×2 = 4 > 3
    place(env["schedule"], a, day=0, slot=0)
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["weight_day"]
    assert findings[0].quantities == {"day": 0, "weight": 4, "max_weight": 3}


def test_peso_per_parte_non_per_classe():
    """Il caso _REL/_ALT: due parti in parallelo non sommano i pesi."""
    env = mini_school()
    _institute(max_weight_day=2)
    partition = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=partition)
    alt = ClassPart.objects.create(name="1A_ALT", partition=partition)
    a = make_activity(env["subject"], parts=[rel], slots=2)   # peso 2 sulla parte
    b = make_activity(env["subject"], parts=[alt], slots=2)   # peso 2 sull'altra
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    # ogni parte riceve 120' ma il servizio (condiviso) ne ha accumulati 240:
    # si riallinea al monte ore per studente, che è 120'
    Service.objects.filter(study_plan=env["plan"], subject=env["subject"]) \
        .update(class_minutes=120)
    assert check_schedule(env["schedule"]) == []  # 2 ≤ 2 per ciascuna parte


def test_tetto_settimanale_di_classe_prevale():
    env = mini_school()
    _institute(max_weight_week=100)
    env["klass"].max_weekly_weight_per_student = 2
    env["klass"].save()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)  # peso 3 > 2
    place(env["schedule"], a, day=0, slot=0)
    assert [f.code for f in check_schedule(env["schedule"])] == ["weight_week"]


def test_copertura_monte_ore():
    env = mini_school()
    make_activity(env["subject"], classes=[env["klass"]])  # il servizio nasce a 60'
    service = Service.objects.get(study_plan=env["plan"], subject=env["subject"])
    service.class_minutes = 120                            # 60' contro 120'
    service.save()
    findings = check_schedule(env["schedule"])
    assert [f.code for f in findings] == ["coverage_mismatch"]
    assert findings[0].quantities == {"expected_minutes": 120, "actual_minutes": 60}


def test_copertura_quadrata_nessun_finding():
    env = mini_school()
    make_activity(env["subject"], classes=[env["klass"]], slots=2)
    assert check_schedule(env["schedule"]) == []


def test_registro_completo():
    """Ogni valore di enum ha un checker: nessun buco silenzioso nel verdetto."""
    all_checkers()  # forza la registrazione
    for value in ResourceTimeConstraint.Type.values:
        assert value in REGISTRY, f"ResourceTimeConstraint.Type.{value} senza checker"
    for value in SubjectConstraint.Type.values:
        assert value in REGISTRY, f"SubjectConstraint.Type.{value} senza checker"
    structural = {k for k in REGISTRY if isinstance(k, str) and k.startswith("structural:")}
    assert structural == {
        "structural:occupation", "structural:unavailability", "structural:grid",
        "structural:site_transition", "structural:didactic_weight",
        "structural:coverage",
    }
