import datetime

import pytest

from domain import weeks
from domain.models import (
    Activity, ActivityMaterialRequirement, Discipline, Material, Period, Placement,
    Schedule, SchoolClass, SchoolYear, StudyPlan, Subject, Teacher,
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
def test_subject_is_the_only_required_reference(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=weeks.full_mask(33)
    )
    assert a.teachers.count() == 0  # un'attività senza docente è legale (XSD)
    assert a.immobility == Activity.Immobility.NONE


@pytest.mark.django_db
def test_substitution_is_a_single_bit_activity(subject, school_class):
    original = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=weeks.full_mask(33)
    )
    sub = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60,
        week_mask=weeks.single_week(12), parent=original,
    )
    assert bin(sub.week_mask).count("1") == 1  # ADR-014: un bit solo
    assert sub.parent == original


@pytest.mark.django_db
def test_activity_requires_materials_with_quantity(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=1
    )
    laptops = Material.objects.create(name="PC portatile", simultaneous_capacity=12)
    ActivityMaterialRequirement.objects.create(activity=a, material=laptops, quantity=5)
    assert a.material_requirements.get().quantity == 5


@pytest.mark.django_db
def test_placement_is_separate_and_unique_per_schedule(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=2, duration_minutes=120, week_mask=1
    )
    year = SchoolYear.objects.create(
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 6, 8),
        first_week_monday=datetime.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="Q1",
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 1, 31),
    )
    sched = Schedule.objects.create(period=period)
    Placement.objects.create(schedule=sched, activity=a, day=0, start_slot=2)
    assert Placement.objects.count() == 1
    import django.db.utils
    with pytest.raises(django.db.utils.IntegrityError):
        Placement.objects.create(schedule=sched, activity=a, day=1, start_slot=0)
