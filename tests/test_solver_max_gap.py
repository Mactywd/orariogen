"""D.T.B.: budget settimanale di minuti di buco, non soglia per singolo buco."""
import pytest

from domain.models import ResourceTimeConstraint, ResourceUnavailability, Teacher
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = ResourceTimeConstraint.Type


def _solo_queste_fasce(teacher, ammesse):
    """Tutto rosso tranne le celle indicate: costringe la forma della giornata."""
    for giorno in range(5):
        for fascia in range(6):
            if (giorno, fascia) not in ammesse:
                ResourceUnavailability.objects.create(
                    resource=teacher, day=giorno, slot=fascia, level="hard")


def _dtb(teacher, minuti):
    return ResourceTimeConstraint.objects.create(
        resource=teacher, type=T.MAX_GAP_HOURS,
        params={"max_gap_minutes": minuti})


def _scena_due_buchi(env):
    """Due giornate identiche: fascia 0 fissa, fascia 1 vietata, fascia 2 da
    riempire. Ne escono per forza due buchi da 60 minuti, uno per giorno."""
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 2), (1, 0), (1, 2)})
    for giorno in (0, 1):
        fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
        place(env["schedule"], fissa, day=giorno, slot=0)
    return [make_activity(env["subject"], teachers=[docente]) for _ in range(2)]


def test_budget_sufficiente_e_fattibile():
    env = mini_school()
    _scena_due_buchi(env)
    _dtb(env["teacher"], 120)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_due_buchi_da_un_ora_sforano_un_budget_di_un_ora_e_mezza():
    """Il test che distingue budget da soglia. Con una soglia per singolo buco
    ciascuno dei due sarebbe legale (60 <= 90); come budget settimanale la
    somma e' 120 e sfora. E' il caso indicato dalla spec."""
    env = mini_school()
    _scena_due_buchi(env)
    _dtb(env["teacher"], 90)
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_senza_vincolo_la_stessa_scena_e_fattibile():
    env = mini_school()
    _scena_due_buchi(env)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_il_buco_non_si_conta_a_cavallo_del_pranzo():
    """Fascia 3 (mattina) e fascia 4 (pomeriggio) sono adiacenti nella griglia
    ma stanno in due mezze giornate: fra loro non c'e' nessun buco."""
    env = mini_school()
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 5)})
    fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
    place(env["schedule"], fissa, day=0, slot=0)
    make_activity(env["subject"], teachers=[docente])
    _dtb(docente, 0)
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    """Il D.T.B. e' gia' sforato dalle sole attivita' congelate, ma il docente
    non ha niente da piazzare: e' un fatto, non una decisione."""
    env = mini_school()
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 2)})
    for fascia in (0, 2):
        fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
        place(env["schedule"], fissa, day=0, slot=fascia)
    _dtb(docente, 0)
    altro = Teacher.objects.create(name="Neri Ugo", last_name="Neri", first_name="Ugo")
    make_activity(env["subject"], teachers=[altro])
    assert solve(env["schedule"]).status in ("OPTIMAL", "FEASIBLE")
