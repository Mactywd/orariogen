"""L'ondata 1 dell'Alighieri: l'anagrafica, e la sua quadratura.

⚠ Questi test **non** hanno il mestiere di `test_fermi_representation.py`.
Là la trascrizione è la prova che lo schema regge una scuola osservata; qui è
la prova che il banco è **coerente** — che il quadro orario, le cattedre e le
attività dicono lo stesso numero. Un banco incoerente misura sé stesso."""

import pytest
from django.db.models import Q

from domain.models import (
    Activity, Break, ClassPart, ClassPartition, Discipline, Group,
    ResourceTimeConstraint, Room, SchoolClass, Service, Site, SlotLabel,
    StudyPlan, Subject, Teacher, TeachingAssignment,
)
from tests import alighieri


@pytest.fixture
def dataset(db):
    return alighieri.build()


def test_conteggi_delle_entita(dataset):
    assert Site.objects.count() == 2
    assert Discipline.objects.count() == 10
    assert Subject.objects.count() == 16
    assert StudyPlan.objects.count() == 11    # 2 indirizzi × 5 anni + Scienze Applicate
    assert Service.objects.count() == 128
    assert SchoolClass.objects.count() == 12
    assert Teacher.objects.count() == 23
    assert TeachingAssignment.objects.count() == 140
    assert Room.objects.count() == 20
    assert SlotLabel.objects.count() == 8
    assert Break.objects.count() == 1
    # Ondata 2 — le quattro forme di sdoppiamento
    assert ClassPartition.objects.count() == 12 + 2 + 1 + 1
    assert ClassPart.objects.count() == 32
    assert Group.objects.count() == 2
    # Ondata 3: otto famiglie in dieci righe. `max_half_days` ne porta due (il
    # `MMG` e il `MG`) e `max_presence` anche (il tempo parziale e il
    # cappellano che serve alle sedi).
    assert ResourceTimeConstraint.objects.count() == 10
    assert len({r.type for r in ResourceTimeConstraint.objects.all()}) == 8


def test_340_attivita_per_361_ore_erogate(dataset):
    """⚠ 361 sono le ore **erogate**, non quelle di un alunno. Lo scarto è
    tutto negli sdoppiamenti dell'ondata 2: dodici ore di attività alternativa
    che si affiancano all'IRC, tre di informatica che si affiancano al latino
    nella 2C articolata, e l'ora di laboratorio di 3A insegnata due volte."""
    assert Activity.objects.count() == 340
    total = sum(Activity.objects.values_list("duration_minutes", flat=True))
    assert total == 361 * 60


def test_ogni_cattedra_quadra_a_zero(dataset):
    """Il `+/- = 0` della ripartizione di EDT, riga per riga: le ore assegnate
    a un docente sono esattamente il suo monte ore contrattuale."""
    for teacher in Teacher.objects.all():
        assegnate = sum(a.weekly_minutes
                        for a in TeachingAssignment.objects.filter(teacher=teacher))
        assert assegnate == teacher.effective_weekly_minutes, teacher.name


def test_copertura_a_classe_intera_quadra_col_piano(dataset):
    """La lezione di `vincoli-attesi.md` del Fermi: due materie invertite
    tornano nei totali. Si controlla per (classe, materia) contro il servizio
    del piano.

    ⚠ **Ma solo per le coppie erogate a classe intera**, e dall'ondata 2 non
    sono più tutte. Dove entrano parti e raggruppamenti la somma sulla classe
    non è il monte ore di nessuno: la 1A riceve **sei** ore di inglese, tre per
    livello, e ogni alunno ne fa tre. L'unità vera è l'**atomo** (ADR-020), e
    il predicato che la usa è `structural:coverage` — verificato in
    `test_alighieri_solver.test_su_schedule_vuoto_solo_attivita_non_piazzate`.

    Qui si tiene fermo il resto, *e* si tiene fermo quante coppie sono uscite
    dal conteggio grossolano: un'erogazione che sparisse in silenzio
    tornerebbe verde su entrambi i fronti."""
    fuori = set()
    for school_class in SchoolClass.objects.all():
        parti = ClassPart.objects.filter(partition__school_class=school_class)
        for service in school_class.study_plan.services.all():
            per_unita = Activity.objects.filter(subject=service.subject).filter(
                Q(parts__in=parti) | Q(groups__parts__in=parti)).distinct()
            if per_unita.exists():
                fuori.add((school_class.name, service.subject.code))
                continue
            erogate = sum(a.duration_minutes for a in Activity.objects.filter(
                subject=service.subject, classes=school_class))
            assert erogate == service.class_minutes, (school_class.name,
                                                      service.subject.code)
    assert fuori == {("1A", "ING"), ("1B", "ING"), ("2C", "LAT"), ("3A", "SCI")} | {
        (c[0], m) for c in alighieri.CLASSES for m in ("IRC", "ALT")}


def test_i_due_quadri_orari_sono_diversi(dataset):
    """Due indirizzi servono a qualcosa solo se i loro piani divergono: il
    classico ha greco e non ha disegno, e il suo triennio fa 31 ore."""
    per_piano = {}
    for plan in StudyPlan.objects.all():
        per_piano[plan.code] = {s.subject.code: s.class_minutes // 60
                                for s in plan.services.all()}
    def per_alunno(code):
        """🔑 ADR-020: il piano è un **catalogo**, non un curriculum. Delle due
        righe in alternativa un alunno ne segue una, quindi la somma delle
        righe è un'ora più alta del monte ore di chiunque."""
        quadro = per_piano[code]
        elettive = {s.subject.code
                    for s in StudyPlan.objects.get(code=code).services.all()
                    if s.election_group}
        return sum(quadro.values()) - (len(elettive) - 1 if elettive else 0)

    assert sum(per_piano["SCI1"].values()) == 28 and per_alunno("SCI1") == 27
    assert sum(per_piano["SCI3"].values()) == 31 and per_alunno("SCI3") == 30
    assert sum(per_piano["CLA1"].values()) == 28 and per_alunno("CLA1") == 27
    assert sum(per_piano["CLA3"].values()) == 32 and per_alunno("CLA3") == 31
    assert per_alunno("SAP2") == 27
    assert "GRE" in per_piano["CLA1"] and "GRE" not in per_piano["SCI1"]
    assert "DIS" in per_piano["SCI1"] and "DIS" not in per_piano["CLA1"]
    # L'articolata: stesso totale, materie diverse.
    assert "LAT" in per_piano["SCI2"] and "LAT" not in per_piano["SAP2"]
    assert "INF" in per_piano["SAP2"] and "INF" not in per_piano["SCI2"]


def test_ogni_attivita_ha_una_sede_e_le_sedi_sono_entrambe_abitate(dataset):
    """🔑 `structural:site_transition` legge `Activity.site`, non la sede della
    risorsa: senza questa riga il builder resta muto come sul Fermi, che di
    `Site` ne ha zero."""
    assert not Activity.objects.filter(site=None).exists()
    per_sede = {s.name: Activity.objects.filter(site=s).count()
                for s in Site.objects.all()}
    assert per_sede == {"Centrale": 285, "Succursale": 55}


def test_almeno_un_docente_insegna_in_entrambe_le_sedi(dataset):
    """Senza, due sedi sono due scuole e nessun vincolo di transizione ha
    soggetto."""
    doppi = [t.name for t in Teacher.objects.all()
             if len({a.site_id for a in t.activities.all()}) == 2]
    assert len(doppi) >= 5, doppi
    assert dataset["teachers"]["R01"].name in doppi


def test_i_blocchi_lunghi_rispettano_l_intervallo_mensa(dataset):
    """Il `Break` esiste per essere attraversato-e-vietato: senza attività che
    lo dichiarino, `structural:grid` non toglie una cella per causa sua."""
    lunghe = Activity.objects.filter(duration_slots__gt=1)
    # MOT ×12, MAT biennio ×4, FIS triennio ×3, SCI triennio ×2 — ⚠ due e non
    # tre: in 3A le scienze sono sdoppiate, e le due ore a classe intera che
    # restano non fanno più un blocco.
    assert lunghe.count() == 12 + 4 + 3 + 2
    assert not lunghe.filter(respects_breaks=False).exists()
    assert not Activity.objects.filter(duration_slots=1,
                                       respects_breaks=True).exists()


def test_il_laboratorio_condiviso_della_centrale_e_conteso(dataset):
    """Come al Fermi: a candidata unica la seconda fase non decide niente.
    `LAB-INF` è il laboratorio condiviso della centrale."""
    condivise = Activity.objects.filter(rooms__name="LAB-INF").distinct()
    assert {a.subject.code for a in condivise.select_related("subject")} == {
        "FIS", "SCI", "DIS"}


def test_la_succursale_ha_le_sue_aule_e_non_manda_nessuno_in_centrale(dataset):
    """⚠ Un'attività della succursale che chiedesse un'aula della centrale
    sarebbe un errore di anagrafica travestito da vincolo insoddisfacibile."""
    succ = dataset["sites"]["Succursale"]
    for activity in Activity.objects.filter(site=succ).prefetch_related("rooms"):
        for room in activity.rooms.all():
            assert room.site_id == succ.id, (activity.subject.code, room.name)
