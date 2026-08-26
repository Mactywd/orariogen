"""La fase 5: il sottoinsieme infattibile. Meta' dei casi sono negativi, e
contano di piu' — il difetto temuto e' il falso positivo, che manda l'utente a
smontare vincoli sani."""
import pytest

from domain.analysis.hall import STATEMENT_SINGOLA, analyze_hall
from domain.models import Activity, ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _blocca(resource, giorni=(), celle=()):
    """Indisponibilita' hard: giornate intere e/o singole (giorno, fascia)."""
    for day in giorni:
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=resource, day=day, slot=slot, level="hard")
    for day, slot in celle:
        ResourceUnavailability.objects.create(
            resource=resource, day=day, slot=slot, level="hard")


def test_sette_lezioni_in_sei_fasce():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))       # resta il solo giorno 0
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 1
    f = findings[0]
    assert f.n_activities == 7
    assert f.required_minutes == 7 * 60
    assert f.placeable_minutes == 6 * 60
    assert env["teacher"].name in f.resource_labels


def test_sette_lezioni_in_sette_fasce_non_e_un_problema():
    env = mini_school()
    _blocca(env["teacher"], giorni=(2, 3, 4),
            celle=[(1, s) for s in range(1, 6)])       # giorno 0 intero + (1,0)
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []


def test_l_impronta_e_fatta_di_fasce_occupate_non_di_avvii():
    # Due blocchi da 3 ore in un giorno da 6 fasce: entrano (0-2 e 3-5).
    # Contando gli avvii invece delle fasce occupate l'impronta sarebbe di 4
    # celle e uscirebbe un falso positivo.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=3)

    assert analyze_hall(env["schedule"]) == []


def test_l_immobile_consuma_capienza():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(3, 6)])       # restano (0,0) (0,1) (0,2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []         # 3 attivita', 3 fasce

    bloccata = make_activity(
        env["subject"], teachers=[env["teacher"]], slots=1,
        immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], bloccata, day=0, slot=0)

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 3               # l'immobile non e' colpevole
    assert findings[0].placeable_minutes == 2 * 60


def test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio():
    # Trappola §4.1: se si spiazza solo l'attivita' in prova, il blocco B
    # copre entrambe le fasce ammesse ad A, il dominio di A risulta vuoto e
    # esce un falso positivo. Spiazzando tutte le candidate, entra tutto.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(4, 6)])       # docente: (0,0)..(0,3)
    _blocca(env["klass"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(2, 6)])       # classe:  (0,0) (0,1)

    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=1)
    b = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    place(env["schedule"], b, day=0, slot=0)           # copre (0,0) e (0,1)
    place(env["schedule"], a, day=0, slot=2)           # fuori dalla finestra di classe

    assert analyze_hall(env["schedule"]) == []
