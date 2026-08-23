"""Il criterio di riuscita: solve → apply → check_schedule → zero HARD nelle
cinque famiglie modellate. Il registro dei predicati e' l'oracolo del solver:
le due facce sono state scritte dai lati opposti dello stesso dato."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (
    Break, ClassPart, ClassPartition, Extraction, Placement,
    ResourceTimeConstraint, ResourceUnavailability, SchoolClass, Subject,
    SubjectConstraint, Teacher,
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


def violazioni(schedule):
    return [f for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in CODICI]


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
    assert violazioni(env["schedule"]) == []


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
    assert violazioni(dataset["schedule"]) == []


def test_oracolo_puo_fallire():
    """L'oracolo deve poter fallire, non solo passare sempre. Senza questo
    test, un oracolo diventato vacuo — per esempio perche' l'insieme CODICI
    perde un codice, o un checker smette di essere registrato — passerebbe
    silenziosamente per sempre: gli altri test dell'oracolo continuerebbero a
    dare 'violazioni() == []' anche se non stessero piu' verificando niente.
    Qui corrompiamo deliberatamente due Placement dopo un solve+apply andato a
    buon fine, e verifichiamo che violazioni() veda ciascuna corruzione con il
    codice atteso, in due famiglie diverse: occupazione (due attivita' dello
    stesso docente sulla stessa cella) e indisponibilita' (un'attivita'
    spostata su una fascia rossa)."""
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"]) == []

    ita = env["ita_activities"]  # [1A×2, 1B×2, 1C×2], stesso docente per tutte
    docente_ita = env["docenti"]["ITA"]

    # Famiglia "occupazione": due attivita' dello stesso docente (classi
    # diverse, 1A e 1B) forzate sulla stessa cella.
    p_a = Placement.objects.get(schedule=env["schedule"], activity=ita[0])
    p_b = Placement.objects.get(schedule=env["schedule"], activity=ita[2])
    giorno_orig, fascia_orig = p_b.day, p_b.start_slot
    p_b.day, p_b.start_slot = p_a.day, p_a.start_slot
    p_b.save()
    codici = {f.code for f in violazioni(env["schedule"])}
    assert "resource_occupied" in codici

    # Ripristino: la corruzione precedente non deve contaminare la successiva.
    p_b.day, p_b.start_slot = giorno_orig, fascia_orig
    p_b.save()
    assert violazioni(env["schedule"]) == []

    # Famiglia "indisponibilita'": un'attivita' del docente ITA spostata sulla
    # fascia (giorno=0, fascia=1), dichiarata indisponibile hard per lui.
    assert ResourceUnavailability.objects.filter(
        resource=docente_ita, day=0, slot=1, level="hard").exists()
    p_a.day, p_a.start_slot = 0, 1
    p_a.save()
    codici = {f.code for f in violazioni(env["schedule"])}
    assert "unavailability" in codici


def test_fermi_intero_misurato():
    """Il Fermi ha le classi del triennio a 30 ore su una griglia di 30 fasce:
    non e' noto se sia fattibile. Qualunque cosa il solver restituisca, deve
    essere corretta — e le misure vanno riportate."""
    dataset = fermi.build()
    soluzione = solve(dataset["schedule"], time_limit=120)
    print("\nFermi intero:", soluzione.status, soluzione.stats)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    if soluzione.placements:
        apply(soluzione, dataset["schedule"])
        assert violazioni(dataset["schedule"]) == []
