"""L'ondata 1 dell'Alighieri: l'anagrafica, e la sua quadratura.

⚠ Questi test **non** hanno il mestiere di `test_fermi_representation.py`.
Là la trascrizione è la prova che lo schema regge una scuola osservata; qui è
la prova che il banco è **coerente** — che il quadro orario, le cattedre e le
attività dicono lo stesso numero. Un banco incoerente misura sé stesso."""

import pytest

from domain.models import (
    Activity, Break, Discipline, Room, SchoolClass, Service, Site, SlotLabel,
    StudyPlan, Subject, Teacher, TeachingAssignment,
)
from tests import alighieri


@pytest.fixture
def dataset(db):
    return alighieri.build()


def test_conteggi_delle_entita(dataset):
    assert Site.objects.count() == 2
    assert Discipline.objects.count() == 8
    assert Subject.objects.count() == 14
    assert StudyPlan.objects.count() == 10          # due indirizzi × cinque anni
    assert Service.objects.count() == 2 * 10 + 3 * 11 + 2 * 9 + 3 * 12
    assert SchoolClass.objects.count() == 12
    assert Teacher.objects.count() == 21
    assert TeachingAssignment.objects.count() == 127
    assert Room.objects.count() == 20
    assert SlotLabel.objects.count() == 8
    assert Break.objects.count() == 1


def test_323_attivita_per_345_ore(dataset):
    assert Activity.objects.count() == 323
    total = sum(Activity.objects.values_list("duration_minutes", flat=True))
    assert total == 345 * 60


def test_ogni_cattedra_quadra_a_zero(dataset):
    """Il `+/- = 0` della ripartizione di EDT, riga per riga: le ore assegnate
    a un docente sono esattamente il suo monte ore contrattuale."""
    for teacher in Teacher.objects.all():
        assegnate = sum(a.weekly_minutes
                        for a in TeachingAssignment.objects.filter(teacher=teacher))
        assert assegnate == teacher.effective_weekly_minutes, teacher.name


def test_copertura_per_classe_e_materia_non_solo_i_totali(dataset):
    """La lezione di `vincoli-attesi.md` del Fermi: due materie invertite
    tornano nei totali. Si controlla per (classe, materia) contro il servizio
    del piano."""
    for school_class in SchoolClass.objects.all():
        for service in school_class.study_plan.services.all():
            piazzate = sum(
                a.duration_minutes
                for a in Activity.objects.filter(classes=school_class,
                                                 subject=service.subject))
            assert piazzate == service.class_minutes, (school_class.name,
                                                       service.subject.code)


def test_i_due_quadri_orari_sono_diversi(dataset):
    """Due indirizzi servono a qualcosa solo se i loro piani divergono: il
    classico ha greco e non ha disegno, e il suo triennio fa 31 ore."""
    per_piano = {}
    for plan in StudyPlan.objects.all():
        per_piano[plan.code] = {s.subject.code: s.class_minutes // 60
                                for s in plan.services.all()}
    assert sum(per_piano["SCI1"].values()) == 27
    assert sum(per_piano["SCI3"].values()) == 30
    assert sum(per_piano["CLA1"].values()) == 27
    assert sum(per_piano["CLA3"].values()) == 31
    assert "GRE" in per_piano["CLA1"] and "GRE" not in per_piano["SCI1"]
    assert "DIS" in per_piano["SCI1"] and "DIS" not in per_piano["CLA1"]


def test_ogni_attivita_ha_una_sede_e_le_sedi_sono_entrambe_abitate(dataset):
    """🔑 `structural:site_transition` legge `Activity.site`, non la sede della
    risorsa: senza questa riga il builder resta muto come sul Fermi, che di
    `Site` ne ha zero."""
    assert not Activity.objects.filter(site=None).exists()
    per_sede = {s.name: Activity.objects.filter(site=s).count()
                for s in Site.objects.all()}
    assert per_sede == {"Centrale": 273, "Succursale": 50}


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
    assert lunghe.count() == 12 + 4 + 3 + 3   # MOT, MAT biennio, FIS, SCI
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
