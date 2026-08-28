import pytest

from domain.models import (
    Activity, Discipline, Room, SchoolClass, Service, StudyPlan, Subject, Teacher,
    TeachingAssignment,
)
from tests import fermi


@pytest.fixture
def dataset(db):
    return fermi.build()


def test_entity_counts(dataset):
    assert Discipline.objects.count() == 8
    assert Subject.objects.count() == 12
    assert StudyPlan.objects.count() == 5
    assert Service.objects.count() == 2 * 10 + 3 * 11  # biennio 10 materie, triennio 11
    assert SchoolClass.objects.count() == 10
    assert Teacher.objects.count() == 18
    assert Room.objects.count() == 16


def test_284_activities_for_288_hours(dataset):
    assert Activity.objects.count() == 284
    total = sum(Activity.objects.values_list("duration_minutes", flat=True))
    assert total == 288 * 60


def test_every_teacher_balances_to_zero(dataset):
    for teacher in Teacher.objects.all():
        assigned = sum(
            a.weekly_minutes for a in TeachingAssignment.objects.filter(teacher=teacher)
        )
        assert assigned == teacher.effective_weekly_minutes, teacher.name


def test_coverage_per_plan_and_subject_not_just_totals(dataset):
    """La lezione di vincoli-attesi.md: STO/SCI invertite tornavano nei totali.
    Si controlla per (classe, materia), contro il servizio del piano."""
    for school_class in SchoolClass.objects.all():
        for service in school_class.study_plan.services.all():
            placed = sum(
                a.duration_minutes
                for a in Activity.objects.filter(classes=school_class, subject=service.subject)
            )
            assert placed == service.class_minutes, (school_class.name, service.subject.code)


def test_gym_hosts_two_classes_lab_inf_is_smaller(dataset):
    assert Room.objects.get(name="PALESTRA").simultaneous_capacity == 2
    assert Room.objects.get(name="LAB-INF").capacity == 25


def test_il_fermi_chiede_almeno_un_aula(dataset):
    """Prima di questo pezzo nessuna attivita' del Fermi dichiarava aule,
    quindi la seconda fase aveva un problema **vuoto** — e una misura su un
    problema vuoto non e' una misura."""
    assert Activity.objects.exclude(rooms=None).count() > 0


def test_il_laboratorio_condiviso_e_conteso(dataset):
    """⚠ E il problema non dev'essere solo non vuoto: dev'essere una
    **decisione**. A candidata unica l'aula entra gia' nei token del
    piazzamento (`domain/analysis/state.py`), quindi la ripartizione si
    limiterebbe a confermare una scelta gia' fatta: zero gradi di liberta',
    e una misura che non puo' fallire. `LAB-INF` e' condiviso da tre materie
    con docenti diversi, ed e' cio' che rende la fase una scelta vera."""
    condivise = Activity.objects.filter(rooms__name="LAB-INF").distinct()
    materie = {a.subject.code for a in condivise.select_related("subject")}
    assert materie == {"FIS", "SCI", "DIS"}, materie
    assert Activity.objects.filter(rooms__name="PALESTRA").exists()
