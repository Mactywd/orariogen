"""La fase 1 conta le aule (ADR-021).

Non le **assegna** — quella resta la seconda fase, com'e' in EDT. Conta: tre
attivita' che scelgono ognuna fra le stesse due aule non possono stare nella
stessa fascia, e il piazzamento deve saperlo *prima*, perche' §6 della spec
dell'assegnazione dichiara fuori scope il ritorno indietro.

⚠ Il vincolo e' **sano per costruzione**: vieta solo configurazioni che
nessuna assegnazione d'aula potrebbe servire (principio dei cassetti). Non
toglie mai un orario che la fase 2 saprebbe completare, quindi non puo'
introdurre scarti nuovi — puo' solo spostarli da «rinuncia d'aula» a
«collocazione diversa»."""
import pytest

from domain import weeks
from domain.analysis.checkers.room_pool import RoomPoolChecker
from domain.analysis.state import ScheduleState
from domain.models import Activity, Placement, Resource, ResourceUnavailability, Room
from domain.solver.model import solve
from tests.analysis_helpers import FULL, make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _aula(nome, simultanee=1):
    return Room.objects.create(name=nome, simultaneous_capacity=simultanee)


def _celle(soluzione, attivita):
    return [soluzione.placements[a.id] for a in attivita]


def _deficit(schedule):
    state = ScheduleState.build(schedule)
    return sum(f.quantities["load"] - f.quantities["capacity"]
               for f in RoomPoolChecker().check(state))


def test_tre_richieste_su_due_aule_non_condividono_la_fascia():
    env = mini_school()
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    atts = [make_activity(env["subject"], rooms=[fis, inf]) for _ in range(3)]
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    celle = _celle(soluzione, atts)
    assert max(celle.count(c) for c in celle) <= 2
    assert _deficit(env["schedule"]) == 0


def test_il_deficit_di_hall_e_vietato_anche_sotto_l_unione():
    """La forma del Fermi: sull'unione la capienza basta (3 aule, 4 richieste
    no — 3 aule, 3 richieste strette + 1 larga). Il vincolo deve mordere sul
    **sottoinsieme**, che e' cio' che un tetto sull'unione non vedrebbe."""
    env = mini_school(days=1, slots=2)
    fis, inf, sci = _aula("LAB-FIS"), _aula("LAB-INF"), _aula("LAB-SCI")
    stretti = [make_activity(env["subject"], rooms=[fis, inf]) for _ in range(3)]
    largo = make_activity(env["subject"], rooms=[inf, sci])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    celle = _celle(soluzione, stretti)
    assert max(celle.count(c) for c in celle) <= 2
    assert _deficit(env["schedule"]) == 0
    assert largo.id not in soluzione.unplaced


def test_senza_spazio_l_attivita_e_scartata_non_infattibile():
    """Cinque richieste su due aule e una sola fascia: lo scarto e' la
    risposta, come per ogni altro vincolo dal pezzo 3 in poi."""
    env = mini_school(days=1, slots=1)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(5):
        make_activity(env["subject"], rooms=[fis, inf])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert len(soluzione.unplaced) == 3
    assert _deficit(env["schedule"]) == 0


def test_pretendere_il_piazzamento_e_infattibile():
    env = mini_school(days=1, slots=1)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(3):
        make_activity(env["subject"], rooms=[fis, inf])
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_la_capienza_simultanea_conta_i_posti_non_le_aule():
    env = mini_school(days=1, slots=1)
    palestra, campo = _aula("PALESTRA", simultanee=2), _aula("CAMPO")
    for _ in range(3):
        make_activity(env["subject"], rooms=[palestra, campo])
    soluzione = solve(env["schedule"])
    assert soluzione.unplaced == ()      # 2 + 1 posti per 3 richieste


def test_l_aula_indisponibile_non_offre_posti():
    env = mini_school(days=1, slots=2)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    ResourceUnavailability.objects.create(
        resource=Resource.objects.get(pk=inf.pk), day=0, slot=0, level="hard")
    atts = [make_activity(env["subject"], rooms=[fis, inf]) for _ in range(3)]
    soluzione = solve(env["schedule"])
    celle = _celle(soluzione, atts)
    assert celle.count((0, 0)) <= 1      # nella fascia 0 c'e' solo LAB-FIS
    assert _deficit(env["schedule"]) == 0


def test_maschere_disgiunte_non_competono_per_le_aule():
    env = mini_school(days=1, slots=1)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    prima = weeks.single_week(0) | weeks.single_week(1)
    dopo = weeks.single_week(2) | weeks.single_week(3)
    for mask in (prima, prima, dopo, dopo):
        make_activity(env["subject"], rooms=[fis, inf], mask=mask)
    soluzione = solve(env["schedule"])
    assert soluzione.unplaced == ()      # due per semestre, due aule


def test_il_blocco_lungo_compete_su_tutte_le_sue_fasce():
    env = mini_school(days=1, slots=3)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    lungo = make_activity(env["subject"], rooms=[fis, inf], slots=3)
    brevi = [make_activity(env["subject"], rooms=[fis, inf]) for _ in range(3)]
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert _deficit(env["schedule"]) == 0


def test_le_congelate_gia_in_violazione_non_rendono_infattibile():
    """ADR-018: il tetto e' la capienza **residua**, clampata a zero. Tre
    congelate su due aule sono un orario illegale, e il solver deve continuare
    a lavorare invece di rispondere INFEASIBLE per colpa del passato."""
    env = mini_school(days=1, slots=1)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(3):
        a = make_activity(env["subject"], rooms=[fis, inf],
                          immobility=Activity.Immobility.FIXED)
        place(env["schedule"], a, 0, 0)
    libera = make_activity(env["subject"], rooms=[fis, inf])
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert libera.id in soluzione.unplaced     # residuo zero: non c'e' posto


def test_a_candidata_unica_il_vincolo_resta_quello_dell_occupazione():
    """Con una sola candidata l'aula e' gia' una chiave di occupazione, e
    `structural:occupation` la conta. Questa famiglia non deve aggiungere
    niente: il comportamento e' quello di prima, e il modello non cresce."""
    env = mini_school(days=1, slots=2)
    fis = _aula("LAB-FIS")
    atts = [make_activity(env["subject"], rooms=[fis]) for _ in range(2)]
    soluzione = solve(env["schedule"])
    celle = _celle(soluzione, atts)
    assert celle[0] != celle[1]
