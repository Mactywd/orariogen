"""La classe articolata retta dalle parti — **condizione 3 di ADR-015**.

`scope-v1.md` copre la classe articolata (la 3A con 12 alunni di Manutenzione e
10 di Elettronica) senza entità dedicata: *«la parte A segue un piano, la parte
B un altro, le ore comuni si insegnano a classe intera»*. La scorciatoia regge
**solo se** una parte può portare un piano di studi proprio, e il documento lo
dice per esteso: *«da verificare presto, non a modello finito»*.

Qui si verifica, e la risposta è in due metà.

🔑 **La prima metà tiene, ed è misurata invece che dichiarata.** Il piano
proprio esiste (`ClassPart.study_plan`, `NULL` = eredita), la **copertura lo
legge** (`state.student_units` porta il piano effettivo di ogni parte), le due
articolazioni **stanno nella stessa fascia** — che è ciò che la scorciatoia
compra: parti della stessa partizione sono insiemi disgiunti di alunni, quindi
non confliggono — e l'ora comune a classe intera **occupa** entrambe le parti,
quindi nessuno può fare laboratorio mentre la classe fa italiano.

⚠ **La seconda metà non tiene, e non riguarda solo la classe articolata.**
L'unità della copertura è la **parte**, e l'atteso è il piano **intero** di
quella parte: è una lettura *per alunno*, ed è quella giusta. Ma un alunno non
sta in una parte, sta in una **combinazione** di parti — una per partizione — e
quella combinazione è l'**atomo** di ADR-017, che il modello già costruisce per
l'occupazione e non per il curriculum. Da cui il limite, tenuto fermo
dall'ultimo test di questo file: appena una classe ha **due** partizioni — o
anche una sola, se le due parti ricevono materie diverse, cioè IRC e
alternativa: la configurazione di **ogni** classe italiana — la copertura
produce scostamenti che non esistono.

Nessuno se n'era accorto perché il Fermi **non ha nessuna partizione**, e
`test_beyond_fermi.py` le costruisce senza mai chiamare `check_schedule`: la
forma di sempre, una proprietà del dataset scambiata per una proprietà del
codice.
"""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (ClassPart, ClassPartition, Service, StudyPlan,
                           Subject, Teacher)
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school


def _docente(nome):
    return Teacher.objects.create(name=nome, last_name=nome, first_name=nome)


def _servizio(plan, subject, minutes):
    Service.objects.update_or_create(study_plan=plan, subject=subject,
                                     defaults={"class_minutes": minutes})


def _articolata(days=2, slots=2):
    """La 3A articolata: una partizione, due parti, un piano per ciascuna, e le
    ore comuni dichiarate **in entrambi i piani** perché sono ore che entrambe
    le popolazioni di alunni ricevono."""
    env = mini_school(days=days, slots=slots)
    man, klass = env["plan"], env["klass"]
    ele = StudyPlan.objects.create(code="ELE3", name="Elettronica 3", year=3)
    partizione = ClassPartition.objects.create(school_class=klass,
                                               name="Articolazione")
    p_man = ClassPart.objects.create(name="3A_MAN", partition=partizione)
    p_ele = ClassPart.objects.create(name="3A_ELE", partition=partizione,
                                     study_plan=ele)

    ita = env["subject"]
    t_man = Subject.objects.create(code="TMAN", name="Tecnologie MAN",
                                   discipline=env["discipline"])
    t_ele = Subject.objects.create(code="TELE", name="Tecnologie ELE",
                                   discipline=env["discipline"])

    env["a_com"] = make_activity(ita, teachers=[env["teacher"]],
                                 classes=[klass], slots=1)
    env["a_man"] = make_activity(t_man, teachers=[_docente("Bianchi")],
                                 parts=[p_man], slots=1)
    env["a_ele"] = make_activity(t_ele, teachers=[_docente("Verdi")],
                                 parts=[p_ele], slots=1)

    Service.objects.all().delete()
    _servizio(man, ita, 60)
    _servizio(ele, ita, 60)      # l'ora comune sta in **entrambi** i piani
    _servizio(man, t_man, 60)
    _servizio(ele, t_ele, 60)

    env.update(man=man, ele=ele, p_man=p_man, p_ele=p_ele)
    return env


def _hard(schedule):
    return [f for f in check_schedule(schedule) if f.severity == Severity.HARD]


@pytest.mark.django_db
def test_la_copertura_misura_ogni_parte_sul_proprio_piano():
    """La condizione 3 nella sua forma diretta: due piani sulla stessa classe,
    e la copertura quadra su entrambi."""
    env = _articolata()
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])
    assert _hard(env["schedule"]) == []


@pytest.mark.django_db
def test_senza_piano_proprio_l_articolazione_non_quadra():
    """La stessa istanza con la parte che **eredita** invece di portare il
    proprio piano. È il controfattuale che rende la condizione 3 portante: se
    il quadro orario restasse agganciato alla sola classe, la scorciatoia
    decadrebbe — e questo è l'aspetto che avrebbe."""
    env = _articolata()
    parte = env["p_ele"]
    parte.study_plan = None
    parte.save()

    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    apply(soluzione, env["schedule"])
    scostamenti = [f for f in _hard(env["schedule"])
                   if f.code == "coverage_mismatch"]
    # la parte ELE risulta debitrice delle ore di Manutenzione che non fa, e
    # creditrice delle proprie che il piano di classe non dichiara
    assert {f.quantities["expected_minutes"] for f in scostamenti} == {0, 60}
    assert len(scostamenti) == 2


@pytest.mark.django_db
def test_le_due_articolazioni_stanno_nella_stessa_fascia():
    """Ciò che la scorciatoia **compra**: parti della stessa partizione sono
    insiemi disgiunti di alunni, quindi le due specializzazioni sono
    simultanee. L'istanza lo forza per aritmetica — tre attività, due celle —
    così che un modello in cui le parti confliggono risponda `INFEASIBLE`
    invece di scegliere per caso una collocazione diversa."""
    env = _articolata(days=1, slots=2)
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "OPTIMAL"
    assert (soluzione.placements[env["a_man"].pk]
            == soluzione.placements[env["a_ele"].pk])
    assert soluzione.placements[env["a_com"].pk] != soluzione.placements[env["a_man"].pk]


@pytest.mark.django_db
def test_l_ora_comune_a_classe_intera_occupa_le_parti():
    """E ciò che la scorciatoia **non** deve concedere: nessuno fa laboratorio
    mentre la sua classe fa italiano. Si forza la violazione e si attende
    `INFEASIBLE`, che è la forma della casa — «risolvi e guarda dove è finita»
    non dimostrerebbe che il vincolo morde."""
    env = _articolata()
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False,
                      pinned={env["a_com"].pk: (0, 0), env["a_man"].pk: (0, 0)})
    assert soluzione.status == "INFEASIBLE"


@pytest.mark.django_db
def test_l_unita_della_copertura_e_la_parte_dove_dovrebbe_essere_l_atomo():
    """⚠ Il limite, tenuto fermo perché chi lo toglie debba prima cancellare
    questo test e leggerne il perché.

    L'istanza è la classe italiana **normale**: nessuna articolazione, solo IRC
    e alternativa — due parti della stessa partizione che ricevono materie
    diverse. Il piano di classe dichiara entrambe le materie, come fa il quadro
    orario di una scuola vera, e la copertura produce **due scostamenti che non
    esistono**: chi fa religione risulta debitore dell'ora di alternativa, e
    viceversa.

    🔑 La causa non è la misura ma l'**unità**. L'atteso è il piano intero
    della parte, cioè il curriculum di *un alunno*: lettura giusta, unità
    sbagliata, perché un alunno sta in una **combinazione** di parti — una per
    partizione — e quella combinazione è l'**atomo** di ADR-017. Con una sola
    partizione parte e atomo coincidono, ed è per questo che
    `test_la_copertura_misura_ogni_parte_sul_proprio_piano` qui sopra è verde:
    là le due parti hanno curriculum diversi *e* piani diversi.

    ⚠ Una scappatoia esiste ed è misurata: dare a `1A_ALT` un piano **gemello**
    del piano di classe, identico salvo ALT al posto di REL, azzera i finding.
    Ma costa un `StudyPlan` per ogni combinazione — quattro per una 3A
    articolata con IRC — cioè materializzare gli atomi come anagrafica, che è
    ciò che ADR-017 ha deciso di **non** fare per l'occupazione.

    Alternative, entrambe da decidere e nessuna da indovinare qui: portare la
    copertura sull'atomo, oppure leggere il monte ore **tripartito** del
    servizio (`reduced_minutes`, `split_minutes` — nello schema dal primo
    giorno, ⚠ letti da **nessuno**), che è la risposta di EDT alla stessa
    domanda ma la cui semantica non è mai stata osservata in UI
    (`docs/edt/piani-di-studi.md` la elenca fra le cose da osservare)."""
    env = mini_school(days=2, slots=2)
    klass, piano = env["klass"], env["plan"]
    partizione = ClassPartition.objects.create(school_class=klass, name="IRC")
    p_rel = ClassPart.objects.create(name="1A_REL", partition=partizione)
    p_alt = ClassPart.objects.create(name="1A_ALT", partition=partizione)
    assert p_rel.effective_study_plan == p_alt.effective_study_plan

    religione = Subject.objects.create(code="REL", name="Religione",
                                       discipline=env["discipline"])
    alternativa = Subject.objects.create(code="ALT", name="Alternativa",
                                         discipline=env["discipline"])
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[klass], slots=1)
    make_activity(religione, teachers=[_docente("Neri")], parts=[p_rel], slots=1)
    make_activity(alternativa, teachers=[_docente("Gialli")], parts=[p_alt],
                  slots=1)

    Service.objects.all().delete()
    _servizio(piano, env["subject"], 60)
    _servizio(piano, religione, 60)
    _servizio(piano, alternativa, 60)

    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    apply(soluzione, env["schedule"])
    scostamenti = [f for f in _hard(env["schedule"])
                   if f.code == "coverage_mismatch"]
    print('DUMP', [(f.resources, f.message, f.quantities) for f in scostamenti])
    assert len(scostamenti) == 2
    assert {f.resources[0] for f in scostamenti} == {p_rel.pk, p_alt.pk}
    # ⚠ Ognuno è debitore dell'ora dell'altro: il numero atteso è 60 e quello
    # osservato 0, su una scuola in cui entrambe le ore si fanno davvero.
    assert all(f.quantities == {"expected_minutes": 60, "actual_minutes": 0}
               for f in scostamenti)
