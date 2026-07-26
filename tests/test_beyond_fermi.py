import pytest

from domain import weeks
from domain.models import (
    Activity, ClassPart, ClassPartition, Group, InstituteSettings, Site,
)
from tests import fermi


@pytest.fixture
def dataset(db):
    return fermi.build()


def _irc_partition(dataset, class_name):
    c = dataset["classes"][class_name]
    partition = ClassPartition.objects.create(school_class=c, name="IRC")
    rel = ClassPart.objects.create(name=f"{class_name}_REL", partition=partition)
    alt = ClassPart.objects.create(name=f"{class_name}_ALT", partition=partition)
    return rel, alt


@pytest.mark.django_db
def test_irc_and_alternative_are_two_parts(dataset):
    rel, alt = _irc_partition(dataset, "1A")
    assert rel.partition == alt.partition          # stessa partizione
    assert rel.effective_study_plan == alt.effective_study_plan  # entrambe ereditano


@pytest.mark.django_db
def test_transversal_group_and_its_activity(dataset):
    rel_a, _ = _irc_partition(dataset, "2A")
    rel_b, _ = _irc_partition(dataset, "2B")
    g = Group.objects.create(name="ALTERNATIVA 2A-2B")
    g.parts.add(rel_a, rel_b)
    a = Activity.objects.create(
        subject=dataset["subjects"]["IRC"], duration_slots=1, duration_minutes=60,
        week_mask=weeks.full_mask(fermi.WEEKS_IN_YEAR), alignment_ident="ALT-2AB",
    )
    a.groups.add(g)
    involved = {p.partition.school_class.name for p in a.groups.get().parts.all()}
    assert involved == {"2A", "2B"}  # l'attività accoppia due classi


@pytest.mark.django_db
def test_sites_with_transition_parameter(dataset):
    branch = Site.objects.create(name="Succursale")
    settings = InstituteSettings.load()
    settings.site_transition_slots = 1
    settings.save()
    a = Activity.objects.create(
        subject=dataset["subjects"]["MOT"], duration_slots=1, duration_minutes=60,
        week_mask=1, site=branch,
    )
    assert a.site == branch
    assert InstituteSettings.load().site_transition_slots == 1


@pytest.mark.django_db
def test_substitution_reuses_a_fermi_activity(dataset):
    original = Activity.objects.filter(classes=dataset["classes"]["1A"]).first()
    substitute = dataset["teachers"]["D02"]
    sub = Activity.objects.create(
        subject=original.subject, duration_slots=original.duration_slots,
        duration_minutes=original.duration_minutes,
        week_mask=weeks.single_week(12), parent=original,
    )
    sub.teachers.add(substitute)
    sub.classes.set(original.classes.all())
    assert bin(sub.week_mask).count("1") == 1
    assert list(sub.classes.all()) == list(original.classes.all())
