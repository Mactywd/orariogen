"""La copertura è un predicato **per alunno**, e un alunno non è una parte.

`structural:coverage` confronta il monte ore delle attività con i servizi del
piano. L'atteso è il piano **intero**, cioè il curriculum di *un* alunno: la
lettura è giusta, l'unità no. Un alunno sta in una **combinazione** di parti —
una per partizione — che è l'**atomo** di ADR-017, e il piano di classe è un
**catalogo**, non un curriculum: contiene righe che nessun singolo alunno deve
tutte (IRC e alternativa: ogni classe italiana).

Due difetti distinti, che qui si tengono fermi separatamente:

- **il lato osservato** — con due partizioni le ore ricevute attraverso l'altra
  partizione non entrano nel conteggio della parte. Si chiude portando l'unità
  sull'atomo, che `activity_tokens` marca già;
- **il lato atteso** — le righe in alternativa vanno dichiarate tali. È il dato
  che EDT porta come `MS` (`Modalité d'élection`, `R` = Religioso).

Vedi ADR-020 e `tests/test_classe_articolata.py`, che tiene fermo il caso IRC
**non** dichiarato.
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


def _servizio(plan, subject, minutes, **extra):
    Service.objects.update_or_create(
        study_plan=plan, subject=subject,
        defaults={"class_minutes": minutes, **extra})


def _materia(env, code, name):
    return Subject.objects.create(code=code, name=name,
                                  discipline=env["discipline"])


def _hard(schedule):
    return [f for f in check_schedule(schedule) if f.severity == Severity.HARD]


def _sdoppiata():
    """Due partizioni indipendenti sulla stessa classe: lingua e laboratorio,
    ognuna sdoppiata in due parti che ricevono la **stessa** materia. È lo
    sdoppiamento vero, non l'articolazione: il piano di classe basta e avanza,
    e nessuna riga è in alternativa. Ogni alunno riceve ITA + ING + LAB."""
    env = mini_school(days=2, slots=2)
    klass, piano = env["klass"], env["plan"]
    lingua = ClassPartition.objects.create(school_class=klass, name="LINGUA")
    lab = ClassPartition.objects.create(school_class=klass, name="LAB")
    l1 = ClassPart.objects.create(name="1A_L1", partition=lingua)
    l2 = ClassPart.objects.create(name="1A_L2", partition=lingua)
    b1 = ClassPart.objects.create(name="1A_B1", partition=lab)
    b2 = ClassPart.objects.create(name="1A_B2", partition=lab)

    ing = _materia(env, "ING", "Inglese")
    laboratorio = _materia(env, "LAB", "Laboratorio")
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[klass],
                  slots=1)
    make_activity(ing, teachers=[_docente("Bianchi")], parts=[l1], slots=1)
    make_activity(ing, teachers=[_docente("Verdi")], parts=[l2], slots=1)
    make_activity(laboratorio, teachers=[_docente("Neri")], parts=[b1], slots=1)
    make_activity(laboratorio, teachers=[_docente("Gialli")], parts=[b2],
                  slots=1)

    Service.objects.all().delete()
    _servizio(piano, env["subject"], 60)
    _servizio(piano, ing, 60)
    _servizio(piano, laboratorio, 60)
    env.update(l1=l1, l2=l2, b1=b1, b2=b2, lingua=lingua, lab=lab)
    return env


@pytest.mark.django_db
def test_la_copertura_conta_le_ore_ricevute_dall_altra_partizione():
    """Il difetto del **lato osservato**, nella forma più ordinaria che ci sia:
    una classe sdoppiata due volte. L'alunno della parte `1A_L1` fa anche
    laboratorio, ma l'attività di laboratorio è dichiarata sulla parte `1A_B1`,
    che non porta la chiave di `1A_L1`: misurando per parte le ore
    dell'**altra** partizione spariscono, e ogni parte risulta debitrice di
    tutto ciò che riceve attraverso l'altra divisione. Misurando per atomo
    quadra, e senza un dato nuovo: `activity_tokens` marca già gli atomi."""
    env = _sdoppiata()
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])
    scostamenti = [f for f in _hard(env["schedule"])
                   if f.code == "coverage_mismatch"]
    assert scostamenti == []


def _irc(alternativa_su_parte=True, sulla_classe=False):
    """La classe italiana normale: una partizione, due parti, IRC e attività
    alternativa. Il piano di classe dichiara **entrambe** le righe, come fa il
    quadro orario di una scuola vera, e le due sono in **alternativa**: un
    alunno ne segue esattamente una."""
    env = mini_school(days=2, slots=2)
    klass, piano = env["klass"], env["plan"]
    partizione = ClassPartition.objects.create(school_class=klass, name="IRC")
    p_rel = ClassPart.objects.create(name="1A_REL", partition=partizione)
    p_alt = ClassPart.objects.create(name="1A_ALT", partition=partizione)

    religione = _materia(env, "REL", "Religione")
    alternativa = _materia(env, "ALT", "Alternativa")
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[klass],
                  slots=1)
    make_activity(religione, teachers=[_docente("Neri")],
                  classes=[klass] if sulla_classe else (),
                  parts=() if sulla_classe else [p_rel], slots=1)
    if alternativa_su_parte or sulla_classe:
        make_activity(alternativa, teachers=[_docente("Gialli")],
                      classes=[klass] if sulla_classe else (),
                      parts=() if sulla_classe else [p_alt], slots=1)

    Service.objects.all().delete()
    _servizio(piano, env["subject"], 60)
    _servizio(piano, religione, 60, election_group="IRC")
    _servizio(piano, alternativa, 60, election_group="IRC")
    env.update(p_rel=p_rel, p_alt=p_alt, religione=religione,
               alternativa=alternativa)
    return env


@pytest.mark.django_db
def test_l_elezione_dichiarata_toglie_lo_scostamento_di_irc():
    """Il difetto del **lato atteso**, chiuso dal dato che lo dichiara. Il
    piano è un catalogo: contiene REL e ALT perché la classe le riceve
    entrambe, ma nessun alunno le deve entrambe. Con le due righe dichiarate
    in alternativa, chi fa religione smette di risultare debitore dell'ora di
    alternativa."""
    env = _irc()
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])
    assert [f for f in _hard(env["schedule"])
            if f.code in ("coverage_mismatch", "election_mismatch")] == []


@pytest.mark.django_db
def test_chi_non_segue_nessuna_alternativa_e_uno_scostamento():
    """L'elezione non è un condono: dichiarare due righe in alternativa non
    autorizza a non seguirne nessuna. È l'errore vero della scuola che si
    dimentica l'attività alternativa, e va nominato — con il **gruppo**, non
    con una delle due materie, perché quale delle due manchi non è deciso."""
    env = _irc(alternativa_su_parte=False)
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    apply(soluzione, env["schedule"])
    elezioni = [f for f in _hard(env["schedule"]) if f.code == "election_mismatch"]
    assert len(elezioni) == 1
    assert elezioni[0].resources == (env["p_alt"].pk,)
    assert elezioni[0].quantities["followed"] == 0


@pytest.mark.django_db
def test_chi_segue_due_alternative_e_uno_scostamento():
    """L'altro verso, ed è l'errore di dato più facile da commettere: le due
    attività dichiarate sulla **classe** invece che sulle parti. A classe
    intera le seguono tutti, quindi ogni parte ne segue due, e nessuna delle
    due è sbagliata di suo: a essere sbagliata è la coppia."""
    env = _irc(sulla_classe=True)
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    apply(soluzione, env["schedule"])
    elezioni = [f for f in _hard(env["schedule"]) if f.code == "election_mismatch"]
    assert len(elezioni) == 2
    assert {f.resources[0] for f in elezioni} == {env["p_rel"].pk, env["p_alt"].pk}
    assert {f.quantities["followed"] for f in elezioni} == {2}


@pytest.mark.django_db
def test_due_gruppi_di_elezione_insoddisfatti_sono_due_verdetti():
    """⚠ La trappola documentata in `Finding.key`: il messaggio è fuori dalla
    chiave, quindi **tutto ciò che distingue due verdetti dev'essere un
    campo**. Due gruppi in alternativa entrambi insoddisfatti sulla stessa
    unità hanno causale, risorsa e quantità identiche: senza il gruppo come
    campo collasserebbero in uno, e la diagnosi ne nominerebbe uno solo — con
    quale dei due sopravvive deciso dall'ordine di iterazione."""
    env = _irc(alternativa_su_parte=False)
    seconda = _materia(env, "FRA", "Francese")
    terza = _materia(env, "SPA", "Spagnolo")
    _servizio(env["plan"], seconda, 60, election_group="LINGUA2")
    _servizio(env["plan"], terza, 60, election_group="LINGUA2")

    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    apply(soluzione, env["schedule"])
    elezioni = [f for f in _hard(env["schedule"])
                if f.code == "election_mismatch" and f.resources == (env["p_alt"].pk,)]
    assert len(elezioni) == 2
    assert {f.group for f in elezioni} == {"IRC", "LINGUA2"}


def _articolata_con_irc():
    """La 3A articolata **con** IRC: due partizioni indipendenti, quattro
    atomi. È la classe su cui il todo aveva misurato **quattro** scostamenti
    inesistenti, ed è la composizione dei due difetti in una sola istanza —
    l'articolazione porta il piano proprio, IRC porta l'alternativa."""
    env = mini_school(days=2, slots=2)
    klass, man = env["klass"], env["plan"]
    ele = StudyPlan.objects.create(code="ELE3", name="Elettronica 3", year=3)
    art = ClassPartition.objects.create(school_class=klass, name="Articolazione")
    p_man = ClassPart.objects.create(name="3A_MAN", partition=art)
    p_ele = ClassPart.objects.create(name="3A_ELE", partition=art, study_plan=ele)
    irc = ClassPartition.objects.create(school_class=klass, name="IRC")
    p_rel = ClassPart.objects.create(name="3A_REL", partition=irc)
    p_alt = ClassPart.objects.create(name="3A_ALT", partition=irc)

    ita = env["subject"]
    t_man = _materia(env, "TMAN", "Tecnologie MAN")
    t_ele = _materia(env, "TELE", "Tecnologie ELE")
    religione = _materia(env, "REL", "Religione")
    alternativa = _materia(env, "ALT", "Alternativa")
    make_activity(ita, teachers=[env["teacher"]], classes=[klass], slots=1)
    make_activity(t_man, teachers=[_docente("Bianchi")], parts=[p_man], slots=1)
    make_activity(t_ele, teachers=[_docente("Verdi")], parts=[p_ele], slots=1)
    make_activity(religione, teachers=[_docente("Neri")], parts=[p_rel], slots=1)
    make_activity(alternativa, teachers=[_docente("Gialli")], parts=[p_alt],
                  slots=1)

    Service.objects.all().delete()
    for piano, propria in ((man, t_man), (ele, t_ele)):
        _servizio(piano, ita, 60)          # l'ora comune sta in entrambi
        _servizio(piano, propria, 60)
        _servizio(piano, religione, 60, election_group="IRC")
        _servizio(piano, alternativa, 60, election_group="IRC")
    env.update(man=man, ele=ele, p_man=p_man, p_ele=p_ele, p_rel=p_rel,
               p_alt=p_alt)
    return env


@pytest.mark.django_db
def test_l_articolata_con_irc_quadra_su_tutti_e_quattro_gli_atomi():
    """I due difetti insieme, sulla classe che li porta entrambi. Ogni alunno
    è una coppia (articolazione × IRC): il suo piano è quello dichiarato dalla
    parte che lo dichiara, e delle due righe in alternativa ne deve una."""
    env = _articolata_con_irc()
    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])
    assert [f for f in _hard(env["schedule"])
            if f.code in ("coverage_mismatch", "election_mismatch")] == []


@pytest.mark.django_db
def test_due_piani_propri_nella_stessa_combinazione_sono_un_errore_di_dato():
    """⚠ Il limite del piano risolto per atomo, e la ragione per cui i piani
    non si fondono: se **due** parti della stessa combinazione dichiarano
    piani diversi, quale sia il curriculum dell'alunno non è deciso da nessun
    dato. Unirli inventerebbe il campo che ADR-017 ha rifiutato di creare, e
    sceglierne uno in silenzio sarebbe peggio: si nomina l'errore, e quella
    unità non si misura."""
    env = mini_school(days=2, slots=2)
    klass = env["klass"]
    art = ClassPartition.objects.create(school_class=klass, name="Articolazione")
    lingua = ClassPartition.objects.create(school_class=klass, name="Lingua")
    for nome, partizione in (("3A_MAN", art), ("3A_ELE", art),
                             ("3A_FRA", lingua), ("3A_TED", lingua)):
        ClassPart.objects.create(
            name=nome, partition=partizione,
            study_plan=StudyPlan.objects.create(code=nome, name=nome, year=3))

    findings = _hard(env["schedule"])
    ambigui = [f for f in findings if f.code == "ambiguous_study_plan"]
    assert len(ambigui) == 4        # i quattro atomi, ognuno con due piani
    assert all(str(f.resources[0]).startswith("atom:") for f in ambigui)
    assert {f.quantities["plans"] for f in ambigui} == {2}
    # l'unità ambigua non si misura: nessun verdetto di copertura su di essa
    assert [f for f in findings if f.code == "coverage_mismatch"] == []
