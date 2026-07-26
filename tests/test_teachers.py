import pytest
from django.db import IntegrityError

from domain.models import (
    Discipline, InstituteSettings, SchoolClass, StudyPlan, Subject, Teacher,
    TeachingAssignment,
)


@pytest.fixture
def subject(db):
    let = Discipline.objects.create(code="LET", name="Lettere")
    return Subject.objects.create(code="ITA", name="Italiano", discipline=let)


@pytest.fixture
def school_class(db):
    plan = StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)
    return SchoolClass.objects.create(name="1A", study_plan=plan, year=1)


@pytest.mark.django_db
def test_capability_is_separate_from_assignment(subject, school_class):
    t = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    t.teachable_subjects.add(subject)          # capacità (ADR-006)
    assert TeachingAssignment.objects.count() == 0  # nessuna cattedra implicita


@pytest.mark.django_db
def test_weekly_minutes_inherits_global_default(subject):
    settings = InstituteSettings.load()
    settings.default_teacher_weekly_minutes = 18 * 60
    settings.save()
    t = Teacher.objects.create(name="Bianchi Marco", last_name="Bianchi", first_name="Marco")
    assert t.weekly_minutes is None
    assert t.effective_weekly_minutes == 18 * 60


@pytest.mark.django_db
def test_assignment_points_to_exactly_one_unit(subject, school_class):
    t = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    TeachingAssignment.objects.create(
        teacher=t, subject=subject, school_class=school_class, weekly_minutes=240
    )
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(teacher=t, subject=subject, weekly_minutes=240)
