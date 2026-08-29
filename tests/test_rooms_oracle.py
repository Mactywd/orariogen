"""L'oracolo differenziale della ripartizione: assegna → scrivi → rileggi.

Il criterio e' **differenziale** e non «zero findings»: la premessa di ADR-018
e' che un orario gia' illegale resti uno stato ammesso."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Placement
from domain.solver.rooms import apply_rooms, solve_rooms
from tests.rooms_harness import costruisci_testimone_aule

pytestmark = pytest.mark.django_db


def _hard(schedule):
    return {f.key for f in check_schedule(schedule) if f.severity == Severity.HARD}


@pytest.mark.parametrize("seed", range(1, 11))
def test_l_oracolo_non_produce_finding_nuovi(seed):
    banco = costruisci_testimone_aule(seed)
    schedule = banco["schedule"]
    Placement.objects.filter(schedule=schedule).update(assigned_room=None)
    baseline = _hard(schedule)
    soluzione = solve_rooms(schedule, workers=1)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    apply_rooms(soluzione, schedule)
    assert _hard(schedule) - baseline == set()


def test_fermi_ripartizione_misurata():
    """⚠ Il Fermi misura il **costo**, mai la copertura: una firma di settimana
    sola, nessuna indisponibilita' d'aula, nessun vincolo di sede.

    🔑 E misura la cosa che ha chiuso D3: **la fase 1 conta le aule**, quindi
    la fase 2 non rinuncia piu'.

    Fino al 2026-08-29 questo test pretendeva **8 rinunce su 92**, ed era la
    misura giusta di un modello sbagliato: il piazzamento era cieco alle aule
    con piu' di una candidata (a candidata unica se le prende come token), e
    §6 dichiara fuori scope il ritorno al piazzamento — quindi la fase 1
    accatastava su una cella piu' richieste di quante aule esistessero, e la
    fase 2 non aveva altra risposta che rinunciare. Era scritto come «la
    conseguenza dichiarata di assegnare le aule *dopo*», e la parte falsa era
    proprio quella: assegnarle dopo non obbliga a **contarle** dopo. EDT le
    conta mentre piazza — la causale *«il gruppo di aule ha raggiunto il suo
    picco d'occupazione»* sta in `AffSco_UtilDiagnostic`, che e' la
    diagnostica del piazzamento. Vedi ADR-021.

    Il deficit misurato allora era esattamente il numero di rinunce: **8**,
    su 7 celle, tutte sullo stesso insieme `{LAB-FIS, LAB-INF}`. Ora
    `structural:room_pool` lo vieta prima, e le richieste servite sono 92 su
    92. Se un giorno tornasse una rinuncia qui, la notizia sarebbe che il
    piazzamento e' tornato cieco — non che la ripartizione si e' rotta."""
    from domain.solver.model import apply, solve
    from tests import fermi
    schedule = fermi.build()["schedule"]
    # serve un orario: la ripartizione lavora sui piazzamenti gia' scritti
    apply(solve(schedule, workers=1), schedule)
    soluzione = solve_rooms(schedule, workers=1)
    assert soluzione.status == "OPTIMAL"
    assert soluzione.stats["richieste"] == 92
    assert soluzione.unassigned == (), soluzione.stats
    assert soluzione.stats["assegnate"] == 92


@pytest.mark.parametrize("seed", range(1, 11))
def test_il_testimone_esiste_quindi_zero_rinunce(seed):
    """Il testimone e' un'assegnazione valida: l'ottimo e' zero rinunce. Senza
    questa pretesa una fase che rinuncia a tutto sarebbe «pulita» per qualunque
    checker, perche' un'attivita' senza aula non occupa niente."""
    banco = costruisci_testimone_aule(seed)
    Placement.objects.filter(schedule=banco["schedule"]).update(assigned_room=None)
    soluzione = solve_rooms(banco["schedule"], workers=1)
    assert soluzione.unassigned == ()
    assert soluzione.stats["minuti_senza_aula"] == 0
