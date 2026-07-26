from django.db import models

from .institute import Site


class Resource(models.Model):
    """Base comune delle risorse di piazzamento (multi-table inheritance).
    Disponibilità, vincoli orari e capacità puntano qui, mai al tipo concreto."""

    class Kind(models.TextChoices):
        TEACHER = "teacher"
        CLASS = "class"
        CLASS_PART = "class_part"
        ROOM = "room"
        STAFF = "staff"
        MATERIAL = "material"

    KIND = None  # ogni sottoclasse lo fissa

    kind = models.CharField(max_length=16, choices=Kind.choices, editable=False)
    name = models.CharField(max_length=100)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)
    simultaneous_capacity = models.PositiveSmallIntegerField(default=1)

    def save(self, *args, **kwargs):
        if self.KIND is not None:
            self.kind = self.KIND
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Room(Resource):
    KIND = Resource.Kind.ROOM
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)  # descrittiva


class Material(Resource):
    KIND = Resource.Kind.MATERIAL


class StaffMember(Resource):
    KIND = Resource.Kind.STAFF
    role = models.CharField(max_length=50, blank=True)
