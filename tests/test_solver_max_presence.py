"""La presenza non e' il lavoro: include i buchi. E si misura sulla giornata
intera, non per mezza giornata — a differenza del D.T.B.

⚠ Niente `test_max_presence_sul_banco` qui (Ruling 16): `tests/solver_harness.py`
registra il derivatore `_derive_max_presence` sotto `T.MAX_PRESENCE`, e
`tests/test_solver_witness.py::test_famiglia` gia' parametrizza su
`sorted(DERIVERS) × [1..5]` — i cinque seed della famiglia esistono in
automatico appena il derivatore e' registrato. Scriverli anche qui sarebbe un
duplicato esatto, come gia' per i tre derivatori del Task 7."""
import pytest

from domain.models import Activity, Placement, ResourceTimeConstraint
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


def test_la_presenza_include_i_buchi_e_attraversa_il_pranzo():
    """Due attivita' della stessa classe, presenza massima due ore. Su una
    griglia 5x6 con meta' giornata a 4, il solver non puo' metterle alle fasce
    0 e 5 (presenza sei ore) ne' alle fasce 3 e 4 (presenza due ore ma **a
    cavallo del pranzo**, che per la presenza non conta come separazione).

    Se il builder usasse la mezza giornata come span, 3 e 4 risulterebbero due
    presenze da un'ora ciascuna e passerebbero: e' il modo esatto in cui questo
    vincolo si confonde con il D.T.B."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    per_giorno = {}
    for (day, slot) in soluzione.placements.values():
        per_giorno.setdefault(day, []).append(slot)
    for _day, fasce in per_giorno.items():
        assert (max(fasce) - min(fasce) + 1) * 60 <= 120


def test_adr018_presenza_gia_sforata_dalle_congelate_non_blocca():
    """Due congelate alle fasce 0 e 5 dello stesso giorno: presenza sei ore,
    tetto due. Con le fasce estreme della griglia il clamp e il vecchio
    salto (`continue`) coincidono — 360' e' gia' il massimo raggiungibile
    sulla griglia, quindi non c'e' modo per una libera di peggiorare quella
    giornata comunque venga trattato il vincolo. Questo test da solo non
    distingue i due comportamenti: vedi
    `test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata` qui
    sotto per la controprova che morde. Un'attivita' libera resta comunque
    piazzabile altrove."""
    env = mini_school()
    for i, slot in enumerate((0, 5)):
        act = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]],
                            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=slot)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert libera.id in soluzione.placements


def test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata():
    """La controprova che distingue clamp da salto (correzione 1 del brief,
    Ruling 23). Tre congelate alle fasce 0, 1, 2 dello stesso giorno: presenza
    gia' 180', tetto dichiarato 120'. Le congelate hanno gia' sforato — per
    ADR-018 il vincolo non puo' bloccare il solver per colpa del passato — ma
    non deve nemmeno **sparire**: una libera dello stesso giorno non puo'
    finire oltre la fascia 2, perche' allargherebbe la presenza da 180' a un
    valore maggiore, e il finding porta `minutes=presence` nelle sue
    `quantities` (`Finding.key`) — una presenza peggiorata e' una violazione
    **nuova** per l'oracolo differenziale, non la stessa di prima.

    Col `continue` del piano (salta il vincolo del giorno) questo test e'
    rosso: la libera puo' andare alla fascia 5 e portare la presenza a 360'.
    Col clamp (`cap_effettivo = max(cap, presenza_congelate) = 180`) resta
    verde. Verificato manualmente reintroducendo il `continue` — vedi il
    report del task per l'output rosso incollato."""
    env = mini_school()
    for slot in (0, 1, 2):
        act = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]],
                            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=slot)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 120})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    giorno, fascia = soluzione.placements[libera.id]
    if giorno == 0:
        assert fascia <= 2


def test_max_presence_giorni_morde():
    """Il ramo `days`. Un'asserzione «al piu' N giorni» non morde da sola
    contro questa fixture: CP-SAT, senza alcun vincolo, tende gia' a
    compattare le attivita' sui primi giorni per costruzione della ricerca —
    un builder con il ramo `days` disabilitato passerebbe comunque questo
    test (verificato disabilitandolo davvero). Serve un argomento di
    capienza: il docente e' indisponibile ovunque tranne una fascia per
    ciascuno di tre giorni, quindi al piu' un'attivita' al giorno e tre
    attivita' **richiedono** tre giorni distinti. Con un tetto di due
    giorni il modello deve risultare INFEASIBLE — l'unico modo per
    accettare una soluzione sarebbe ignorare il ramo `days`."""
    from domain.models import ResourceUnavailability

    env = mini_school()
    docente = env["teacher"]
    for day in range(3):
        for slot in range(1, 6):
            ResourceUnavailability.objects.create(
                resource=docente, day=day, slot=slot, level="hard")
    for day in (3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=docente, day=day, slot=slot, level="hard")
    for _ in range(3):
        make_activity(env["subject"], teachers=[docente], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"days": 2})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    """Rete di sicurezza di ResourceBuilder: entrambi i tetti sono gia'
    sforati dalle sole congelate, ma la classe non ha nulla da piazzare —
    e' un fatto, non una decisione, e il solver non deve nemmeno accorgersi
    del vincolo."""
    env = mini_school()
    congelate = [
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for _ in range(2)
    ]
    for day, act in enumerate(congelate):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=day, start_slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE,
        params={"max_minutes": 0, "days": 0})
    from domain.models import Teacher
    altro = Teacher.objects.create(name="Neri Ugo", last_name="Neri", first_name="Ugo")
    make_activity(env["subject"], teachers=[altro])
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
