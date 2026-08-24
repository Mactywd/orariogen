"""I tre vincoli orari che chiedono un minimo invece di imporre un tetto. Il
test che conta e' quello su FREE_GUARANTEED: il checker conta le mezze
giornate libere **solo sui giorni che hanno attivita'**, e un builder che le
contasse su tutti i giorni accetterebbe orari che il checker boccia.

⚠ I cinque test per seed di ogni famiglia (`test_famiglia` in
tests/test_solver_witness.py, parametrizzato su `sorted(DERIVERS) x [1..5]`)
li copre gia' la sola registrazione dei tre derivatori sotto: non li si
riscrive qui."""
import pytest

from domain.models import ResourceTimeConstraint
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school
from tests.test_solver_oracle import violazioni

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


def test_min_distribution_morde():
    """Quattro ore, distribuite su almeno tre giorni."""
    env = mini_school()
    for _ in range(4):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert len({day for (day, _s) in soluzione.placements.values()}) >= 3


def test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti():
    """La trappola, dritta. Griglia 5x6 con meta' giornata a 4; una sola
    attivita', quindi quattro giorni su cinque sono **completamente** vuoti.

    Il checker conta le mezze giornate libere solo sui giorni con attivita':
    con una sola attivita' ce n'e' esattamente **una** (l'altra meta' del
    giorno in cui si lavora). Un builder che sommasse su tutti i giorni ne
    conterebbe nove, e dichiarerebbe soddisfatto un vincolo che il checker
    boccia. Chiediamo tre mezze giornate libere: dev'essere INFEASIBLE."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_free_guaranteed_soddisfacibile_resta_soddisfacibile():
    """Il complemento del test sopra: con una sola mezza giornata richiesta la
    stessa istanza dev'essere fattibile, e pulita per il checker."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"free_guaranteed"}) == set()


def test_arrival_departure_morde():
    """Con un'unica attivita' il vincolo non e' garantito di mordere: CP-SAT
    e' libero di scegliere una qualunque soluzione ammissibile, e su un
    modello quasi vuoto puo' evitare lo slot proibito anche senza che nulla
    glielo imponga — verificato empiricamente (vedi report). Serve un
    argomento di **capienza**, come per FREE_GUARANTEED: griglia 5x6 (30
    celle), `not_before_slot=1` vieta la fascia 0 su **tutti** i 5 giorni
    (days=5, cioe' nessuna violazione ammessa), lasciando 25 celle libere
    per la classe. Ventisei attivita' da un'ora non ci stanno: dev'essere
    INFEASIBLE. È il complemento del test FREE_GUARANTEED sopra, sull'altra
    famiglia."""
    env = mini_school()
    for _ in range(26):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.ARRIVAL_DEPARTURE,
        params={"not_before_slot": 1, "days": 5})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_arrival_departure_soddisfacibile_resta_soddisfacibile():
    """Il complemento: la stessa restrizione (`not_before_slot=1`, `days=5`,
    slot 0 vietato su tutta la settimana), ma con 25 attivita' invece di 26 —
    esattamente la capienza residua. Dev'essere fattibile, e pulita per il
    checker: il vincolo morde davvero (nessuna cella nello slot 0 viene
    usata) senza per questo rendere l'istanza infattibile."""
    env = mini_school()
    for _ in range(25):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.ARRIVAL_DEPARTURE,
        params={"not_before_slot": 1, "days": 5})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"arrival_departure"}) == set()
