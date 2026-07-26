import pytest

from domain.models import (
    ClassPart, ClassPartition, Group, Resource, Room, SchoolClass, StudyPlan,
)


@pytest.fixture
def plan(db):
    return StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)


@pytest.mark.django_db
def test_class_is_a_resource_with_plan_and_preferred_room(plan):
    room = Room.objects.create(name="A101", capacity=30)
    c = SchoolClass.objects.create(name="1A", study_plan=plan, year=1, preferred_room=room)
    assert Resource.objects.get(pk=c.pk).kind == Resource.Kind.CLASS
    assert c.preferred_room == room


@pytest.mark.django_db
def test_part_inherits_study_plan_from_class(plan):
    c = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    partition = ClassPartition.objects.create(school_class=c, name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=partition)
    assert rel.study_plan is None                 # NULL = eredita
    assert rel.effective_study_plan == plan       # condizione 3 di ADR-015


@pytest.mark.django_db
def test_articulated_class_part_carries_its_own_plan(plan):
    other = StudyPlan.objects.create(code="ELE3", name="Elettronica 3", year=3)
    c = SchoolClass.objects.create(name="3A", study_plan=plan, year=3)
    partition = ClassPartition.objects.create(school_class=c, name="Articolazione")
    part_b = ClassPart.objects.create(name="3A_ELE", partition=partition, study_plan=other)
    assert part_b.effective_study_plan == other


@pytest.mark.django_db
def test_group_crosses_classes_through_parts(plan):
    a = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    b = SchoolClass.objects.create(name="1B", study_plan=plan, year=1)
    pa = ClassPartition.objects.create(school_class=a, name="Lingua")
    pb = ClassPartition.objects.create(school_class=b, name="Lingua")
    part_a = ClassPart.objects.create(name="1A_FRA", partition=pa)
    part_b = ClassPart.objects.create(name="1B_FRA", partition=pb)
    g = Group.objects.create(name="FRANCESE 1A-1B")
    g.parts.add(part_a, part_b)
    classes = {p.partition.school_class.name for p in g.parts.all()}
    assert classes == {"1A", "1B"}
