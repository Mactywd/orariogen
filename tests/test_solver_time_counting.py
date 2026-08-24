"""MAX_HOURS e MAX_HALF_DAYS: puro conteggio. E il primo test end-to-end di
ADR-018 su input sporco — una congelata che ha gia' sforato il tetto non deve
rendere il modello infattibile."""
import pytest

from domain.models import Activity, Placement, ResourceTimeConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place
from tests.solver_harness import run_family

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_max_hours_sul_banco(seed):
    run_family(T.MAX_HOURS, seed)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_max_half_days_sul_banco(seed):
    run_family(T.MAX_HALF_DAYS, seed)


def test_max_hours_morde():
    """Tre attivita' della stessa classe, tetto giornaliero a due ore: il
    solver deve distribuirle su piu' di un giorno."""
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_HOURS, params={"day_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    per_giorno = {}
    for (day, _slot) in soluzione.placements.values():
        per_giorno[day] = per_giorno.get(day, 0) + 1
    assert max(per_giorno.values()) <= 2


def test_adr018_una_congelata_gia_in_violazione_non_blocca_il_solver():
    """Il caso di ADR-018, end-to-end. Due attivita' congelate sono gia'
    piazzate lo stesso giorno e sforano da sole il tetto di un'ora. Una terza,
    libera, deve comunque poter essere piazzata: il tetto residuo e' zero per
    quel giorno, non negativo, quindi il modello resta fattibile e la libera
    va altrove."""
    env = mini_school()
    congelate = [
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for _ in range(2)
    ]
    for i, act in enumerate(congelate):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=i)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_HOURS, params={"day_minutes": 60})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id][0] != 0   # non il giorno gia' pieno


def test_adr018_dtb_gia_sforato_dalle_congelate_non_blocca_il_solver():
    """Lo stesso principio di ADR-018, ma sul D.T.B. (MaxGapBuilder), che il
    brief non copre esplicitamente: due attivita' congelate dello stesso
    docente lasciano un buco di 60' fra loro (fasce 0 e 2 ammesse, fascia 1
    vietata da un'indisponibilita' hard), e il tetto dichiarato e' 0 — gia'
    sforato dal solo passato. Una terza attivita' libera dello stesso
    docente, su un altro giorno, non deve rendere il modello infattibile: il
    guardiano deve riconoscere il debito gia' contratto e concedere un tetto
    effettivo pari ad esso (clamp), non spegnere il vincolo — la review Task
    6 (Important 2) ha corretto lo spegnimento in un clamp, perche' il D.T.B.
    resta un budget su tutta la settimana, non solo sul giorno gia' sforato."""
    from domain.models import ResourceUnavailability

    env = mini_school()
    docente = env["teacher"]
    # Restringe solo il giorno 0, cosi' il buco e' forzato li' e la libera
    # ha comunque altrove (giorni 1-4, tutti aperti) dove andare.
    for fascia in (1, 3, 4, 5):
        ResourceUnavailability.objects.create(
            resource=docente, day=0, slot=fascia, level="hard")
    congelate = [
        make_activity(env["subject"], teachers=[docente],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for _ in range(2)
    ]
    for slot, act in zip((0, 2), congelate):
        place(env["schedule"], act, day=0, slot=slot)
    make_activity(env["subject"], teachers=[docente])
    ResourceTimeConstraint.objects.create(
        resource=docente, type=T.MAX_GAP_HOURS, params={"max_gap_minutes": 0})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats


def test_adr018_only_half_day_gia_sforato_dalle_congelate_non_blocca_il_solver():
    """Il ramo `only_half_day_per_day` di MaxHalfDaysBuilder non era provato
    in nessuna direzione (review Task 6, Important 1: l'affermazione del
    brief che fosse coperto da test_max_hours_morde era falsa, quel test
    riguarda MAX_HOURS). Due attivita' congelate dello stesso docente, una in
    mattinata (fascia 0) e una in pomeriggio (fascia 4) dello stesso giorno,
    forzano entrambe le half_active derivate a 1: AddAtMostOne([1, 1]) senza
    guardia sarebbe insoddisfacibile, colpa del passato. Una terza attivita'
    libera dello stesso docente deve poter comunque essere piazzata."""
    env = mini_school()
    docente = env["teacher"]
    mattina = make_activity(env["subject"], teachers=[docente],
                            immobility=Activity.Immobility.LOCKED_IN_PLACE)
    pomeriggio = make_activity(env["subject"], teachers=[docente],
                               immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], mattina, day=0, slot=0)
    place(env["schedule"], pomeriggio, day=0, slot=4)
    make_activity(env["subject"], teachers=[docente])
    ResourceTimeConstraint.objects.create(
        resource=docente, type=T.MAX_HALF_DAYS,
        params={"only_half_day_per_day": True})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
