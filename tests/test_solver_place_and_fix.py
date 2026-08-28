"""`Piazza e sistema` (`domain/solver/place_and_fix.py`).

La funzione ha due meta' che vanno provate separatamente: quando si puo',
l'orario si ricompone e il rendiconto dice **chi si e' spostato**; quando non
si puo', il rifiuto e' **nominato** invece di essere un `INFEASIBLE`.
"""
import time

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (Activity, Extraction, Placement,
                          ResourceUnavailability, SchoolClass)
from domain.solver.model import apply, solve
from domain.solver.place_and_fix import place_and_fix
from domain.solver.registry import Builder, all_builders
from tests import fermi
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_solo_due_builder_prefiltrano():
    """⚠ La premessa di `CAUSALI_DI_PREFILTRO`, tenuta ferma da un test invece
    che ricordata: un pin puo' finire fuori dominio **solo** per la griglia o
    per un'indisponibilita', perche' sono i soli due builder che tolgono celle.
    Se ne comparisse un terzo, la diagnosi di `_perche_no` diventerebbe muta
    proprio sul suo caso — e questo test rosso lo direbbe."""
    quali = {type(b).__name__ for b in all_builders()
             if type(b).restrict is not Builder.restrict}
    assert quali == {"GridBuilder", "UnavailabilityBuilder"}, quali


def test_l_attivita_va_dove_le_si_dice_e_l_altra_si_sposta():
    """Il caso canonico: due attivita' della stessa classe, una gia' nella
    cella che si vuole. La forzata ci va, l'altra si ricolloca, e `moved` la
    nomina — che e' la domanda «qual e' l'insieme minimo di attivita' da
    spostare perche' A stia qui?»."""
    env = mini_school(days=1, slots=2)
    occupante = make_activity(env["subject"], classes=[env["klass"]])
    entrante = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], occupante, 0, 0)
    place(env["schedule"], entrante, 0, 1)

    esito = place_and_fix(env["schedule"], entrante.pk, 0, 0, workers=1)
    assert esito.ok, esito.solution.stats
    assert esito.solution.placements[entrante.pk] == (0, 0)
    assert esito.moved == (occupante.pk,)
    assert esito.dropped == ()
    assert esito.solution.placements[occupante.pk] == (0, 1)


def test_non_si_sposta_chi_non_serve():
    """⚠ La meta' che una sola misura non distingue: `moved` deve contenere il
    **minimo**, non tutti. Qui una terza classe non c'entra niente, e un
    rendiconto che la nominasse manderebbe l'utente a controllare un orario
    che nessuno ha toccato."""
    env = mini_school(days=1, slots=2)
    altra_classe = SchoolClass.objects.create(
        name="1B", study_plan=env["plan"], year=1)
    occupante = make_activity(env["subject"], classes=[env["klass"]])
    entrante = make_activity(env["subject"], classes=[env["klass"]])
    estranea = make_activity(env["subject"], classes=[altra_classe])
    place(env["schedule"], occupante, 0, 0)
    place(env["schedule"], entrante, 0, 1)
    place(env["schedule"], estranea, 0, 0)

    esito = place_and_fix(env["schedule"], entrante.pk, 0, 0, workers=1)
    assert esito.ok
    assert esito.moved == (occupante.pk,), esito.moved
    assert esito.solution.placements[estranea.pk] == (0, 0)


def test_non_si_scarta_per_non_spostare():
    """⚠ L'ordine della catena, provato invece che dichiarato: **non
    scartare** viene prima di **non spostare**. Con tre attivita' della stessa
    classe su tre fasce e la forzata in mezzo, l'orario si ricompone spostando;
    un ordine invertito preferirebbe lasciare qualcuno fuori."""
    env = mini_school(days=1, slots=3)
    a, b, c = [make_activity(env["subject"], classes=[env["klass"]])
               for _ in range(3)]
    for act, slot in ((a, 0), (b, 1), (c, 2)):
        place(env["schedule"], act, 0, slot)

    esito = place_and_fix(env["schedule"], c.pk, 0, 0, workers=1)
    assert esito.ok
    assert esito.solution.unplaced == (), esito.solution.unplaced
    assert esito.dropped == ()
    assert esito.solution.placements[c.pk] == (0, 0)


def test_le_congelate_non_si_spostano_e_il_rifiuto_lo_dice():
    """Il perno di ogni riparazione (`scope-v1.md`): occupata-spostabile e
    occupata-bloccata non sono lo stesso slot. Qui l'occupante e' bloccata e
    la classe ne ammette una sola: la richiesta e' impossibile, e la frase
    dice che l'orario non si ricompone — non che la cella sia vietata
    all'attivita', perche' non lo e'."""
    env = mini_school(days=1, slots=2)
    bloccata = make_activity(env["subject"], classes=[env["klass"]],
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    entrante = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], bloccata, 0, 0)
    place(env["schedule"], entrante, 0, 1)

    esito = place_and_fix(env["schedule"], entrante.pk, 0, 0, workers=1)
    assert not esito.ok
    assert esito.solution.stats["pin_fuori_dominio"] == ()
    assert esito.obstruction == (
        "La collocazione è ammissibile per l'attività, ma l'orario non si "
        "ricompone attorno: le altre attività non hanno dove andare.",)


def test_l_indisponibilita_rossa_e_nominata_per_nome():
    """🔑 La diagnosi che vale il pezzo: non «INFEASIBLE» ma *chi* e *perche'*.
    La cella e' fuori dal dominio dell'attivita' — un pre-filtro l'ha tolta —
    quindi nessuno spostamento altrui potrebbe aiutare, e la frase e' quella
    del catalogo delle causali."""
    env = mini_school(days=1, slots=2)
    entrante = make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]])
    place(env["schedule"], entrante, 0, 1)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    esito = place_and_fix(env["schedule"], entrante.pk, 0, 0, workers=1)
    assert not esito.ok
    assert esito.solution.stats["pin_fuori_dominio"] == ((entrante.pk, 0, 0),)
    assert esito.obstruction == ("Rossi Anna ha una indisponibilità",)


def test_la_diagnosi_non_incolpa_chi_si_potrebbe_spostare():
    """⚠ `trial_placements` valuta **tutti** i checker contro lo stato
    corrente, quindi sulla cella contesa vede anche l'occupazione da parte
    dell'attivita' che sta li'. Ma quella `Piazza e sistema` la sposterebbe:
    nominarla sarebbe una diagnosi falsa. Solo le causali dei due builder che
    pre-filtrano possono comparire.

    L'istanza tiene insieme le due cose: l'indisponibilita' che *e'* la causa
    e un'occupante che non lo e'."""
    env = mini_school(days=1, slots=2)
    occupante = make_activity(env["subject"], classes=[env["klass"]])
    entrante = make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]])
    place(env["schedule"], occupante, 0, 0)
    place(env["schedule"], entrante, 0, 1)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    esito = place_and_fix(env["schedule"], entrante.pk, 0, 0, workers=1)
    assert esito.obstruction == ("Rossi Anna ha una indisponibilità",)
    assert not any("occupata" in f for f in esito.obstruction)


def test_l_orario_scritto_e_legale():
    """L'oracolo, nella forma della casa: la soluzione applicata e riletta da
    `check_schedule` non porta violazioni hard. Un `Piazza e sistema` che
    forzasse producendo un orario illegale sarebbe peggio di un rifiuto."""
    env = mini_school(days=1, slots=3)
    a, b, c = [make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]]) for _ in range(3)]
    for act, slot in ((a, 0), (b, 1), (c, 2)):
        place(env["schedule"], act, 0, slot)

    esito = place_and_fix(env["schedule"], c.pk, 0, 0, workers=1)
    assert esito.ok
    apply(esito.solution, env["schedule"])
    hard = [f for f in check_schedule(env["schedule"])
            if f.severity == Severity.HARD]
    assert hard == [], hard


def test_lo_scarto_va_dichiarato_perche_moved_da_solo_mentirebbe():
    """⚠ Il caso in cui `moved` vuoto e' vero e ingannevole insieme: la forzata
    e' un blocco da due ore che si prende meta' giornata, e chi c'era non si
    **sposta** — resta fuori. Un rendiconto che dicesse «zero spostamenti» su
    un orario che ha perso un'ora sarebbe il peggiore possibile.

    ⚠ E lo scarto e' `dropped` solo per chi era piazzato: l'attivita' che non
    lo era e resta fuori non e' un danno di questa mossa, e contarla
    gonfierebbe il conto di ogni orario incompleto."""
    env = mini_school(days=1, slots=3)
    blocco = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[env["klass"]])
    mai_piazzata = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], blocco, 0, 1)
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 2)

    esito = place_and_fix(env["schedule"], blocco.pk, 0, 0, workers=1)
    assert esito.ok, esito.solution.stats
    assert esito.solution.placements[blocco.pk] == (0, 0)
    # Il blocco occupa le fasce 0 e 1: resta una sola fascia per tre attivita'.
    assert len(esito.dropped) == 1, esito.dropped
    assert set(esito.dropped) <= {a.pk, b.pk}
    assert mai_piazzata.pk in esito.solution.unplaced
    assert mai_piazzata.pk not in esito.dropped


def test_fermi_intero_misurato():
    """🔑 La misura che conta, e stavolta il Fermi la puo' dare: su un orario
    **pieno** — 284 attivita' piazzate, zero scarti — forzare una lezione dove
    ne sta un'altra della stessa classe costa **uno** spostamento. E' la
    risposta alla domanda della condizione 1 di `scope-v1.md`, su un'istanza
    vera invece che su una scuola giocattolo: l'insieme minimo e' uno scambio.

    ⚠ E il costo va detto: ~4 s contro il secondo scarso del `solve` che ha
    generato l'orario. La differenza e' **L4**, che prima non aveva niente da
    conservare e ora confronta 284 collocazioni — cioe' e' il prezzo di
    disturbare poco, non un difetto.

    ⚠ Come sempre sul Fermi, e' una misura del **costo** e non della
    copertura: il dataset non ha righe di vincolo, quindi la ricomposizione
    incontra la sola occupazione."""
    dataset = fermi.build()
    partenza = solve(dataset["schedule"], time_limit=30, workers=1)
    assert partenza.status == "OPTIMAL" and partenza.unplaced == ()
    apply(partenza, dataset["schedule"])

    prima = Placement.objects.select_related("activity").order_by("activity_id").first()
    bersaglio = (Placement.objects
                 .filter(activity__classes__in=list(prima.activity.classes.all()))
                 .exclude(activity_id=prima.activity_id)
                 .order_by("activity_id").first())

    t0 = time.perf_counter()
    esito = place_and_fix(dataset["schedule"], prima.activity_id,
                          bersaglio.day, bersaglio.start_slot,
                          time_limit=30, workers=1)
    elapsed = time.perf_counter() - t0
    print(f"\nFermi place_and_fix: {elapsed:.2f}s, {len(esito.moved)} spostate")
    assert esito.ok, esito.solution.stats
    assert esito.solution.placements[prima.activity_id] == (bersaglio.day,
                                                            bersaglio.start_slot)
    assert esito.dropped == ()
    assert len(esito.moved) <= 5, esito.moved

    apply(esito.solution, dataset["schedule"])
    # ⚠ `room_unassigned` si esclude per la ragione con cui lo esclude
    # `manage.py solve`: descrive un orario **incompleto**, non illegale — le
    # aule le assegna la seconda fase, che qui non e' girata.
    hard = [f for f in check_schedule(dataset["schedule"])
            if f.severity == Severity.HARD and f.code != "room_unassigned"]
    assert hard == [], hard[:5]


def test_il_pin_su_una_bloccata_dice_che_e_bloccata():
    """⚠ «I pre-filtri sono due» non implica «un pin fuori dominio viene solo
    dai pre-filtri», e per un giorno il commento di `CAUSALI_DI_PREFILTRO`
    diceva il contrario. Il dominio lo restringe anche `SolverContext.build`:
    a un'immobile gia' piazzata da' un dominio di **cardinalita' uno**, quindi
    qualunque altra cella e' «fuori dominio» — anche una cella vuota, su una
    griglia senza un solo vincolo.

    La vecchia risposta era «La collocazione non e' ammissibile per
    l'attivita'»: falsa, e falsa nella direzione peggiore, perche' manda a
    cercare un vincolo che non esiste. Il rimedio non e' allentare niente, e'
    sbloccare."""
    env = mini_school(days=1, slots=3)
    bloccata = make_activity(env["subject"], classes=[env["klass"]],
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], bloccata, 0, 0)

    esito = place_and_fix(env["schedule"], bloccata.pk, 0, 2, workers=1)
    assert not esito.ok
    assert esito.solution.stats["pin_fuori_dominio"] == ((bloccata.pk, 0, 2),)
    assert len(esito.obstruction) == 1
    frase = esito.obstruction[0]
    assert "bloccata su giorno 0, fascia 0" in frase, frase
    assert "sbloccata" in frase, frase


def test_il_pin_fuori_estrazione_nomina_l_estrazione():
    """Il gemello: fuori dal perimetro un'attivita' e' congelata dov'e'
    (`SolverContext.build`), quindi il pin esce dal dominio per una ragione
    che non e' un vincolo dell'orario. La frase deve nominare l'estrazione,
    perche' il rimedio e' allargarla."""
    env = mini_school(days=1, slots=3)
    fuori = make_activity(env["subject"], classes=[env["klass"]])
    dentro = make_activity(env["subject"])
    place(env["schedule"], fuori, 0, 0)
    place(env["schedule"], dentro, 0, 1)
    estrazione = Extraction.objects.create(name="solo-dentro")
    estrazione.activities.add(dentro)

    esito = place_and_fix(env["schedule"], fuori.pk, 0, 2,
                          extraction=estrazione, workers=1)
    assert not esito.ok
    assert esito.obstruction and "solo-dentro" in esito.obstruction[0]


def test_il_pin_su_una_sospesa_lo_dice():
    """Una sospesa non entra nemmeno in `ScheduleState`: senza questa lettura
    la risposta era «L'attivita' non fa parte di questo orario», che e' vera
    ma non dice **perche'**."""
    env = mini_school(days=1, slots=3)
    sospesa = make_activity(env["subject"], classes=[env["klass"]],
                            immobility=Activity.Immobility.SUSPENDED)

    esito = place_and_fix(env["schedule"], sospesa.pk, 0, 1, workers=1)
    assert not esito.ok
    assert esito.obstruction and "sospesa" in esito.obstruction[0]
