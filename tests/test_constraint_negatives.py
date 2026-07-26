"""I test negativi rimandati dal piano 1: i CheckConstraint respingono
davvero i dati malformati."""
import pytest
from django.db import IntegrityError

from domain.models import (
    ClassPartition, RelaxationQuota, SchoolClass, StudyPlan, Subject,
    SubjectConstraint, Teacher, TeachingAssignment,
)
from domain.models.curriculum import Discipline
from domain.models.time import Break, TimeGrid

pytestmark = pytest.mark.django_db


@pytest.fixture
def env():
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    partition = ClassPartition.objects.create(school_class=klass, name="X")
    from domain.models import ClassPart
    part = ClassPart.objects.create(name="1A-x", partition=partition)
    teacher = Teacher.objects.create(name="Rossi", last_name="Rossi", first_name="Anna")
    return {"subject": subject, "klass": klass, "partition": partition,
            "part": part, "teacher": teacher}


def test_cattedra_con_due_unita_respinta(env):
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=env["subject"],
            school_class=env["klass"], class_part=env["part"], weekly_minutes=60)


def test_cattedra_senza_unita_respinta(env):
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=env["subject"], weekly_minutes=60)


def test_vincolo_di_materia_con_due_unita_respinto(env):
    with pytest.raises(IntegrityError):
        SubjectConstraint.objects.create(
            school_class=env["klass"], class_part=env["part"],
            subject_a=env["subject"], subject_b=env["subject"],
            type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)


def test_partizione_duplicata_respinta(env):
    with pytest.raises(IntegrityError):
        ClassPartition.objects.create(school_class=env["klass"], name="X")


def test_quota_globale_senza_risorsa_ammessa(env):
    quota = RelaxationQuota.objects.create(
        family=RelaxationQuota.Family.MAX_HOURS, resource=None, max_violations=3)
    assert quota.resource is None


def test_straddles_con_durata_uno_mai_a_cavallo():
    grid = TimeGrid.objects.create(morning_end_slot=4)
    interval = Break.objects.create(grid=grid, boundary_slot=2)
    assert not interval.straddles(start_slot=1, duration_slots=1)
    assert not interval.straddles(start_slot=2, duration_slots=1)
    assert interval.straddles(start_slot=1, duration_slots=2)
