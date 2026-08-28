"""Il perimetro: **restringe ciò su cui si agisce, mai ciò che si conta**.

È la proprietà su cui questo pezzo poteva sbagliare in silenzio. Filtrare lo
stato invece delle candidate darebbe un'occupazione più bassa del vero, e il
motore piazzerebbe sopra a lezioni che esistono — un difetto che nessun test di
«l'estrazione restringe» coglierebbe, perché restringere lo farebbe comunque."""
import pytest

from domain import extraction as ex
from domain.analysis.blame import rank_constraints
from domain.analysis.domain_size import free_candidates
from domain.analysis.hall import analyze_hall
from domain.analysis.state import ScheduleState
from domain.models import Activity, Placement, ResourceUnavailability, Room
from domain.solver.rooms import RoomContext, solve_rooms
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_fuori_perimetro_resta_piazzata_e_continua_a_occupare():
    """🔑 La metà che conta. La non estratta non è candidata **e** non viene
    spiazzata: `free_candidates` spiazza tutte le candidate (§4.1), quindi se
    l'estrazione le togliesse per esclusione dallo stato l'occupazione
    sparirebbe con loro."""
    env = mini_school(days=1, slots=2)
    fuori = make_activity(env["subject"], classes=[env["klass"]])
    dentro = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], fuori, 0, 0)
    place(env["schedule"], dentro, 0, 1)

    state = ScheduleState.build(env["schedule"])
    liberi = free_candidates(state, selected={dentro.pk})

    assert [a.pk for a in liberi] == [dentro.pk]
    assert fuori.pk in state.placed          # non spiazzata
    assert state.occupancy[(env["klass"].pk, 0, 0)] == [fuori.pk]


def test_fuori_perimetro_e_mai_piazzata_non_e_candidata():
    """⚠ Diversa da una congelata: una FIXED mai piazzata **resta** candidata,
    perché non c'è niente a cui congelarla. Una fuori estrazione no, e la
    ragione è d'altra natura — non è il lavoro che si è chiesto di fare."""
    env = mini_school(days=1, slots=2)
    fuori = make_activity(env["subject"], classes=[env["klass"]],
                          immobility=Activity.Immobility.FIXED)
    dentro = make_activity(env["subject"], classes=[env["klass"]])

    state = ScheduleState.build(env["schedule"])
    assert [a.pk for a in free_candidates(state)] == sorted([fuori.pk, dentro.pk])

    state = ScheduleState.build(env["schedule"])
    assert [a.pk for a in free_candidates(state, selected={dentro.pk})] == [dentro.pk]


def test_la_classifica_ignora_le_altre_ma_ne_subisce_l_occupazione():
    """Due metà nello stesso test, perché è la loro combinazione a essere la
    proprietà: la classifica esamina **una** attività, e quella attività trova
    la cella dell'altra occupata."""
    env = mini_school(days=1, slots=2)
    fuori = make_activity(env["subject"], classes=[env["klass"]],
                          teachers=[env["teacher"]])
    dentro = make_activity(env["subject"], classes=[env["klass"]],
                           teachers=[env["teacher"]])
    place(env["schedule"], fuori, 0, 0)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=1,
        level=ResourceUnavailability.Level.HARD)

    report = rank_constraints(env["schedule"], selected={dentro.pk})

    assert report.considered == 1
    assert report.unplaceable == (dentro.pk,)
    # La fascia 0 la chiude l'occupazione della non estratta, la 1
    # l'indisponibilità: due causali, e nessuna delle due è «non c'è niente».
    assert {r.code for r in report.rows} == {"resource_occupied", "unavailability"}


def test_la_fase_5_guarda_solo_il_perimetro():
    env = mini_school(days=1, slots=2)
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    b = make_activity(env["subject"], classes=[env["klass"]], slots=2)

    intero = analyze_hall(env["schedule"])
    ristretto = analyze_hall(env["schedule"], selected={a.pk})

    assert intero, "senza perimetro le due attività non entrano nella giornata"
    assert ristretto == [], "da sola, una ci sta"
    assert b.pk in {aid for f in intero for aid in f.activities}


def test_le_aule_fuori_perimetro_si_tengono_e_consumano_la_capienza():
    """La seconda fase con un perimetro: `held` invece di `requests`. È la
    stessa forma dell'immobile che tiene la sua aula — non è una decisione, ma
    la capienza la occupa lo stesso."""
    env = mini_school(days=1, slots=1)
    lab = Room.objects.create(name="LAB")
    fuori = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    dentro = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], fuori, 0, 0, room=lab)
    place(env["schedule"], dentro, 0, 0)

    from domain.models import Extraction
    estrazione = Extraction.objects.create(name="solo-dentro")
    estrazione.activities.add(dentro)

    ctx = RoomContext.build(env["schedule"], extraction=estrazione)
    assert set(ctx.requests) == {dentro.pk}
    assert ctx.held == {fuori.pk: lab.pk}

    soluzione = solve_rooms(env["schedule"], extraction=estrazione, workers=1)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    # L'unica aula è già occupata da chi sta fuori: la rinuncia è il verdetto
    # corretto, e sarebbe stata un'assegnazione illegale senza il carico.
    assert soluzione.unassigned == (dentro.pk,)


def test_apply_rooms_non_tocca_chi_sta_fuori():
    """⚠ Il primo test scritto per questa proprietà **non poteva fallire**:
    chi sta fuori teneva la sua aula anche senza perimetro, perché nessuno
    gliela contendeva. Qui il perimetro è l'unica cosa che la salva —
    `LAB` è diventata indisponibile dopo l'assegnazione a mano, quindi come
    *richiesta* non avrebbe candidate, rinuncerebbe, e `apply_rooms`
    **cancella** l'aula di chi rinuncia. Come `held`, non è una decisione e
    resta dov'è."""
    env = mini_school(days=1, slots=1)
    lab = Room.objects.create(name="LAB")
    fuori = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    dentro = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], fuori, 0, 0, room=lab)
    place(env["schedule"], dentro, 0, 0)
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    from domain.models import Extraction
    from domain.solver.rooms import apply_rooms
    estrazione = Extraction.objects.create(name="solo-dentro")
    estrazione.activities.add(dentro)

    apply_rooms(solve_rooms(env["schedule"], extraction=estrazione, workers=1),
                env["schedule"])
    assert Placement.objects.get(activity=fuori).assigned_room_id == lab.pk

    # E la prova che il perimetro è ciò che la salva: senza, `fuori` è una
    # richiesta senza candidate, rinuncia, e l'aula sparisce.
    apply_rooms(solve_rooms(env["schedule"], workers=1), env["schedule"])
    assert Placement.objects.get(activity=fuori).assigned_room_id is None


def test_fermi_una_classe_e_il_perimetro_che_serve_davvero():
    """La misura, e il caso d'uso che il pezzo esiste per servire: *«ripiazza
    solo la 1A»*.

    ⚠ **E la misura ha smentito la previsione, che era di un fattore dieci.**
    Un undicesimo delle attività (26 su 284) costa il **62%** del tempo, non il
    9%: `0,263s` contro `0,422s`. La decomposizione dice perché — `0,25s` di
    `ScheduleState.build`, che il perimetro non tocca perché lo stato si
    costruisce sempre intero, più `~0,6ms` per attività esaminata. Il perimetro
    riduce del 90% la parte **variabile** e del 38% il totale.

    🔑 Il che vale più del numero: sul Fermi la classifica è **dominata dalla
    costruzione dello stato**, non dal conteggio delle attività, ed è la
    conferma dal verso opposto che «restringe l'azione, mai il conteggio» non è
    solo una regola di correttezza — è anche il modello di costo.

    ⚠ Come sempre sul Fermi si misura il **costo**, mai la copertura: il
    dataset non ha righe di vincolo, quindi ciò che il perimetro incontra è la
    sola occupazione."""
    import time

    from tests import fermi

    dataset = fermi.build()
    prima_a = ex.per_risorsa([dataset["classes"]["1A"].pk])
    assert len(prima_a) == 26

    t0 = time.perf_counter()
    report = rank_constraints(dataset["schedule"], selected=prima_a)
    ristretto = time.perf_counter() - t0
    t0 = time.perf_counter()
    intero = rank_constraints(dataset["schedule"])
    pieno = time.perf_counter() - t0
    print(f"\nFermi blame: 1A {ristretto:.3f}s (26 att.), "
          f"intero {pieno:.3f}s (284 att.)")

    assert report.considered == 26
    assert report.unplaceable == ()
    assert intero.considered == 284
    # Il perimetro deve costare **meno**, ma non un decimo: la soglia è larga
    # apposta, perché il rapporto è una proprietà della macchina e la proprietà
    # da tenere ferma è solo che restringere non costi di più.
    assert ristretto < pieno


def test_apply_rooms_non_ruba_l_aula_a_chi_sta_fuori():
    """⚠ Chi sta fuori dal perimetro tiene la sua aula anche **senza
    assegnazione**, e per un giorno la seconda fase non lo sapeva.

    `activity_tokens` mette l'aula fra le chiavi di occupazione anche con
    `assigned_room` a NULL, se le candidate dichiarate sono **una sola**: a
    candidata unica la scelta è determinata, quindi occupare è esatto e non è
    una stima. `RoomContext.build` invece leggeva il solo `assigned_room`,
    quindi quella capienza non entrava in `frozen_load` e `_post_capacity` la
    regalava a chi stava dentro.

    Qui `fuori` dichiara la sola `R` e non ha assegnazione; `dentro` e
    `altra`, entrambe estratte e piazzate sulla stessa fascia, dichiarano
    `{R, S}` e devono spartirsele — quindi una delle due prende `R`, che è già
    occupata. La misura non è sul modello ma sull'orario che ne esce: zero
    conflitti d'occupazione prima, zero anche dopo. Con la lettura vecchia ne
    compariva uno **nuovo** sull'aula, creato dalla fase stessa."""
    from domain.analysis.conformity import check_schedule
    from domain.analysis.findings import Severity
    from domain.models import Extraction, SchoolClass
    from domain.solver.rooms import apply_rooms

    env = mini_school(days=1, slots=1)
    r = Room.objects.create(name="R")
    s = Room.objects.create(name="S")
    seconda = SchoolClass.objects.create(name="1B", study_plan=env["plan"],
                                         year=1)
    terza = SchoolClass.objects.create(name="1C", study_plan=env["plan"],
                                       year=1)
    fuori = make_activity(env["subject"], classes=[env["klass"]], rooms=[r])
    dentro = make_activity(env["subject"], classes=[seconda], rooms=[r, s])
    altra = make_activity(env["subject"], classes=[terza], rooms=[r, s])
    for act in (fuori, dentro, altra):
        place(env["schedule"], act, 0, 0)

    estrazione = Extraction.objects.create(name="le-due")
    estrazione.activities.set([dentro.pk, altra.pk])

    def conflitti():
        return sorted((f.code, f.resources) for f in check_schedule(env["schedule"])
                      if f.severity == Severity.HARD
                      and f.code.startswith("resource_"))

    assert conflitti() == [], "il passato è già in conflitto: il test non misura nulla"

    ctx = RoomContext.build(env["schedule"], extraction=estrazione)
    assert ctx.held == {fuori.pk: r.pk}, ctx.held

    soluzione = solve_rooms(env["schedule"], extraction=estrazione, workers=1)
    apply_rooms(soluzione, env["schedule"])
    assert conflitti() == [], "la seconda fase ha creato un conflitto d'aula"
    # `R` è tenuta da chi sta fuori: dentro la fascia resta una sola aula
    # libera, quindi una delle due estratte rinuncia. È il verdetto corretto.
    assert len(soluzione.unassigned) == 1, soluzione.assignments
