"""La classifica dei vincoli per fallimenti causati (`domain/analysis/blame.py`).

I test sono costruiti attorno alla distinzione che il modulo esiste per fare:
**escludere celle** e **rendere impiazzabile un'attivita'** sono due cose
diverse, e solo la seconda dice all'utente cosa allentare. Un vincolo che
esclude quattrocento celle senza mai essere l'ultimo a chiudere la porta non
va toccato; uno che ne esclude due, ma sono le due che restavano, si'.
"""
import datetime as dt
import time

import pytest

from domain.analysis.blame import famiglie_silenziose, rank_constraints
from domain.models import (
    Activity, ResourceTimeConstraint, ResourceUnavailability, SchoolClass,
    Teacher,
)
from tests import fermi
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
HARD = ResourceUnavailability.Level.HARD


def _tutta_la_griglia(env, risorsa, slots):
    for s in slots:
        ResourceUnavailability.objects.create(
            resource=risorsa, day=0, slot=s, level=HARD)


def _riga(report, code, risorsa=None):
    for r in report.rows:
        if r.code == code and (risorsa is None or r.resources == (risorsa.pk,)):
            return r
    raise AssertionError(f"{code} assente: {[r.code for r in report.rows]}")


def test_la_classifica_nomina_la_causale_e_la_risorsa():
    """La riga porta la frase italiana con dentro il nome della risorsa: e'
    cio' che l'utente va a cercare nella propria anagrafica."""
    env = mini_school(days=1, slots=4)
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    _tutta_la_griglia(env, env["teacher"], (0, 1))

    riga = _riga(rank_constraints(env["schedule"]), "unavailability")
    assert riga.resources == (env["teacher"].pk,)
    assert riga.statement == "Rossi Anna ha una indisponibilità"
    assert (riga.cells_blocked, riga.cells_alone) == (2, 2)


def test_escludere_celle_non_e_rendere_impiazzabile():
    """Due celle escluse su quattro: l'attivita' ha ancora dove andare, quindi
    il vincolo non blocca e non libera nessuno. E' la meta' del modulo che una
    somma di celle non saprebbe dire."""
    env = mini_school(days=1, slots=4)
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    _tutta_la_griglia(env, env["teacher"], (0, 1))

    report = rank_constraints(env["schedule"])
    riga = _riga(report, "unavailability")
    assert (riga.activities_blocked, riga.activities_freed) == (0, 0)
    assert report.unplaceable == ()


def test_il_vincolo_che_chiude_l_ultima_porta_libera_l_attivita():
    """Stessa istanza, indisponibilita' su tutte e quattro le fasce: ogni cella
    ha **questa sola** causale, quindi togliendola l'attivita' torna
    piazzabile."""
    env = mini_school(days=1, slots=4)
    a = make_activity(env["subject"], classes=[env["klass"]],
                      teachers=[env["teacher"]])
    _tutta_la_griglia(env, env["teacher"], range(4))

    report = rank_constraints(env["schedule"])
    riga = _riga(report, "unavailability")
    assert (riga.activities_blocked, riga.activities_freed) == (1, 1)
    assert report.unplaceable == (a.pk,)


def test_due_vincoli_che_bloccano_insieme_non_liberano_nessuno():
    """🔑 Il caso che separa `activities_freed` da `activities_blocked`, e la
    ragione per cui il primo non e' una somma: docente **e** classe
    indisponibili sulle stesse quattro fasce. Ciascuno dei due, da solo,
    basterebbe a svuotare il dominio — quindi entrambi *bloccano* — ma
    allentarne uno solo non apre niente, perche' nessuna cella ha una causale
    sola. Una classifica che li dichiarasse liberatori manderebbe l'utente a
    smontare un vincolo per niente."""
    env = mini_school(days=1, slots=4)
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    _tutta_la_griglia(env, env["teacher"], range(4))
    _tutta_la_griglia(env, env["klass"], range(4))

    report = rank_constraints(env["schedule"])
    for risorsa in (env["teacher"], env["klass"]):
        riga = _riga(report, "unavailability", risorsa)
        assert riga.activities_blocked == 1
        assert riga.activities_freed == 0, riga
        assert riga.cells_alone == 0, riga
        assert riga.cells_blocked == 4


def test_l_azionabile_precede_la_pressione():
    """⚠ L'ordine non e' per numero di celle escluse, ed e' una decisione: il
    vincolo che esclude **sedici** celle senza mai chiudere una porta sta sotto
    a quello che ne esclude cinque ma libera un'attivita'. Ordinare per
    pressione metterebbe in cima, su ogni scuola vera, l'indisponibilita' piu'
    larga — che e' quasi sempre quella che non si puo' togliere."""
    env = mini_school(days=1, slots=5)
    altro = Teacher.objects.create(name="Bianchi Ugo", last_name="Bianchi",
                                   first_name="Ugo")
    # Chiuso: le cinque fasce del docente 1 sono tutte indisponibili.
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    _tutta_la_griglia(env, env["teacher"], range(5))
    # Sotto pressione ma aperto: quattro attivita' del docente 2, a cui restano
    # le fasce indisponibili meno una — sedici celle escluse, zero porte chiuse.
    for _ in range(4):
        make_activity(env["subject"], classes=[env["klass"]], teachers=[altro])
    _tutta_la_griglia(env, altro, range(1, 5))

    report = rank_constraints(env["schedule"])
    primo = report.rows[0]
    assert primo.resources == (env["teacher"].pk,), report.rows
    assert primo.activities_freed == 1
    altre = [r for r in report.rows[1:]]
    assert all(r.activities_freed == 0 for r in altre), altre
    assert max(r.cells_blocked for r in altre) > primo.cells_blocked


def test_le_famiglie_non_monotone_tacciono_e_lo_dichiarano():
    """⚠ Il D.T.B. non puo' comparire in classifica, e non e' una svista.
    `MAX_GAP_HOURS` e' `PLACEMENT_MONOTONE = False`: piazzare **dentro** un
    buco lo riduce, quindi ogni cella di prova cambia la chiave del finding e
    il criterio «chiave nuova ⇒ cella esclusa» diventa falso. Contarlo lo
    metterebbe in cima a qualunque classifica per un artefatto del criterio.

    Il test tiene ferme le due meta': la famiglia non compare, **e**
    `famiglie_silenziose()` la nomina — perche' una rinuncia che il comando
    non dichiara e' indistinguibile da un vincolo innocuo.

    ⚠ Le due attivita' che creano il buco sono **congelate**, e la prima
    stesura di questo test non lo faceva: `free_candidates` spiazza tutte le
    mobili, quindi il buco spariva prima di essere misurato e il test restava
    verde anche togliendo il rilassamento. E' la trappola §4.1 del violatore
    di Hall, questa volta dentro il caso di prova."""
    env = mini_school(days=1, slots=4)
    for slot in (0, 3):
        a = make_activity(env["subject"], classes=[env["klass"]],
                          teachers=[env["teacher"]],
                          immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], a, 0, slot)
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    codici = {r.code for r in rank_constraints(env["schedule"]).rows}
    assert "max_gap" not in codici, codici
    assert str(ResourceTimeConstraint.Type.MAX_GAP_HOURS) in famiglie_silenziose()


def test_le_firme_di_settimana_si_uniscono_invece_di_sommarsi():
    """⚠ Un'attivita' va collocata in **una** cella valida in **tutte** le
    settimane in cui e' attiva. L'indisponibilita' qui e' **datata** — il
    meccanismo delle assenze — quindi vale in una settimana sola e crea due
    firme: la cella 0 e' libera in una e occupata nell'altra, e la risposta
    giusta e' «esclusa».

    ⚠ E l'attivita' va contata **una volta**, non una per firma: sommare le
    firme raddoppierebbe ogni numero su una scuola vera, dove le firme sono
    trentacinque."""
    env = mini_school(days=1, slots=2)
    a = make_activity(env["subject"], classes=[env["klass"]],
                      teachers=[env["teacher"]])
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0, level=HARD,
        date=env["year"].first_week_monday)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=1, level=HARD,
        date=env["year"].first_week_monday + dt.timedelta(days=7))

    report = rank_constraints(env["schedule"])
    riga = _riga(report, "unavailability")
    assert report.considered == 1
    assert report.unplaceable == (a.pk,)
    assert riga.cells_blocked == 2, riga
    assert riga.activities_freed == 1


def test_l_attivita_piu_lunga_della_giornata_non_ha_colpevoli():
    """Il caso senza nessuna cella da provare: e' impiazzabile e non e' colpa
    di nessun vincolo. Va detta impiazzabile lo stesso — sparire dal rapporto
    sarebbe il verdetto peggiore — e nessuna riga deve prendersene il merito."""
    env = mini_school(days=1, slots=2)
    a = make_activity(env["subject"], classes=[env["klass"]],
                      teachers=[env["teacher"]], slots=3)

    report = rank_constraints(env["schedule"])
    assert report.unplaceable == (a.pk,)
    assert report.considered == 1
    assert sum(r.activities_freed for r in report.rows) == 0


def test_l_ordine_e_riproducibile():
    """A parita' di numeri la classifica si spareggia sull'identita' della
    riga: due letture della stessa scuola devono dare la stessa pagina, o non
    e' leggibile due volte."""
    env = mini_school(days=1, slots=4)
    for _ in range(3):
        klass = SchoolClass.objects.create(
            name=f"X{_}", study_plan=env["plan"], year=1)
        make_activity(env["subject"], classes=[klass], teachers=[env["teacher"]])
        _tutta_la_griglia(env, klass, range(4))

    prima = rank_constraints(env["schedule"]).rows
    dopo = rank_constraints(env["schedule"]).rows
    assert prima == dopo
    assert len(prima) > 1


def test_fermi_intero_misurato():
    """⚠ Come per la fase 5, sul Fermi questo misura il **costo**, mai la
    **copertura**: il dataset non ha righe `ResourceTimeConstraint` ne'
    `SubjectConstraint`, quindi le uniche causali che possono comparire sono
    le indisponibilita' — le tre giornate intere di `vincoli-attesi.md` — e
    zero attivita' impiazzabili e' l'esito atteso, non un risultato.

    Misurato: ~0,25s su 284 attivita' e **una** firma di settimana. Il costo e'
    lineare nelle firme, come per `analyze_hall`, quindi il numero da portarsi
    dietro e' «~0,25s per firma» e non un assoluto."""
    dataset = fermi.build()
    t0 = time.perf_counter()
    report = rank_constraints(dataset["schedule"])
    elapsed = time.perf_counter() - t0
    print(f"\nFermi blame: {elapsed:.3f}s, {len(report.rows)} righe")
    assert report.considered == 284
    assert report.unplaceable == ()
    assert {r.code for r in report.rows} == {"unavailability"}
    assert all(r.activities_freed == 0 for r in report.rows)
    assert elapsed < 5.0
