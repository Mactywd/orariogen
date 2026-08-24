"""Il criterio di riuscita: solve → apply → check_schedule → zero HARD nelle
cinque famiglie modellate. Il registro dei predicati e' l'oracolo del solver:
le due facce sono state scritte dai lati opposti dello stesso dato."""
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
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db

# le causali delle cinque famiglie modellate, e solo quelle
CODICI = {
    "resource_occupied", "resource_occupied_locked", "resource_peak",   # occupazione
    "unavailability",                                                   # indisponibilita'
    "slot_out_of_grid", "break_straddled", "holiday",                   # griglia
    "max_gap",                                                          # D.T.B.
    "subject_same_day",                                                 # materia
}


def violazioni(schedule, codici=CODICI):
    """L'insieme delle chiavi dei finding HARD nelle famiglie modellate.
    Un insieme, non una lista: il criterio di riuscita e' il **contenimento**
    (ADR-018), non l'uguaglianza."""
    return {f.key for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici}


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
    assert violazioni(env["schedule"]) == set()


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
    assert violazioni(dataset["schedule"]) == set()


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
    assert violazioni(env["schedule"]) == set()

    ita = env["ita_activities"]  # [1A×2, 1B×2, 1C×2], stesso docente per tutte
    docente_ita = env["docenti"]["ITA"]

    # Famiglia "occupazione": due attivita' dello stesso docente (classi
    # diverse, 1A e 1B) forzate sulla stessa cella.
    p_a = Placement.objects.get(schedule=env["schedule"], activity=ita[0])
    p_b = Placement.objects.get(schedule=env["schedule"], activity=ita[2])
    giorno_orig, fascia_orig = p_b.day, p_b.start_slot
    p_b.day, p_b.start_slot = p_a.day, p_a.start_slot
    p_b.save()
    codici = {codice for codice, *_ in violazioni(env["schedule"])}
    assert "resource_occupied" in codici

    # Ripristino: la corruzione precedente non deve contaminare la successiva.
    p_b.day, p_b.start_slot = giorno_orig, fascia_orig
    p_b.save()
    assert violazioni(env["schedule"]) == set()

    # Famiglia "indisponibilita'": un'attivita' del docente ITA spostata sulla
    # fascia (giorno=0, fascia=1), dichiarata indisponibile hard per lui.
    assert ResourceUnavailability.objects.filter(
        resource=docente_ita, day=0, slot=1, level="hard").exists()
    p_a.day, p_a.start_slot = 0, 1
    p_a.save()
    codici = {codice for codice, *_ in violazioni(env["schedule"])}
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
    soluzione = solve(env["schedule"], time_limit=30)
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
    assert violazioni(env["schedule"]) == set()

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


def test_fermi_intero_misurato():
    """Il Fermi ha le classi del triennio a 30 ore su una griglia di 30 fasce:
    non e' noto se sia fattibile. Qualunque cosa il solver restituisca, deve
    essere corretta — e le misure vanno riportate."""
    dataset = fermi.build()
    soluzione = solve(dataset["schedule"], time_limit=120)
    print("\nFermi intero:", soluzione.status, soluzione.stats)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    if soluzione.status in ("OPTIMAL", "FEASIBLE"):
        assert soluzione.placements
        apply(soluzione, dataset["schedule"])
        assert violazioni(dataset["schedule"]) == set()
