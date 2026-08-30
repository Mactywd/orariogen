from django.db import models

from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .institute import Site
from .resources import Material, Room, StaffMember
from .teachers import Teacher
from .time import Schedule


class Activity(models.Model):
    """L'unità di piazzamento (ADR-014): una sola entità con maschera
    temporale. La sostituzione è la stessa riga con un bit solo."""

    class Immobility(models.TextChoices):
        NONE = "none"
        FIXED = "fixed"
        LOCKED_IN_PLACE = "locked_in_place"
        NOT_SUSPENDABLE = "not_suspendable"
        SUSPENDED = "suspended"

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)  # unico obbligatorio
    teachers = models.ManyToManyField(Teacher, blank=True, related_name="activities")
    classes = models.ManyToManyField(SchoolClass, blank=True, related_name="activities")
    parts = models.ManyToManyField(ClassPart, blank=True, related_name="activities")
    groups = models.ManyToManyField(Group, blank=True, related_name="activities")
    rooms = models.ManyToManyField(Room, blank=True, related_name="activities")  # eccezione dichiarata
    staff = models.ManyToManyField(StaffMember, blank=True, related_name="activities")
    materials = models.ManyToManyField(
        Material, blank=True, through="ActivityMaterialRequirement", related_name="activities"
    )
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)

    duration_slots = models.PositiveSmallIntegerField()
    duration_minutes = models.PositiveIntegerField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )  # spezzamento padre/figlio (TypeParenteCours)
    alignment_ident = models.CharField(max_length=50, blank=True)  # stesso ident = attività complessa
    week_mask = models.PositiveBigIntegerField()

    respects_breaks = models.BooleanField(default=False)
    priority = models.BooleanField(default=False)
    immobility = models.CharField(max_length=20, choices=Immobility.choices, default=Immobility.NONE)


class ActivityMaterialRequirement(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="material_requirements")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)


class Placement(models.Model):
    """Il piazzamento è output, mai sull'attività. assigned_room è l'esito
    della seconda fase (assegnazione aule), distinto dalle aule dichiarate."""

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="placements")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="placements")
    day = models.PositiveSmallIntegerField()
    start_slot = models.PositiveSmallIntegerField()
    assigned_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)
    # Il lucchetto **sull'aula**, distinto dall'immobilità della collocazione.
    # In EDT è la casella per riga di `Blocco delle aule nelle attività
    # coinvolte`, nella finestra dell'ottimizzatore: si blocca *questa*
    # assegnazione, e l'attività resta libera di spostarsi in griglia.
    # ⚠ Come per l'immobilità, blocca l'aula che ha e non quella che non ha:
    # con `assigned_room` a NULL non blocca niente.
    room_locked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["schedule", "activity"], name="uniq_placement_per_schedule"),
        ]
