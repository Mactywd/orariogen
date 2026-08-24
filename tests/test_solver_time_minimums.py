"""I tre vincoli orari che chiedono un minimo invece di imporre un tetto. Il
test che conta e' quello su FREE_GUARANTEED: il checker conta le mezze
giornate libere **solo sui giorni che hanno attivita'**, e un builder che le
contasse su tutti i giorni accetterebbe orari che il checker boccia.

⚠ I cinque test per seed di ogni famiglia (`test_famiglia` in
tests/test_solver_witness.py, parametrizzato su `sorted(DERIVERS) x [1..5]`)
li copre gia' la sola registrazione dei tre derivatori sotto: non li si
riscrive qui."""
import datetime as dt

import pytest

from domain.models import (
    Activity, Discipline, Period, ResourceTimeConstraint, Schedule,
    SchoolClass, SchoolYear, StudyPlan, Subject, Teacher, TimeGrid,
)
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school, place
from tests.test_solver_oracle import violazioni

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


def _scuola_senza_pomeriggio():
    """Come mini_school(), ma con `morning_end_slot == slots_per_day`: la
    mezza giornata pomeridiana e' vuota per costruzione (griglia 5x4). Serve
    a riprodurre Important 1 della review Task 7 — `v.halves()` restituisce
    uno `span` vuoto per il pomeriggio, e il vecchio `if not len(span):
    continue` saltava quella meta' del tutto invece di lasciarla contribuire
    come costante scarica."""
    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=4, slot_minutes=60, morning_end_slot=4
    )
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 10, 11),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1",
        start_date=year.start_date, end_date=year.end_date,
    )
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="Rossi Anna", last_name="Rossi",
                                     first_name="Anna")
    return {
        "grid": grid, "year": year, "period": period, "schedule": schedule,
        "discipline": disc, "subject": subject, "plan": plan,
        "klass": klass, "teacher": teacher,
    }


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


def test_arrival_departure_giorno_vuoto_conta_come_conforme():
    """Requisito aggiunto dal controller dopo la review Task 7 (Minor
    promossa): ArrivalDepartureChecker legge `if not slots: compliant += 1`
    (`checkers/time_constraints.py`) — un giorno senza alcuna attivita' e'
    conforme, non violato. Un'unica attivita' su cinque giorni richiesti
    (`days=5`) lascia quattro giorni **completamente vuoti**: un builder che
    trattasse "nessuna attivita'" come "non conforme" renderebbe la soglia
    irraggiungibile (al massimo un giorno puo' mai essere popolato), quindi
    INFEASIBLE. Il comportamento corretto e' FEASIBLE: i quattro giorni vuoti
    contano gratis, resta solo da piazzare l'unica attivita' fuori dalla
    fascia vietata."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.ARRIVAL_DEPARTURE,
        params={"not_before_slot": 1, "days": 5})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"arrival_departure"}) == set()


def test_adr018_arrival_departure_congelata_in_zona_vietata_non_blocca_il_solver():
    """Important 2 della review Task 7. Un'attivita' congelata occupa lo
    slot 0 (vietato da `not_before_slot=1`) il giorno 0: quel giorno e' gia'
    reso non conforme dal solo passato, e nessuna libera puo' recuperarlo. Con
    `days=5` (tutti i 5 giorni devono essere conformi) il vincolo, letto alla
    lettera, sarebbe insoddisfacibile per colpa del passato — esattamente
    l'errore che ADR-018 esiste per evitare. Una seconda attivita', libera,
    dello stesso docente deve poter comunque essere piazzata: la soglia
    residua e' `min(5, 5 - 1) = 4`, raggiungibile sui quattro giorni ancora
    liberi."""
    env = mini_school()
    congelata = make_activity(env["subject"], teachers=[env["teacher"]],
                              classes=[env["klass"]],
                              immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], congelata, day=0, slot=0)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.ARRIVAL_DEPARTURE,
        params={"not_before_slot": 1, "days": 5})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id] is not None


def test_adr018_free_guaranteed_congelate_non_bloccano_il_solver():
    """Important 2 della review Task 7, sull'altra famiglia. Cinque
    attivita' congelate, una per giorno (nessun giorno resta libero): la
    soglia `free_days=1` e' gia' irraggiungibile dal solo passato. Una
    sesta attivita', libera, dello stesso docente non deve rendere il
    modello infattibile: la soglia residua e' `min(1, 5 - 5) = 0`, vacua."""
    env = mini_school()
    congelate = [
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for _ in range(5)
    ]
    for day, act in enumerate(congelate):
        place(env["schedule"], act, day=day, slot=0)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_days": 1})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id] is not None


def test_free_guaranteed_meta_pomeriggio_vuota_non_blocca_una_sola_mezza():
    """Important 1 della review Task 7. Griglia 5x4 con
    `morning_end_slot == slots_per_day`: il pomeriggio e' vuoto per ogni
    giorno. `FreeGuaranteedChecker` conta `(not morning) + (not afternoon)`
    per ciascun giorno **con attivita'** — con `afternoon == []` quel
    termine vale 1 su ogni giorno lavorato, gratis. Il vecchio
    `if not len(span): continue` saltava del tutto la meta' pomeridiana:
    zero letterali generati, quindi la mattina (l'unica meta' rimasta)
    finiva per essere `attivo AND NOT attivo == 0` sempre, e qualunque
    `free_half_days >= 1` diventava insoddisfacibile. Con una sola
    attivita' e `free_half_days=1` dev'essere FEASIBLE: il pomeriggio vuoto
    del giorno lavorato basta da solo."""
    env = _scuola_senza_pomeriggio()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"free_guaranteed"}) == set()


def test_free_guaranteed_meta_pomeriggio_vuota_normale_sulla_griglia_6():
    """Controprova indicata dal revisore: la stessa richiesta
    (`free_half_days=1`) sulla griglia normale di `mini_school()`
    (`slots_per_day=6`, pomeriggio non vuoto) era gia' FEASIBLE prima della
    correzione — il difetto e' specifico alla griglia con pomeriggio vuoto,
    non una regressione generale."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats


def test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno():
    """Important 1 del giro 1 della review Task 7. Il residuo di
    `free_half_days` era calcolato come `2 * days_per_cycle - mezze_perse`,
    cioe' assumendo che un giorno possa contribuire **due** mezze libere.
    Non puo': `libera = attivo AND NOT meta`, quindi un giorno attivo ha per
    forza almeno una meta' occupata (ne da' al massimo una libera) e un
    giorno inattivo non ne da' nessuna — il massimo raggiungibile e'
    `days_per_cycle`, e va tolto un giorno per ogni giorno **interamente**
    congelato.

    L'istanza: due congelate sul giorno 0, una per meta' (slot 0 mattina,
    slot 4 pomeriggio), piu' sei attivita' libere, con `free_half_days=5`.
    Il massimo raggiungibile e' 4 (i giorni 1..4, una mezza ciascuno): il
    giorno 0 e' perso per intero. Col vecchio bound la soglia restava 5
    (`min(5, 10 - 2)`) e il modello era INFEASIBLE **per colpa del solo
    passato**, cio' che ADR-018 vieta. Col bound corretto
    (`min(5, 5 - 1) = 4`) e' risolvibile."""
    env = mini_school()
    for slot in (0, 4):
        congelata = make_activity(
            env["subject"], teachers=[env["teacher"]], classes=[env["klass"]],
            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], congelata, day=0, slot=slot)
    libere = [make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]]) for _ in range(6)]
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 5})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert all(soluzione.placements[a.id] is not None for a in libere)


def test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate():
    """Controprova del test sopra: senza congelate il bound non deve
    ammorbidire nulla. Griglia 5x6, sei attivita' libere e
    `free_half_days=5` — il massimo raggiungibile e' esattamente 5 (una
    mezza libera per ciascuno dei cinque giorni), quindi il vincolo e'
    stretto e la soluzione deve lasciare almeno cinque mezze giornate
    libere secondo il checker."""
    env = mini_school()
    for _ in range(6):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 5})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"free_guaranteed"}) == set()
