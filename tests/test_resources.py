import pytest

from domain.models import InstituteSettings, Material, Resource, Room, Site, StaffMember


@pytest.mark.django_db
def test_institute_settings_is_singleton():
    a = InstituteSettings.load()
    b = InstituteSettings.load()
    assert a.pk == b.pk == 1


@pytest.mark.django_db
def test_room_is_a_resource_with_default_capacity_one():
    room = Room.objects.create(name="LAB-FIS", capacity=30)
    base = Resource.objects.get(pk=room.pk)
    assert base.kind == Resource.Kind.ROOM
    assert base.simultaneous_capacity == 1


@pytest.mark.django_db
def test_gym_can_host_two_classes():
    gym = Room.objects.create(name="PALESTRA", capacity=60, simultaneous_capacity=2)
    assert Resource.objects.get(pk=gym.pk).simultaneous_capacity == 2


@pytest.mark.django_db
def test_material_and_staff_are_resources():
    cart = Material.objects.create(name="PC portatile", simultaneous_capacity=12)
    aide = StaffMember.objects.create(name="Guglielmi Marco", role="educatore")
    assert Resource.objects.get(pk=cart.pk).kind == Resource.Kind.MATERIAL
    assert Resource.objects.get(pk=aide.pk).kind == Resource.Kind.STAFF


@pytest.mark.django_db
def test_resource_can_have_a_site():
    site = Site.objects.create(name="Succursale")
    room = Room.objects.create(name="S101", site=site)
    assert room.site.name == "Succursale"
