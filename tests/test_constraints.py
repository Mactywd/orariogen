import datetime

import pytest

from domain.models import (
    Discipline, Extraction, RelaxationQuota, ResourceTimeConstraint,
    ResourceUnavailability, SchoolClass, StudyPlan, Subject, SubjectConstraint, Teacher,
)


@pytest.fixture
def teacher(db):
    return Teacher.objects.create(name="Russo Elena", last_name="Russo", first_name="Elena")


@pytest.fixture
def school_class(db):
    plan = StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)
    return SchoolClass.objects.create(name="1A", study_plan=plan, year=1)


@pytest.fixture
def arte(db):
    art = Discipline.objects.create(code="ART", name="Arte")
    return Subject.objects.create(code="DIS", name="Disegno", discipline=art)


@pytest.mark.django_db
def test_unavailability_and_absence_share_one_table(teacher):
    recurring = ResourceUnavailability.objects.create(
        resource=teacher, day=1, slot=3, level=ResourceUnavailability.Level.HARD
    )
    dated = ResourceUnavailability.objects.create(
        resource=teacher, day=1, slot=3,
        level=ResourceUnavailability.Level.HARD, date=datetime.date(2027, 3, 12),
    )
    assert recurring.date is None   # NULL = ricorrente, ogni settimana
    assert dated.date is not None   # valorizzata = assenza puntuale


@pytest.mark.django_db
def test_time_constraint_serves_teachers_and_classes(teacher, school_class):
    ResourceTimeConstraint.objects.create(
        resource=teacher, type=ResourceTimeConstraint.Type.MAX_HOURS, params={"day_minutes": 360}
    )
    ResourceTimeConstraint.objects.create(
        resource=school_class, type=ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        params={"max_half_days": 9},
    )  # MMG della classe = stesso vincolo del docente
    assert ResourceTimeConstraint.objects.count() == 2


@pytest.mark.django_db
def test_subject_constraint_is_directed_and_self_pairs_allowed(school_class, arte):
    c = SubjectConstraint.objects.create(
        school_class=school_class, subject_a=arte, subject_b=arte,
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE,
    )  # il caso dominante: la materia con sé stessa
    assert c.subject_a == c.subject_b


@pytest.mark.django_db
def test_relaxation_is_a_quota_not_a_penalty(teacher):
    q = RelaxationQuota.objects.create(
        family=RelaxationQuota.Family.MAX_HOURS, resource=teacher, max_violations=2
    )
    assert q.max_violations == 2


@pytest.mark.django_db
def test_extraction_is_a_named_persistent_selection(arte):
    from domain.models import Activity
    a = Activity.objects.create(subject=arte, duration_slots=1, duration_minutes=60, week_mask=1)
    ext = Extraction.objects.create(name="biennio")
    ext.activities.add(a)
    assert ext.activities.count() == 1
