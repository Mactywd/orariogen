import pytest

from domain.models import (
    CompetitionClass, Discipline, InstituteSettings, Service, StudyPlan, Subject,
)


@pytest.fixture
def lettere(db):
    return Discipline.objects.create(code="LET", name="Lettere")


@pytest.mark.django_db
def test_discipline_maps_to_competition_classes(lettere):
    a011 = CompetitionClass.objects.create(code="A011")
    a013 = CompetitionClass.objects.create(code="A013")
    lettere.competition_classes.add(a011, a013)
    assert lettere.competition_classes.count() == 2


@pytest.mark.django_db
def test_subject_max_reduced_students_inherits_from_institute(lettere):
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.save()
    ita = Subject.objects.create(code="ITA", name="Italiano", discipline=lettere)
    assert ita.max_reduced_students is None          # NULL = eredita
    assert ita.effective_max_reduced_students == 15  # risolto a runtime


@pytest.mark.django_db
def test_subject_didactic_weight_defaults_to_one(lettere):
    ita = Subject.objects.create(code="ITA", name="Italiano", discipline=lettere)
    assert ita.didactic_weight == 1


@pytest.mark.django_db
def test_service_carries_three_durations(lettere):
    plan = StudyPlan.objects.create(code="SCI1", name="Liceo Scientifico - 1 anno", year=1)
    ing = Subject.objects.create(code="ING", name="Inglese", discipline=lettere)
    svc = Service.objects.create(
        study_plan=plan, subject=ing,
        class_minutes=120, reduced_minutes=None, split_minutes=60,
    )
    assert (svc.class_minutes, svc.reduced_minutes, svc.split_minutes) == (120, None, 60)
