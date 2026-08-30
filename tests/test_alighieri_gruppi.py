"""L'ondata 2 dell'Alighieri: le quattro forme di sdoppiamento.

🔑 Sono la voce ✅ di scope v1 ([ADR-013](../docs/decisioni.md)) che **nessun
dataset rappresentava**: `ClassPartition`, `ClassPart` e `Group` erano tre
tabelle vuote, provate solo da fixture sintetiche di poche righe. Qui stanno
dentro una scuola intera, insieme, e ognuna ha una forma diversa dalle altre:

- **IRC / alternativa** su tutte e dodici le classi — due parti della stessa
  classe, con le due righe di piano dichiarate in alternativa (ADR-020);
- **la classe articolata** 2C — una parte con un **piano proprio** (la
  condizione 3 di ADR-015);
- **lo sdoppiamento a effettivo ridotto** in 3A — un'ora di laboratorio a metà
  classe, che il docente fa due volte;
- **il raggruppamento trasversale** ING1 su 1A e 1B — il caso che *rompe la
  decomposizione per classe*."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.state import AtomMap, activity_tokens
from domain.models import (Activity, ClassPart, Placement, StudyPlan,
                           TeachingAssignment)
from tests import alighieri

pytestmark = pytest.mark.django_db


@pytest.fixture
def dataset():
    env = alighieri.build()
    # 🔑 La **linea di partenza**, presa prima di piazzare qualsiasi cosa.
    # Dall'ondata 3 il dataset porta righe di vincolo, e due delle otto
    # famiglie sono *deficienze*: `min_distribution` e `free_guaranteed`
    # (`PLACEMENT_MONOTONE = False`) sono **massimamente violate a orario
    # vuoto** — zero giornate qualificanti, zero mezze giornate libere — e
    # piazzare le **ripara**. Chiedere loro qualcosa su un orario di tre
    # attività non significa niente, e non è ciò che questi test domandano.
    #
    # ⚠ Il confronto è sulla chiave **grossolana** `(causale, risorsa)` e non
    # sulla `Finding.key`: le quantità di una deficienza cambiano a ogni
    # piazzamento per costruzione, quindi una chiave fine direbbe «nuovo» a
    # ogni giro. È la stessa scelta dell'oracolo differenziale (ADR-018).
    env["partenza"] = {(f.code, f.resources) for f in check_schedule(env["schedule"])}
    return env


def _hard(env):
    return [f for f in check_schedule(env["schedule"])
            if f.severity == Severity.HARD and f.code != "activity_unplaced"
            and (f.code, f.resources) not in env["partenza"]]


def _attivita(subject_code, **filtri):
    return Activity.objects.filter(subject__code=subject_code, **filtri)


# ---------------------------------------------------------------- IRC / ALT

def test_irc_e_alternativa_sono_due_parti_non_due_gruppi(dataset):
    """`docs/edt/gruppi.md`: modellato come **due parti della stessa classe**,
    non come gruppi né come compresenza. Verificato sui dati."""
    for nome in dataset["classes"]:
        irc = _attivita("IRC", parts__name=f"{nome}_REL")
        alt = _attivita("ALT", parts__name=f"{nome}_ALT")
        assert irc.count() == 1 and alt.count() == 1, nome
        assert not irc.first().classes.exists()
        assert not irc.first().groups.exists()


def test_le_due_righe_in_alternativa_sono_dichiarate_tali(dataset):
    """🔑 ADR-020. Senza `election_group` la copertura darebbe **due
    scostamenti su ogni classe italiana**, ed è il comportamento giusto: che
    l'alunno ne segua una non è deducibile da nessuna proprietà dell'orario,
    è un dato."""
    for plan in StudyPlan.objects.all():
        elettive = {s.subject.code for s in plan.services.all()
                    if s.election_group == "RELIGIONE"}
        assert elettive == {"IRC", "ALT"}, plan.code
    assert not [f for f in check_schedule(dataset["schedule"])
                if f.code in ("election_mismatch", "coverage_mismatch")]


def test_irc_e_alternativa_possono_stare_nella_stessa_fascia(dataset):
    """È tutto ciò che lo sdoppiamento compra: parti della **stessa**
    partizione sono insiemi disgiunti di alunni, quindi non confliggono."""
    env = dataset
    irc = _attivita("IRC", parts__name="1A_REL").first()
    alt = _attivita("ALT", parts__name="1A_ALT").first()
    for act in (irc, alt):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=0)
    assert _hard(env) == []


def test_una_lezione_a_classe_intera_occupa_invece_entrambe_le_parti(dataset):
    """L'altra metà della stessa regola, e senza di essa la prima non
    significa niente: nessuno può fare religione mentre la classe fa italiano."""
    env = dataset
    ita = _attivita("ITA", classes__name="1A").first()
    irc = _attivita("IRC", parts__name="1A_REL").first()
    for act in (ita, irc):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=0)
    codici = _hard(env)
    assert codici and {f.code for f in codici} == {"resource_occupied"}


# ------------------------------------------------------- classe articolata

def test_la_2c_articolata_ha_due_piani_e_nessuna_ambiguita(dataset):
    """La condizione 3 di ADR-015: una parte porta un **piano proprio**, e
    l'altra eredita quello della classe (`NULL` = eredita, ADR-003)."""
    ord_, app = (ClassPart.objects.get(name=n) for n in ("2C_ORD", "2C_APP"))
    assert ord_.study_plan is None
    assert ord_.effective_study_plan == dataset["classes"]["2C"].study_plan
    assert app.effective_study_plan.code == "SAP2"
    # ⚠ `ambiguous_study_plan` è il verdetto che l'atomo dà quando due parti
    # **della stessa combinazione** portano piani diversi: qui non deve
    # scattare, perché la religione non porta piani.
    assert not [f for f in check_schedule(dataset["schedule"])
                if f.code == "ambiguous_study_plan"]


def test_gli_ordinari_non_fanno_informatica_e_gli_applicati_non_fanno_latino(dataset):
    lat = _attivita("LAT", parts__name="2C_ORD")
    inf = _attivita("INF", parts__name="2C_APP")
    assert lat.count() == 3 and inf.count() == 3
    assert not _attivita("LAT", classes__name="2C").exists()
    atoms = AtomMap.build()
    ord_atoms = atoms.part[ClassPart.objects.get(name="2C_ORD").pk]
    app_atoms = atoms.part[ClassPart.objects.get(name="2C_APP").pk]
    assert not (ord_atoms & app_atoms)
    assert ord_atoms <= activity_tokens(lat.first(), atoms=atoms)[0]
    assert not (app_atoms & activity_tokens(lat.first(), atoms=atoms)[0])


# --------------------------------------------------- sdoppiamento a metà classe

def test_l_ora_sdoppiata_il_docente_la_fa_due_volte(dataset):
    """🔑 È il costo dello sdoppiamento, e il motivo per cui il monte ore del
    docente **non si legge dal quadro orario**: 3 ore di scienze in 3A, 4 ore
    di lavoro per N01."""
    n01 = dataset["teachers"]["N01"]
    riga = TeachingAssignment.objects.get(teacher=n01,
                                          school_class__name="3A",
                                          subject__code="SCI")
    assert riga.weekly_minutes == 4 * 60
    servizio = dataset["plans"]["SCI3"].services.get(subject__code="SCI")
    assert servizio.class_minutes == 3 * 60
    assert sum(a.duration_minutes for a in _attivita("SCI", classes__name="3A")) == 120
    # ⚠ Quattro e non due dall'ondata 4: la partizione `LABSCI` esiste ora in
    # 3A **e** in 4A, due parti ciascuna.
    assert _attivita("SCI", parts__partition__name="LABSCI").count() == 4


def test_i_gruppi_di_laboratorio_stanno_sotto_l_effettivo_ridotto(dataset):
    """`Al./Rid.` con la cascata di ADR-003: la materia non lo dichiara, quindi
    vale il default d'istituto — e i due gruppi ci stanno sotto."""
    tetto = dataset["subjects"]["SCI"].effective_max_reduced_students
    assert tetto == 15
    for nome in ("3A_G1", "3A_G2"):
        assert ClassPart.objects.get(name=nome).expected_students <= tetto


# ------------------------------------------------ raggruppamento trasversale

def test_il_raggruppamento_attraversa_due_classi(dataset):
    """🔑 È il caso che **rompe la decomposizione per classe** — la conseguenza
    che ADR-013 dichiara e che nessun dataset aveva mai messo alla prova."""
    base = dataset["groups"]["ING1-BASE"]
    classi = {p.partition.school_class.name for p in base.parts.all()}
    assert classi == {"1A", "1B"}
    act = _attivita("ING", groups=base).first()
    assert not act.classes.exists()
    tokens = activity_tokens(act)[0]
    for nome in ("1A_ING_B", "1B_ING_B"):
        assert ClassPart.objects.get(name=nome).pk in tokens
    # E non tocca l'altro livello, né le classi intere.
    assert ClassPart.objects.get(name="1A_ING_A").pk not in tokens
    assert dataset["classes"]["1A"].pk not in tokens


def test_i_due_livelli_accoppiano_1a_e_1b(dataset):
    """Un'ora del livello base occupa alunni di 1A **e** di 1B: mettere
    un'ora a classe intera di 1B in quella fascia è un conflitto, e non
    esisterebbe se le due classi fossero separabili."""
    env = dataset
    base = _attivita("ING", groups=env["groups"]["ING1-BASE"]).first()
    ita_1b = _attivita("ITA", classes__name="1B").first()
    for act in (base, ita_1b):
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=0)
    codici = _hard(env)
    assert codici and {f.code for f in codici} == {"resource_occupied"}


def test_i_due_livelli_invece_convivono(dataset):
    env = dataset
    for nome in ("ING1-BASE", "ING1-AVANZ"):
        act = _attivita("ING", groups=env["groups"][nome]).first()
        Placement.objects.create(schedule=env["schedule"], activity=act,
                                 day=0, start_slot=0)
    assert _hard(env) == []


# ------------------------------------------------------- ⚠ il debito trovato

def test_l_allineamento_e_un_campo_che_nessuno_legge(dataset):
    """⚠ **Il difetto che l'ondata 2 ha trovato, ed è del motore.**

    📦 Lo XSD `Partenaire_Index` dichiara che *l'allineamento genera l'attività
    complessa*: in EDT le attività allineate sono **una** collocazione, non due
    che si somigliano. Da noi `Activity.alignment_ident` è un campo, e nessun
    builder e nessun checker lo legge — quindi l'IRC e la sua alternativa
    possono finire in due giorni diversi, e metà classe resta a scuola per
    un'ora in cui non ha lezione.

    Misurato sul dataset completo (2026-08-30): dei **15** allineamenti
    dichiarati, **14** escono dal solve senza una sola coincidenza — i due
    livelli di inglese di 1A/1B sparsi su sei celle diverse, il latino e
    l'informatica della 2C articolata mai in parallelo.

    ⚠ Non si ripara qui: la spec §8 dice *nessuna modifica al motore*, e un
    dataset che si aggiusta per far passare un test non prova più niente.
    Questo test **fissa il comportamento sbagliato** perché diventi rosso il
    giorno in cui il debito si chiude. Vedi `docs/todo.md`."""
    env = dataset
    allineate = Activity.objects.exclude(alignment_ident="")
    assert allineate.count() == 40
    assert len({a.alignment_ident for a in allineate}) == 16

    irc = _attivita("IRC", parts__name="1A_REL").first()
    alt = _attivita("ALT", parts__name="1A_ALT").first()
    assert irc.alignment_ident == alt.alignment_ident == "REL-1A"
    Placement.objects.create(schedule=env["schedule"], activity=irc,
                             day=0, start_slot=0)
    Placement.objects.create(schedule=env["schedule"], activity=alt,
                             day=3, start_slot=6)   # tre giorni più in là
    assert _hard(env) == []   # ⚠ nessuno se ne accorge
