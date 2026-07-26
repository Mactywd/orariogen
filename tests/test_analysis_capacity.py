"""Le due diagnosi osservate in EDT (diagnostica.md), riprodotte come fixture."""
import pytest

from domain.analysis.capacity import analyze_capacity
from domain.models import ResourceTimeConstraint, SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _lettere_10h(env):
    """Diagnosi A: sei attività di LETTERE (2+2+2+2+1+1 = 10h) su una classe,
    materia incompatibile con sé stessa nella giornata, 5 giorni."""
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    return SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)


def test_diagnosi_a_lettere():
    env = mini_school()
    _lettere_10h(env)
    findings = analyze_capacity()
    assert len(findings) == 1
    f = findings[0]
    assert f.statement == ("I vincoli della classe non permettono il "
                           "piazzamento di tutte le attività.")
    assert f.n_activities == 6
    assert f.required_minutes == 600
    assert f.placeable_minutes == 540      # le 5 attività più lunghe: 9h00
    assert any("incompatib" in c.lower() for c in f.culprits)
    assert "Rendere i vincoli delle materie meno vincolanti" in f.remedies
    assert "Diminuire la durata delle attività" in f.remedies


def test_diagnosi_b_incrociata():
    """Diagnosi B: 4 attività di 6h, stessa incompatibilità, più le due
    giornate libere del docente: innocui separatamente, fatali insieme."""
    env = mini_school()
    for slots in (2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=ResourceTimeConstraint.Type.FREE_GUARANTEED,
        params={"free_days": 2, "free_half_days": 0})
    findings = analyze_capacity()
    assert len(findings) == 1
    f = findings[0]
    assert f.statement == ("I vincoli incrociati della classe e del docente "
                           "non permettono il piazzamento di tutte le attività.")
    assert f.required_minutes == 360
    assert f.placeable_minutes == 300      # 3 giorni × 1 attività: 2+2+1
    assert f.teacher_label == "Rossi Anna"
    assert "Diminuire i giorni e 1/2 giornate libere" in f.remedies
    assert len(f.culprits) >= 2            # entrambe le famiglie mostrate


def test_ciascun_vincolo_da_solo_e_innocuo():
    """Il controllo negativo della diagnosi B: senza l'altro vincolo, nessun
    finding — il verdetto è esatto, mai un falso allarme."""
    env = mini_school()
    for slots in (2, 2, 1, 1):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    assert analyze_capacity() == []        # 5 giorni × 1 attività ≥ 4 attività


def test_dieci_ore_senza_vincoli_entrano():
    env = mini_school()
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], classes=[env["klass"]], slots=slots)
    assert analyze_capacity() == []
