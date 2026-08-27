"""Il criterio di riuscita: solve → apply → check_schedule → zero HARD nelle
famiglie modellate. Il registro dei predicati e' l'oracolo del solver: le due
facce sono state scritte dai lati opposti dello stesso dato.

Dal Task 17 le famiglie sono **ventisei**, non le cinque dello spike: vedi
`CODICI` qui sotto e la guardia che gli impedisce di invecchiare."""
import datetime as dt

import pytest

from domain import weeks
from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.models import (
    Break, ClassPart, ClassPartition, Discipline, Extraction, Period,
    Placement, ResourceTimeConstraint, ResourceUnavailability, Schedule,
    SchoolClass, SchoolYear, StudyPlan, Subject, SubjectConstraint, Teacher,
    TimeGrid,
)
from domain.solver.model import apply, solve
from tests import fermi
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

# Le causali di **tutte** le ventisei famiglie modellate. Fino al Task 16
# questo insieme elencava le sole cinque dello spike, e l'oracolo del Fermi
# era percio' cieco su ventuno famiglie su ventisei: un `check_schedule` che
# gira su tutto ma di cui si guardava un ventesimo.
CODICI = {
    # strutturali
    "resource_occupied", "resource_occupied_locked", "resource_peak",
    "unavailability",
    "slot_out_of_grid", "break_straddled", "holiday",
    "site_transition",
    "weight_day", "weight_morning", "weight_afternoon", "weight_week",
    # orari sulla risorsa
    "min_distribution", "max_hours_day", "max_hours_morning",
    "max_hours_afternoon", "max_presence", "max_presence_days",
    "arrival_departure", "free_guaranteed", "max_half_days", "only_half_day",
    "max_site_changes", "max_gap",
    # di materia
    "subject_same_half_day", "subject_same_day", "subject_two_days",
    "subject_forbidden_sequence", "subject_max_hours_half_day",
    "subject_max_hours_day", "subject_weekly_order",
    "subject_imposed_succession", "subject_half_day_gap",
    "subject_parts_order",
    # lo scarto: il solver lo decide, quindi l'oracolo lo sorveglia. Un
    # piazzamento che c'era nella baseline e che il solve ha rinunciato a
    # tenere e' un finding **nuovo**, e va visto.
    "activity_unplaced",
}

# La legalita' di cio' che **e' piazzato**, separata dalla completezza
# dell'orario. Un'attivita' fuori dall'estrazione, o che il solver ha
# rinunciato a piazzare, non e' un'illegalita': e' un buco. I test che
# pretendono un orario *legale* usano questo insieme; il confronto
# differenziale di `nuove()` resta su CODICI, dove uno scarto **nuovo** —
# qualcosa che era piazzato e non lo e' piu' — deve vedersi.
LEGALITA = CODICI - {"activity_unplaced"}

# Le tre causali del catalogo che restano **deliberatamente** fuori.
FUORI = {
    # nessun builder: PLACEMENT_INDEPENDENT, il solver non crea ne' distrugge
    # attivita' (vedi tests/test_solver_registry_completo.py)
    "coverage_mismatch",
    # non sono HARD: violazioni() le filtrerebbe comunque per severita', ma
    # elencarle qui rende la scelta leggibile invece che implicita
    "unavailability_optional", "preference",
}


def test_codici_copre_tutto_il_catalogo():
    """La guardia contro la deriva: una causale nuova in
    `domain/analysis/causali.py` deve finire in CODICI oppure in FUORI, per
    decisione esplicita. Senza questo test l'insieme invecchia in silenzio —
    ed e' esattamente quello che gli e' successo per ventuno famiglie."""
    from domain.analysis import causali
    assert set(causali.CAUSALI) == CODICI | FUORI


def violazioni(schedule, codici=CODICI):
    """L'insieme delle (chiave, settimana) dei finding HARD nelle famiglie
    modellate. Un insieme, non una lista: il criterio di riuscita e' il
    **contenimento** (ADR-018), non l'uguaglianza.

    Espanso per settimana invece di lasciare la sola chiave: `Finding.key`
    esclude deliberatamente `weeks` (e' pensata per il dedup fra firme dentro
    check_schedule), quindi una violazione identica per codice/risorse/
    attivita'/quantita' ma comparsa su una firma diversa da quella di
    partenza si fonderebbe nello stesso finding e sparirebbe dal calcolo
    differenziale di `nuove()`. Espandere per settimana la rende visibile."""
    return {(f.key, w) for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici
            for w in f.weeks}


def nuove(schedule, prima, codici=CODICI):
    """I finding HARD comparsi **dopo** il solve. Il solver puo' anche
    riparare una violazione preesistente spostando un'attivita' libera: quello
    e' un successo, non una discrepanza, ed e' per questo che il criterio e'
    il contenimento e non l'uguaglianza."""
    return violazioni(schedule, codici) - prima


def _scuola_media():
    """Tre classi, tre docenti, tutte e cinque le famiglie attive. Dimensionata
    con margine: se risulta infattibile, il bug e' nella traduzione, non
    nell'istanza."""
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=4)
    italiano = env["subject"]
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    storia = Subject.objects.create(
        code="STO", name="Storia", discipline=env["discipline"])

    classi = [env["klass"]]
    for nome in ("1B", "1C"):
        classi.append(SchoolClass.objects.create(
            name=nome, study_plan=env["plan"], year=1))

    docenti = {"ITA": env["teacher"]}
    for codice, cognome, nome in (("MAT", "Bruni", "Ivo"), ("STO", "Sala", "Rita")):
        docenti[codice] = Teacher.objects.create(
            name=f"{cognome} {nome}", last_name=cognome, first_name=nome)

    # due partizioni su 1A: gli atomi di ADR-017 entrano nel modello
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)

    ita_activities = []
    for classe in classi:
        for codice, materia in (("ITA", italiano), ("MAT", matematica), ("STO", storia)):
            for _ in range(2):
                att = make_activity(materia, teachers=[docenti[codice]], classes=[classe])
                if codice == "ITA":
                    ita_activities.append(att)
    make_activity(matematica, teachers=[docenti["MAT"]], classes=[classi[1]],
                  slots=2, respects_breaks=True)
    make_activity(italiano, parts=[rel])
    make_activity(italiano, parts=[ing])

    for fascia in range(6):
        ResourceUnavailability.objects.create(
            resource=docenti["STO"], day=4, slot=fascia, level="hard")
    for fascia in (1, 2):
        ResourceUnavailability.objects.create(
            resource=docenti["ITA"], day=0, slot=fascia, level="hard")
    ResourceTimeConstraint.objects.create(
        resource=docenti["ITA"], type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 240})
    SubjectConstraint.objects.create(
        subject_a=italiano, subject_b=italiano, school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    env["docenti"] = docenti
    env["ita_activities"] = ita_activities
    return env


def test_oracolo_sulla_scuola_media():
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()


def test_oracolo_sul_fermi_per_una_classe():
    """Le attivita' di 2A libere, tutto il resto fuori dal modello. 2A e' la
    classe che passa dal docente D09, indisponibile tre giorni su cinque."""
    dataset = fermi.build()
    classe = dataset["classes"]["2A"]
    estrazione = Extraction.objects.create(name="2A")
    estrazione.activities.set(classe.activities.all())
    soluzione = solve(dataset["schedule"], extraction=estrazione, time_limit=60)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert len(soluzione.placements) == classe.activities.count()
    apply(soluzione, dataset["schedule"])
    assert violazioni(dataset["schedule"], LEGALITA) == set()


def test_oracolo_puo_fallire():
    """L'oracolo deve poter fallire, non solo passare sempre. Senza questo
    test, un oracolo diventato vacuo — per esempio perche' l'insieme CODICI
    perde un codice, o un checker smette di essere registrato — passerebbe
    silenziosamente per sempre: gli altri test dell'oracolo continuerebbero a
    dare 'violazioni() == set()' anche se non stessero piu' verificando niente.
    Qui corrompiamo deliberatamente due Placement dopo un solve+apply andato a
    buon fine, e verifichiamo che violazioni() veda ciascuna corruzione con il
    codice atteso, in due famiglie diverse: occupazione (due attivita' dello
    stesso docente sulla stessa cella) e indisponibilita' (un'attivita'
    spostata su una fascia rossa)."""
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()

    ita = env["ita_activities"]  # [1A×2, 1B×2, 1C×2], stesso docente per tutte
    docente_ita = env["docenti"]["ITA"]

    # Famiglia "occupazione": due attivita' dello stesso docente (classi
    # diverse, 1A e 1B) forzate sulla stessa cella.
    p_a = Placement.objects.get(schedule=env["schedule"], activity=ita[0])
    p_b = Placement.objects.get(schedule=env["schedule"], activity=ita[2])
    giorno_orig, fascia_orig = p_b.day, p_b.start_slot
    p_b.day, p_b.start_slot = p_a.day, p_a.start_slot
    p_b.save()
    codici = {codice for (codice, *_), _settimana in violazioni(env["schedule"], LEGALITA)}
    assert "resource_occupied" in codici

    # Ripristino: la corruzione precedente non deve contaminare la successiva.
    p_b.day, p_b.start_slot = giorno_orig, fascia_orig
    p_b.save()
    assert violazioni(env["schedule"], LEGALITA) == set()

    # Famiglia "indisponibilita'": un'attivita' del docente ITA spostata sulla
    # fascia (giorno=0, fascia=1), dichiarata indisponibile hard per lui.
    assert ResourceUnavailability.objects.filter(
        resource=docente_ita, day=0, slot=1, level="hard").exists()
    p_a.day, p_a.start_slot = 0, 1
    p_a.save()
    codici = {codice for (codice, *_), _settimana in violazioni(env["schedule"], LEGALITA)}
    assert "unavailability" in codici


def _scuola_multi_firma():
    """Due settimane con firme diverse, per disciplinare la dimensione che il
    Fermi non esercita (una sola firma, tutto annuale). Un docente con
    D.T.B. = 0 sulla classe; due attivita' della prima settimana forzate da
    indisponibilita' **datate** su (giorno 0, fascia 0) e (giorno 0, fascia
    2); una terza attivita', libera, attiva solo nella seconda settimana.

    Per settimana l'istanza e' infattibile: il buco alla fascia 1 non e'
    colmabile da nessuna attivita' attiva in quella settimana (la terza
    attivita' non c'e' ancora). Un builder che trattasse tutte le attivita'
    come co-attive vedrebbe invece la terza attivita' come disponibile a
    riempire il buco, e dichiarerebbe OPTIMAL una soluzione che
    check_schedule rifiuta per la prima settimana — esattamente il difetto
    dimostrato in time_constraints.py."""
    grid = TimeGrid.objects.create(
        days_per_cycle=1, slots_per_day=3, slot_minutes=60, morning_end_slot=3)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    t1 = Teacher.objects.create(name="Uno Aldo", last_name="Uno", first_name="Aldo")
    t2 = Teacher.objects.create(name="Due Bice", last_name="Due", first_name="Bice")
    t3 = Teacher.objects.create(name="Tre Ciro", last_name="Tre", first_name="Ciro")

    prima_settimana = weeks.single_week(0)
    seconda_settimana = weeks.single_week(1)
    make_activity(subject, teachers=[t1], classes=[klass], mask=prima_settimana)
    make_activity(subject, teachers=[t2], classes=[klass], mask=prima_settimana)
    make_activity(subject, teachers=[t3], classes=[klass], mask=seconda_settimana)

    lunedi_prima_settimana = year.first_week_monday
    for fascia in (1, 2):
        ResourceUnavailability.objects.create(
            resource=t1, day=0, slot=fascia, level="hard", date=lunedi_prima_settimana)
    for fascia in (0, 1):
        ResourceUnavailability.objects.create(
            resource=t2, day=0, slot=fascia, level="hard", date=lunedi_prima_settimana)

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    return {"schedule": schedule}


def test_oracolo_su_istanza_multi_firma():
    """Il dataset Fermi ha un'unica firma di settimana (tutto annuale): questo
    test e' l'unico a esercitare davvero la dimensione «settimane». L'istanza
    e' costruita apposta per essere infattibile **per settimana** (il buco
    alla fascia 1 della prima settimana non e' colmabile da nessuna attivita'
    attiva in quella settimana): un builder corretto deve dichiararlo, non
    nasconderlo dietro un OPTIMAL che check_schedule rifiuterebbe.

    Prima della correzione, trattare tutte le attivita' come co-attive faceva
    apparire colmabile il buco con l'attivita' della seconda settimana: il
    solver rispondeva OPTIMAL, e check_schedule bocciava il piazzamento con
    un HARD max_gap — il fallimento che questo test scopre."""
    env = _scuola_multi_firma()
    # `allow_unplaced=False`: la domanda qui e' «il buco e' colmabile?», e con
    # lo scarto ammesso la risposta sarebbe «no, e allora rinuncio», che e'
    # un'altra domanda. Il modello che pretende il piazzamento e' quello in cui
    # l'infattibilita' e' la risposta.
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def _scuola_multi_firma_fattibile():
    """Due firme di settimana, e un'istanza che ha una soluzione **solo** se il
    modello le distingue. Griglia 2 giorni x 4 fasce, anno di due settimane.

    Il giorno 0 porta la dimensione D.T.B.: la classe non tollera buchi. Nella
    settimana 0 ci sono A2 — inchiodata alla fascia 0 dalle indisponibilita'
    del suo docente — e A1, libera; nella settimana 1 c'e' la sola A3,
    inchiodata alla fascia 3. Prese insieme, le tre occuperebbero {0, 3} piu'
    una fascia: un buco incolmabile su quattro fasce. Prese per firma, la
    settimana 0 chiude il buco mettendo A1 alla fascia 1, e la settimana 1 ha
    una fascia sola, che un buco non ce l'ha.

    Il giorno 1 porta la dimensione occupazione: A5 (settimana 0) e A6
    (settimana 1) condividono docente e classe e hanno entrambe una sola
    collocazione ammissibile, la stessa. Co-attive sarebbero un conflitto; non
    lo sono mai.

    Un modello che trattasse tutte le attivita' come co-attive risponderebbe
    quindi INFEASIBLE a un'istanza che una soluzione ce l'ha."""
    grid = TimeGrid.objects.create(
        days_per_cycle=2, slots_per_day=4, slot_minutes=60, morning_end_slot=4)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)

    docenti = {}
    for sigla, cognome, nome in (("T1", "Uno", "Aldo"), ("T2", "Due", "Bice"),
                                 ("T3", "Tre", "Ciro"), ("T5", "Cinque", "Ebe")):
        docenti[sigla] = Teacher.objects.create(
            name=f"{cognome} {nome}", last_name=cognome, first_name=nome)

    def solo_su(docente, cella):
        """Indisponibilita' ovunque tranne una cella: l'attivita' di quel
        docente ha un dominio di cardinalita' uno. **Ricorrenti**, non datate,
        cosi' le firme di settimana restano due e a distinguerle e' soltanto
        la maschera delle attivita'."""
        for d in range(grid.days_per_cycle):
            for s in range(grid.slots_per_day):
                if (d, s) != cella:
                    ResourceUnavailability.objects.create(
                        resource=docente, day=d, slot=s, level="hard")

    solo_su(docenti["T2"], (0, 0))
    solo_su(docenti["T3"], (0, 3))
    solo_su(docenti["T5"], (1, 0))

    prima, seconda = weeks.single_week(0), weeks.single_week(1)
    attivita = {
        "A1": make_activity(subject, teachers=[docenti["T1"]], classes=[klass], mask=prima),
        "A2": make_activity(subject, teachers=[docenti["T2"]], classes=[klass], mask=prima),
        "A3": make_activity(subject, teachers=[docenti["T3"]], classes=[klass], mask=seconda),
        "A5": make_activity(subject, teachers=[docenti["T5"]], classes=[klass], mask=prima),
        "A6": make_activity(subject, teachers=[docenti["T5"]], classes=[klass], mask=seconda),
    }

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    return {"schedule": schedule, "attivita": attivita}


def test_oracolo_su_istanza_multi_firma_fattibile():
    """L'altra meta' della dimensione «settimane»: non l'istanza infattibile
    che il solver deve rifiutare, ma una **fattibile** portata per intero lungo
    la catena solve -> apply -> check_schedule -> violazioni() == set().

    E' il caso che il criterio di riuscita dello spike descrive davvero, e che
    prima di questo test nessun banco di prova copriva: la scuola giocattolo,
    il Fermi per una classe e il Fermi intero hanno tutti **una sola** firma di
    settimana, perche' al Fermi ogni attivita' e' annuale. Da li' e' passato il
    difetto del D.T.B. trovato il 2026-08-24."""
    env = _scuola_multi_firma_fattibile()
    # se la fixture smettesse di avere due firme il test diventerebbe vacuo
    assert len(week_signatures(env["schedule"])) == 2

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert len(soluzione.placements) == len(env["attivita"])
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()

    # la prova diretta che le due firme non sono state fuse: due attivita' di
    # settimane diverse condividono docente, classe e collocazione
    celle = {
        nome: (p.day, p.start_slot)
        for nome, att in env["attivita"].items()
        for p in [Placement.objects.get(schedule=env["schedule"], activity=att)]
    }
    assert celle["A5"] == (1, 0)
    assert celle["A6"] == (1, 0)
    # e A1 ha dovuto chiudere il buco della settimana 0, non aprirne uno
    assert celle["A1"] in {(0, 1), (1, 1)}


def _due_settimane_stessa_violazione():
    """Fissa la semantica di nuove() sul caso della review: una violazione
    max_gap identica per codice/risorsa/quantita' su due settimane diverse.
    Non passa dal solver — e' costruita a mano con Placement diretti, perche'
    qui l'oggetto sotto esame e' l'helper del test, non il solver.

    Griglia 1 giorno x 3 fasce, MAX_GAP_HOURS = 0 sulla classe (qualunque
    buco e' una violazione). Settimana 0: due attivita' piazzate a fascia 0 e
    2, buco alla fascia 1 → un finding max_gap su 'klass', quantities
    {gap_minutes: 60, max_gap_minutes: 0}. Settimana 1: due attivita' attive
    ma non ancora piazzate → nessuna occupazione, nessun buco, nessuna
    violazione — finche' il chiamante non le piazza con lo stesso schema.

    MaxGapChecker (domain/analysis/checkers/time_constraints.py) costruisce
    il finding senza 'activities' nella chiave (solo resources e quantities):
    piazzando A3/A4 con lo stesso buco, il finding della settimana 1 ha
    esattamente la stessa Finding.key di quello della settimana 0, e
    check_schedule li fonde in un solo oggetto con weeks=(0, 1)."""
    grid = TimeGrid.objects.create(
        days_per_cycle=1, slots_per_day=3, slot_minutes=60, morning_end_slot=3)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")

    prima_settimana, seconda_settimana = weeks.single_week(0), weeks.single_week(1)
    a1 = make_activity(subject, teachers=[teacher], classes=[klass], mask=prima_settimana)
    a2 = make_activity(subject, teachers=[teacher], classes=[klass], mask=prima_settimana)
    a3 = make_activity(subject, teachers=[teacher], classes=[klass], mask=seconda_settimana)
    a4 = make_activity(subject, teachers=[teacher], classes=[klass], mask=seconda_settimana)

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    place(schedule, a1, day=0, slot=0)
    place(schedule, a2, day=0, slot=2)

    return {"schedule": schedule, "a3": a3, "a4": a4}


def test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana():
    """L'osservazione Important della review del Task 3: violazioni() riduce
    ogni finding alla sua Finding.key, che esclude 'weeks' per costruzione
    (e' pensata per il dedup fra firme dentro check_schedule). Senza
    l'espansione per settimana, una violazione preesistente in una firma e
    una identica — stesso codice/risorse/quantities — comparsa su un'altra
    firma si fondono in un solo finding con weeks allargato: la chiave era
    gia' in 'prima', quindi nuove() la perderebbe.

    Qui costruiamo esattamente quel caso: 'prima' cattura la violazione della
    settimana 0; poi piazziamo lo stesso schema di buco sulla settimana 1
    (stessa Finding.key, weeks diverso). Se nuove() operasse sulla sola
    chiave, il risultato sarebbe l'insieme vuoto — il finding "nuovo" e'
    identico a quello gia' visto. Con l'espansione per (chiave, settimana),
    nuove() deve vedere la settimana 1 come genuinamente nuova."""
    env = _due_settimane_stessa_violazione()
    schedule = env["schedule"]

    prima = violazioni(schedule, LEGALITA)
    assert len(prima) == 1
    (chiave, settimana), = prima
    assert chiave[0] == "max_gap"
    assert settimana == 0

    # stesso schema di buco, sulla settimana 1: stessa Finding.key di prima
    place(schedule, env["a3"], day=0, slot=0)
    place(schedule, env["a4"], day=0, slot=2)

    dopo = violazioni(schedule, LEGALITA)
    assert dopo == prima | {(chiave, 1)}

    trovate = nuove(schedule, prima, LEGALITA)
    assert trovate == {(chiave, 1)}


def test_fermi_intero_misurato():
    """Il Fermi ha le classi del triennio a 30 ore su una griglia di 30 fasce:
    non e' noto se sia fattibile. Qualunque cosa il solver restituisca, deve
    essere corretta — e le misure vanno riportate.

    ⚠⚠ **E qui la misura dice meno di quanto sembri, misurato al Task 17.** Il
    dataset Fermi ha **zero** righe `ResourceTimeConstraint`, **zero**
    `SubjectConstraint` e i quattro tetti di peso a `None`: delle ventisei
    famiglie modellate ne esercita **cinque** — griglia, indisponibilita' (42
    righe), occupazione, sedi e D.T.B. — e ventuno builder su ventisei non
    postano nulla. Il numero lo dimostrava: **8140 variabili e 1082
    constraint, identici a quelli dello spike a cinque vincoli** del
    2026-08-09, e lo stesso 0,56s.

    ⚠ Dal 2026-08-26 i numeri sono **8426 e 1086**, e la differenza e' tutta
    la macchina dello scarto e della catena, contata. Variabili: +284 booleani
    `piazzata` (uno per attivita' libera), +1 per i minuti scartati e +1 per il
    numero di attivita' scartate — i due livelli. Constraint: i 284
    `AddExactlyOne` diventano 284 `somma(celle) == piazzata` (netto zero), piu'
    le due uguaglianze dei livelli e i **due fissaggi** che la catena aggiunge
    percorrendola (`minuti <= v1`, `numero <= v2`). Il resto del modello e'
    identico a prima, ed e' la forma in cui «le quote a zero danno il modello
    di oggi» si vede su un dataset vero.

    Quindi «OPTIMAL sul Fermi col modello completo» **non e' una misura del
    modello completo**: e' una misura del dataset. La misura del modello sta
    in `tests/test_solver_witness.py::test_modello_completo`, dove ogni
    famiglia porta le proprie righe.

    Questo test resta per l'altra meta' — la scala. 284 attivita' su una
    griglia stretta sono il volume vero; il banco a testimone ne ha 14-32."""
    dataset = fermi.build()
    assert ResourceTimeConstraint.objects.count() == 0
    assert SubjectConstraint.objects.count() == 0
    soluzione = solve(dataset["schedule"], time_limit=120)
    print("\nFermi intero:", soluzione.status, soluzione.stats)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    if soluzione.status in ("OPTIMAL", "FEASIBLE"):
        assert soluzione.placements
        # Il Fermi si piazza per intero: nessuna rinuncia. Se un giorno
        # comparisse uno scarto qui, sarebbe la notizia — non un dettaglio.
        assert soluzione.stats["scartate"] == 0, soluzione.stats
        assert soluzione.stats["variabili"] == 8426
        assert soluzione.stats["constraint"] == 1086
        # i due livelli hanno concluso, e con l'ottimo dimostrato
        assert [l["nome"] for l in soluzione.stats["livelli"]] == [
            "minuti_scartati", "attivita_scartate"]
        assert all(l["ottimo"] and l["valore"] == 0
                   for l in soluzione.stats["livelli"])
        apply(soluzione, dataset["schedule"])
        assert violazioni(dataset["schedule"], LEGALITA) == set()
