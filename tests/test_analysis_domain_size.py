"""S.P. / Nr G.: il dominio residuo, ricalcolato mai memorizzato (ADR-007)."""
import pytest

from domain.analysis.domain_size import residual_domain
from domain.analysis.state import ScheduleState
from domain.models import ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_griglia_vuota_dominio_pieno():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 30  # 5 giorni × 6 fasce
    assert size.days == 5


def test_il_blocco_riduce_le_partenze():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=3)
    state = ScheduleState.build(env["schedule"])
    assert residual_domain(a, state).placements == 20  # 4 partenze × 5 giorni


def test_indisponibilita_esclude_il_giorno():
    env = mini_school()
    for slot in range(6):
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=0, slot=slot, level="hard")
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 24 and size.days == 4


def test_sospendere_un_vicino_alza_il_dominio():
    """Il comportamento osservato in EDT: i valori salgono sospendendo
    un'attività e si riabbassano richiudendo il buco."""
    env = mini_school()
    occupante = make_activity(env["subject"], teachers=[env["teacher"]])
    libera = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], occupante, day=0, slot=0)
    state = ScheduleState.build(env["schedule"])
    con_vicino = residual_domain(libera, state).placements
    state.unplace(occupante.id)
    senza_vicino = residual_domain(libera, state).placements
    state.place(occupante, 0, 0)
    di_nuovo = residual_domain(libera, state).placements
    assert senza_vicino == con_vicino + 1
    assert di_nuovo == con_vicino


def test_attivita_gia_piazzata_si_sospende_e_ripristina():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=2, slot=3)
    state = ScheduleState.build(env["schedule"])
    size = residual_domain(a, state)
    assert size.placements == 30       # da sola: tutto libero
    assert state.placed[a.id].day == 2 # ripristinata dov'era


def test_violazioni_preesistenti_non_squalificano():
    """Due attività già in conflitto: il dominio di una terza non ne risente."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)   # conflitto preesistente
    altra = make_activity(env["subject"], classes=[env["klass"]])
    state = ScheduleState.build(env["schedule"])
    assert residual_domain(altra, state).placements == 30
