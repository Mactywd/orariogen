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


def test_la_presenza_include_i_buchi():
    """Due attivita' della stessa classe, presenza massima due ore: il solver
    non puo' metterle alle fasce 0 e 5, perche' la presenza include i buchi e
    varrebbe sei ore.

    ⚠ Il nome e la docstring che questo test aveva nel piano promettevano di
    piu' di quanto mantenessero (Minor 1 della review Task 8): dicevano che il
    solver non puo' nemmeno usare le fasce 3 e 4 «a cavallo del pranzo». E'
    **falso** — con `morning_end_slot = 4` le fasce 3 e 4 danno `4 - 3 + 1 = 2`
    fasce, cioe' 120', che un tetto di 120' ammette, e il checker e'
    d'accordo. Cio' che questo test cattura sotto mutazione e' lo `span` in
    generale (l'asserzione che salta e' quella sulle fasce 0 e 5), non il
    pranzo. La dimensione del pranzo e' esercitata dal test qui sotto."""
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


def test_la_presenza_non_si_spezza_a_cavallo_del_pranzo():
    """La dimensione che il test sopra prometteva e non esercitava (Minor 1
    della review Task 8). Due attivita' costrette alle fasce **3 e 4** — le
    due che stanno a cavallo del confine mattina/pomeriggio — con un tetto di
    **60'**.

    `MaxPresenceChecker._presence_minutes` misura `ultima - prima + 1` sulla
    giornata intera e non passa mai da `_halves`: vede una sola presenza di
    120' e boccia. Un builder che usasse la mezza giornata come `span`
    vedrebbe due presenze da 60' ciascuna, entrambe sotto il tetto, e
    accetterebbe — che e' il modo esatto in cui MAX_PRESENCE si confonde col
    D.T.B., il quale invece a cavallo del pranzo non conta mai nulla.

    Attesa: INFEASIBLE. Col builder mutato a `v.halves()` diventa OPTIMAL."""
    from domain.models import ResourceUnavailability

    env = mini_school()
    docente = env["teacher"]
    for day in range(5):
        for slot in range(6):
            if day == 0 and slot in (3, 4):
                continue
            ResourceUnavailability.objects.create(
                resource=docente, day=day, slot=slot, level="hard")
    for _ in range(2):
        make_activity(env["subject"], teachers=[docente], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 60})
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_la_presenza_a_cavallo_del_pranzo_e_ammessa_se_ci_sta_nel_tetto():
    """Caso di controllo del test sopra, perche' quell'INFEASIBLE non sia
    scambiato per «le fasce 3 e 4 sono vietate in quanto tali»: la stessa
    istanza con una sola attivita' (presenza 60') e' risolvibile. Cio' che
    boccia e' la misura della presenza, non la posizione."""
    from domain.models import ResourceUnavailability

    env = mini_school()
    docente = env["teacher"]
    for day in range(5):
        for slot in range(6):
            if day == 0 and slot in (3, 4):
                continue
            ResourceUnavailability.objects.create(
                resource=docente, day=day, slot=slot, level="hard")
    make_activity(env["subject"], teachers=[docente], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"max_minutes": 60})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats


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
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_adr018_giorni_gia_consumati_dalle_congelate_non_bloccano():
    """Il clamp `max(0, max_days - consumo)` del ramo `days` — portante ma
    scoperto da tutti i test consegnati col Task 8 (Minor 2 della review).
    Nessuno di quelli metteva insieme attivita' congelate **e** una riga con
    `days`, quindi il caso `consumo > max_days` non veniva mai costruito: la
    mutazione `max_days - consumo` (senza il clamp a zero) lasciava la suite
    intera verde.

    L'istanza: tre congelate su tre giorni distinti, tetto **due** giorni.
    Il passato ha gia' consumato tre giorni su due, quindi il residuo grezzo
    e' `2 - 3 = -1` e senza clamp il vincolo diventa `sum(giorni liberi) <=
    -1`, insoddisfacibile: il modello sarebbe INFEASIBLE **per colpa del
    passato**, cio' che ADR-018 vieta. Col clamp il residuo e' 0 — nessun
    giorno *nuovo* puo' essere aperto — e l'attivita' libera si piazza in uno
    dei tre giorni gia' consumati."""
    env = mini_school()
    for day in range(3):
        act = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]],
                            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=day, start_slot=0)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_PRESENCE, params={"days": 2})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    giorno, _fascia = soluzione.placements[libera.id]
    assert giorno in (0, 1, 2)


def test_il_vincolo_non_si_posta_se_nulla_e_libero():
    """⚠ Questo test **documenta**, non verifica (Minor 3 della review Task
    8): passa anche disattivando la rete di sicurezza che dice di provare.
    Il motivo e' che il clamp lo rende innocuo comunque — `cap_effettivo` si
    ferma alla presenza delle congelate e il ramo `days` azzera solo giornate
    che nessuna libera puo' toccare, quindi il modello resta risolvibile sia
    postando il vincolo sia saltandolo. E' tenuto perche' esibisce la
    situazione («entrambi i tetti gia' sforati dalle sole congelate, e niente
    da piazzare per quella classe») ed e' un caso limite che deve continuare a
    risolversi; la rete di sicurezza di `ResourceBuilder` e' invece verificata
    davvero dai test che la review del Task 6 ha imposto."""
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
