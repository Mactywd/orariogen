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
from ortools.sat.python import cp_model

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (
    Activity, Discipline, Period, ResourceTimeConstraint,
    ResourceUnavailability, Schedule, SchoolClass, SchoolYear, StudyPlan,
    Subject, Teacher, TimeGrid,
)
from domain.solver.model import apply, build_model, solve
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
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
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
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
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
    passato**, cio' che ADR-018 vieta.

    ⚠ Il bound che questo test difendeva **non esiste piu'** (Finding 2
    della review finale: due soglie clampate una per volta sono
    insoddisfacibili insieme). L'istanza resta valida come test di ADR-018 —
    dev'essere fattibile — ma ora passa per un'altra strada: la baseline del
    checker e' gia' violata (`free_half_days = 0`), ci sono congelate, e il
    ramo status quo chiede `>= 0`. Il posto dove il bound per-giorno e'
    ancora difeso e'
    `test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate`,
    qui sotto."""
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


# ---------------------------------------------------------------------------
# ADR-018 sui due minimi non separabili — review finale, Finding 1 e Finding 2
# ---------------------------------------------------------------------------
#
# Forma obbligatoria per i test di **presenza** (Ruling 85): si costruisce il
# modello e si **forza** la collocazione che viola, aspettandosi INFEASIBLE.
# Mai «risolvi e guarda dove e' finita»: senza forzatura CP-SAT e' libero di
# scegliere una soluzione conforme anche quando nulla gliela impone, e il test
# passerebbe pure con il builder spento.


def _scuola_3x4():
    """Griglia 3 giorni x 4 fasce con `morning_end_slot=2`: mattina = fasce
    0-1, pomeriggio = fasce 2-3. E' la griglia dell'istanza minima del
    Finding 2 della review finale."""
    grid = TimeGrid.objects.create(
        days_per_cycle=3, slots_per_day=4, slot_minutes=60, morning_end_slot=2
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


def _stato_forzando(schedule, forzature):
    """Costruisce il modello, fissa le collocazioni indicate e risolve. Le
    forzature sono `[(attivita', (giorno, fascia)), ...]`; una KeyError qui
    significa che quella cella non e' nemmeno nel dominio, ed e' un fallimento
    legittimo del test, non un dettaglio da aggirare."""
    model, ctx = build_model(schedule)
    for act, (day, slot) in forzature:
        model.Add(ctx.x[(act.id, day, slot)] == 1)
    return cp_model.CpSolver().Solve(model)


def _baseline_viola(schedule, code):
    return any(f.code == code and f.severity == Severity.HARD
               for f in check_schedule(schedule))


def _congelata(env, **kwargs):
    return make_activity(env["subject"], teachers=[env["teacher"]],
                         classes=[env["klass"]],
                         immobility=Activity.Immobility.LOCKED_IN_PLACE,
                         **kwargs)


def _libera(env, **kwargs):
    return make_activity(env["subject"], teachers=[env["teacher"]],
                         classes=[env["klass"]], **kwargs)


# --- Finding 1: MIN_DISTRIBUTION -------------------------------------------


def test_adr018_min_distribution_accetta_lo_status_quo():
    """La riproduzione del Finding 1 della review finale, come test di non
    regressione.

    Griglia 5x6, un docente, `min_minutes_per_day=60, min_days=3`. Due
    congelate sullo **stesso** giorno (0, 0) e (0, 1), una libera al suo
    posto su (1, 0): restano al piu' due giorni distinti qualificanti, quindi
    la baseline del checker **e' gia' violata** e nessuna libera puo'
    ripararla. Il builder postava `sum(qualificati) >= 3` sul parametro
    grezzo: `solve()` rispondeva INFEASIBLE, e restava INFEASIBLE perfino
    forzando la libera **dov'e' gia'** — un solver che rifiuta lo status quo,
    cioe' esattamente la modalita' di fallimento che ADR-018 esiste per
    escludere."""
    env = mini_school()
    a = _congelata(env)
    b = _congelata(env)
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    c = _libera(env)
    place(env["schedule"], c, day=1, slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})

    assert _baseline_viola(env["schedule"], "min_distribution")
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    # e lo status quo, forzato, dev'essere accettato
    stato = _stato_forzando(env["schedule"], [(c, (1, 0))])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_min_distribution_morde_da_zero_senza_congelate():
    """⚠ Il modo piu' facile di rompere la correzione e' farla degenerare in
    «la soglia non si posta mai». Qui non c'e' **nessuna** congelata e la
    soglia e' irraggiungibile per conto suo: due attivita' da un'ora non
    possono qualificare tre giorni distinti. La risposta onesta e'
    INFEASIBLE, e il residuo non deve ammorbidirla."""
    env = mini_school()
    for _ in range(2):
        _libera(env)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_min_distribution_senza_congelate_ripara_anche_se_la_baseline_viola():
    """La seconda meta' della regola «nessuna congelata → soglia grezza»: qui
    la baseline **e' gia' violata**, ma da attivita' tutte **libere** (due
    ore sullo stesso giorno, `min_days=2`). Non c'e' nessun passato da
    rispettare: il solver deve riparare, non conservare. Forzando entrambe
    sul giorno 0 il modello dev'essere INFEASIBLE.

    E' il test che distingue «la baseline viola» da «la baseline viola **per
    colpa delle congelate**»: senza la guardia sulle congelate il ramo status
    quo scatterebbe anche qui, e forzare il giorno 0 diventerebbe fattibile."""
    env = mini_school()
    x, y = _libera(env), _libera(env)
    place(env["schedule"], x, day=0, slot=0)
    place(env["schedule"], y, day=0, slot=1)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 2})

    assert _baseline_viola(env["schedule"], "min_distribution")
    stato = _stato_forzando(env["schedule"], [(x, (0, 0)), (y, (0, 1))])
    assert stato == cp_model.INFEASIBLE


def test_min_distribution_congelate_che_lasciano_la_soglia_raggiungibile():
    """Il ramo di riparazione. Una congelata su (0, 0) e due libere piazzate
    su giorni distinti: la baseline **rispetta** la soglia (tre giorni
    qualificanti su `min_days=3`), quindi il residuo non deve entrare in
    gioco e la soglia grezza resta un obbligo. Forzando le due libere sullo
    **stesso** giorno i giorni qualificanti scendono a due: INFEASIBLE."""
    env = mini_school()
    a = _congelata(env)
    place(env["schedule"], a, day=0, slot=0)
    f1, f2 = _libera(env), _libera(env)
    place(env["schedule"], f1, day=1, slot=0)
    place(env["schedule"], f2, day=2, slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})

    assert not _baseline_viola(env["schedule"], "min_distribution")
    stato = _stato_forzando(env["schedule"], [(f1, (1, 0)), (f2, (1, 1))])
    assert stato == cp_model.INFEASIBLE


def test_min_distribution_lo_status_quo_non_e_un_lasciapassare():
    """`B` si calcola sul piazzamento corrente **completo** — congelate
    incluse — non sulle sole libere. Qui una congelata occupa il giorno 0 e
    due libere stanno sui giorni 1 e 2: `min_days=4` non e' raggiungibile
    (i giorni qualificabili sono al piu' tre), quindi si passa dal ramo
    status quo con `B = 3`. Quel ramo non e' un permesso di peggiorare:
    forzando le due libere sullo **stesso** giorno i qualificanti scendono a
    due, sotto `B`, e il modello dev'essere INFEASIBLE.

    Mutazione che questo test intercetta: `B` calcolato ignorando le
    congelate varrebbe 2, e la forzatura passerebbe."""
    env = mini_school()
    a = _congelata(env)
    place(env["schedule"], a, day=0, slot=0)
    f1, f2 = _libera(env), _libera(env)
    place(env["schedule"], f1, day=1, slot=0)
    place(env["schedule"], f2, day=2, slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 4})

    assert _baseline_viola(env["schedule"], "min_distribution")
    # lo status quo resta ammesso...
    assert _stato_forzando(env["schedule"], [(f1, (1, 0)), (f2, (2, 0))]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE)
    # ...ma peggiorarlo no
    assert _stato_forzando(
        env["schedule"], [(f1, (1, 0)), (f2, (1, 1))]) == cp_model.INFEASIBLE


# --- Finding 2: FREE_GUARANTEED --------------------------------------------


def test_adr018_free_guaranteed_accetta_lo_status_quo_con_due_soglie():
    """La riproduzione del Finding 2 della review finale.

    Griglia 3x4 con `morning_end_slot=2`, un docente, riga
    `free_days=2, free_half_days=2`. Congelate su (1, 3), (1, 1) e (2, 0),
    libera su (1, 0). Le due soglie residue erano clampate
    **indipendentemente**: `giorni_persi = 2` portava la soglia dei giorni a
    1 — cioe' il giorno 0 doveva restare vuoto — mentre la soglia delle mezze
    restava 2 contando il giorno 0 come se potesse contribuirne una. Ma una
    mezza libera si conta solo se il **giorno lavora**: il giorno 0, tenuto
    vuoto dalla prima soglia, contribuisce zero. Ciascuna soglia era
    raggiungibile da sola, la congiunzione no, e il modello rispondeva
    INFEASIBLE per colpa del solo passato — perfino forzando la libera
    dov'e' gia'."""
    env = _scuola_3x4()
    for day, slot in ((1, 3), (1, 1), (2, 0)):
        place(env["schedule"], _congelata(env), day=day, slot=slot)
    libera = _libera(env)
    place(env["schedule"], libera, day=1, slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 2, "free_half_days": 2})

    assert _baseline_viola(env["schedule"], "free_guaranteed")
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    stato = _stato_forzando(env["schedule"], [(libera, (1, 0))])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_free_guaranteed_morde_da_zero_senza_congelate():
    """Il gemello del test «da zero» di MIN_DISTRIBUTION. Nessuna congelata,
    `free_days=5` su una griglia di cinque giorni e una sola attivita': dove
    la si metta, quel giorno lavora, e i giorni liberi sono al massimo
    quattro. INFEASIBLE, e il residuo non deve ammorbidirlo."""
    env = mini_school()
    _libera(env)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 5})
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_free_guaranteed_senza_congelate_ripara_anche_se_la_baseline_viola():
    """Come per MIN_DISTRIBUTION: baseline gia' violata ma da sole attivita'
    **libere** (due ore su due giorni distinti, `free_days=4` su cinque
    giorni → tre giorni liberi, uno di meno del richiesto). Nessun passato da
    rispettare: il solver deve accorpare le due ore sullo stesso giorno.
    Forzarle su giorni distinti dev'essere INFEASIBLE."""
    env = mini_school()
    x, y = _libera(env), _libera(env)
    place(env["schedule"], x, day=0, slot=0)
    place(env["schedule"], y, day=1, slot=0)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 4})

    assert _baseline_viola(env["schedule"], "free_guaranteed")
    stato = _stato_forzando(env["schedule"], [(x, (0, 0)), (y, (1, 0))])
    assert stato == cp_model.INFEASIBLE


def test_free_guaranteed_congelate_che_lasciano_la_soglia_raggiungibile():
    """Il ramo di riparazione. Una congelata su (0, 0) e una libera piazzata
    sullo **stesso** giorno: la baseline rispetta `free_days=4` (i giorni 1-4
    sono liberi), quindi la soglia grezza resta un obbligo e la libera non
    puo' aprire un quinto giorno. Forzandola sul giorno 1: INFEASIBLE."""
    env = mini_school()
    a = _congelata(env)
    place(env["schedule"], a, day=0, slot=0)
    libera = _libera(env)
    place(env["schedule"], libera, day=0, slot=1)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 4})

    assert not _baseline_viola(env["schedule"], "free_guaranteed")
    stato = _stato_forzando(env["schedule"], [(libera, (1, 0))])
    assert stato == cp_model.INFEASIBLE


def test_free_guaranteed_le_due_soglie_stanno_sotto_un_solo_booleano():
    """Il cuore del Finding 2, dal lato del divieto invece che da quello
    dell'ammissione.

    Griglia 5x6 (`morning_end_slot=4`), riga `free_days=1,
    free_half_days=3`. Due congelate sul giorno 0, una per meta' (slot 0 e
    slot 4), e **tre** libere piazzate tutte sul giorno 1. La baseline del
    checker: giorni liberi 3 (>= 1, conforme), mezze libere 1 (< 3, viola) —
    un solo finding per **entrambe** le quantita'.

    I due rami devono stare sotto lo stesso booleano: o si ripara
    (`giorni >= 1 AND mezze >= 3`, ottenibile spargendo le tre libere su tre
    mattine distinte) o si conserva la baseline (`giorni >= 3 AND
    mezze >= 1`, ottenibile tenendole tutte sullo stesso giorno). La
    collocazione forzata qui — due libere sul giorno 1 e una sul giorno 2 —
    non e' ne' l'una ne' l'altra: due giorni liberi e due mezze libere.

    Con due booleani **indipendenti** ciascuna soglia degraderebbe da sola a
    `>= min(soglia, B)`, cioe' `giorni >= 1` e `mezze >= 1`, e quella
    collocazione passerebbe. E' la mutazione che questo test intercetta."""
    env = mini_school()
    for slot in (0, 4):
        place(env["schedule"], _congelata(env), day=0, slot=slot)
    libere = [_libera(env) for _ in range(3)]
    for i, act in enumerate(libere):
        place(env["schedule"], act, day=1, slot=i)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 1, "free_half_days": 3})

    assert _baseline_viola(env["schedule"], "free_guaranteed")
    # lo status quo (tutte e tre sullo stesso giorno) resta ammesso
    assert _stato_forzando(
        env["schedule"],
        [(libere[0], (1, 0)), (libere[1], (1, 1)), (libere[2], (1, 2))]
    ) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # la via di mezzo — ne' riparata ne' conservata — no
    assert _stato_forzando(
        env["schedule"],
        [(libere[0], (1, 0)), (libere[1], (1, 1)), (libere[2], (2, 0))]
    ) == cp_model.INFEASIBLE


def test_free_guaranteed_status_quo_non_rappresentabile_non_blocca():
    """Il caveat sollevato dalla review, verificato invece che assunto: il
    ramo «non peggiorare» chiede di conservare il valore che la quantita' ha
    **adesso**, e quel valore e' riproducibile nel modello solo se ogni
    libera puo' restare dov'e'. Puo' non esserlo: un pre-filtro strutturale
    (qui l'indisponibilita' rossa) toglie dal dominio la cella dove la libera
    si trova in questo momento.

    Griglia 5x6, un docente. Tre congelate occupano i giorni 0, 1 e 2; la
    libera e' piazzata su (0, 1); tutte le fasce dei giorni 0, 1 e 2 sono
    indisponibili **in rosso** per il docente, quindi la libera puo' andare
    solo sui giorni 3 e 4 — e la sua cella attuale non esiste piu' nel
    modello. La baseline del checker viola comunque (`free_days = 2` contro
    `free_days=3`) e le congelate ci sono, quindi si passerebbe dal ramo
    status quo: `B = 2` chiederebbe che **entrambi** i giorni 3 e 4 restino
    liberi, cioe' che la libera stia sui giorni 0-2 — dove non puo' andare.
    INFEASIBLE per colpa del passato, di nuovo.

    Con la guardia di rappresentabilita' il ramo scende a zero, resta vacuo,
    e il modello e' fattibile. E' la mutazione «rappresentabilita' ignorata»
    del criterio di mutazione."""
    env = mini_school()
    for day in range(3):
        place(env["schedule"], _congelata(env), day=day, slot=0)
    libera = _libera(env)
    place(env["schedule"], libera, day=0, slot=1)
    for day in range(3):
        for slot in range(env["grid"].slots_per_day):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.FREE_GUARANTEED,
        params={"free_days": 3})

    assert _baseline_viola(env["schedule"], "free_guaranteed")
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id][0] in (3, 4)



def test_min_distribution_status_quo_non_rappresentabile_non_blocca():
    """L'analogo su MIN_DISTRIBUTION del caveat gia' difeso per
    FREE_GUARANTEED, e la ragione per cui `B` si calcola su
    `_giorni_garantiti` e non su `ScheduleState.resource_days`.

    ⚠ La distinzione era **scoperta**: sostituendo `_giorni_garantiti` con
    `resource_days` la suite di questo file restava verde. E' la stessa forma
    della Ruling 119 — il codice fa una distinzione, nessun test la afferma —
    quindi ci vuole un'istanza dove le due danno un `B` diverso e uno dei due
    non e' raggiungibile.

    Griglia 5x6, un docente. Una congelata su (0, 0), una libera piazzata su
    (1, 0), e i giorni 1-4 **interamente** indisponibili in rosso: la libera
    puo' andare solo sul giorno 0, e la sua cella attuale non esiste piu' nel
    modello. `min_days=3` e' irraggiungibile comunque, quindi si passa dal
    ramo status quo, e li' le due letture divergono:

    - `_giorni_garantiti` scarta la libera (cella fuori dominio) e conta **un**
      giorno qualificante. `>= 1` e' vero per costruzione: fattibile.
    - `resource_days` conta anche la libera dov'e' adesso, cioe' **due**
      giorni. Ma il massimo raggiungibile e' uno — congelata e libera finiscono
      entrambe sul giorno 0 — quindi `>= 2` e' una **pretesa sul passato**:
      INFEASIBLE, esattamente cio' che ADR-018 vieta.
    """
    env = mini_school()
    _congelata(env)
    place(env["schedule"], Activity.objects.last(), day=0, slot=0)
    libera = _libera(env)
    place(env["schedule"], libera, day=1, slot=0)
    for day in range(1, env["grid"].days_per_cycle):
        for slot in range(env["grid"].slots_per_day):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})

    assert _baseline_viola(env["schedule"], "min_distribution")
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[libera.id][0] == 0
