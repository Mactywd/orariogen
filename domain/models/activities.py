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
    #: La relazione *sostituisce* di ADR-014 (in EDT `RELATIONCOURSSUBSTITUT`,
    #: 161 record verificati): questa riga rimpiazza quella annuale nelle
    #: settimane della **propria** maschera. È anche il campo `natura` che
    #: quell'ADR chiedeva — un'attività è un sostituto se lo dichiara — e la
    #: *soppressione dell'occorrenza* originale ne discende invece di essere
    #: una seconda tabella: una sola verità, e nessun modo di scriverne due
    #: che si contraddicono.
    #: ⚠ Non è la cancellazione di EDT (`ANNULATIONCOURS`), che è un'ora **non
    #: tenuta** e non ha un sostituto: quella resta fuori.
    substitutes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="substituted_by")

    respects_breaks = models.BooleanField(default=False)
    priority = models.BooleanField(default=False)
    immobility = models.CharField(max_length=20, choices=Immobility.choices, default=Immobility.NONE)


def effective_week_masks(pairs=None):
    """`{id attività: maschera effettiva}` — la maschera dichiarata **meno** le
    settimane in cui un sostituto la rimpiazza.

    🔑 È l'altra metà di ADR-014, e senza di essa quella decisione è mezza: il
    sostituto ha un bit solo e compare da sé, ma l'originale resta annuale
    (161/161 nella base di EDT), quindi le due ore si sovrappongono nella
    settimana sostituita — due lezioni nel calendario del docente, e per
    l'analisi un conflitto di occupazione su una classe che in realtà ha
    un'ora sola.

    ⚠ **Vale ovunque si legga una maschera**, non solo nell'export: il punto
    non è che il calendario mostri una cosa e i checker un'altra, è che
    l'orario di quella settimana *è* uno solo. I quattro lettori — le firme di
    settimana, lo stato, la capienza e l'iCal — passano tutti di qui.

    `pairs` sono le coppie `(id, maschera)` già in mano al chiamante, così chi
    ha già filtrato (per esempio le sospese) non rifà la query."""
    if pairs is None:
        pairs = Activity.objects.values_list("id", "week_mask")
    coperte = {}
    # ⚠ Un sostituto **sospeso** non sopprime niente: se l'ora di rimpiazzo non
    # si tiene, quella che si tiene è di nuovo l'originale. È la stessa
    # esclusione che ogni lettore di maschere applica di suo, e va ripetuta qui
    # perché questa query non passa dalla loro.
    for original, mask in (Activity.objects
                           .filter(substitutes__isnull=False)
                           .exclude(immobility=Activity.Immobility.SUSPENDED)
                           .values_list("substitutes_id", "week_mask")):
        coperte[original] = coperte.get(original, 0) | mask
    return {i: m & ~coperte.get(i, 0) for i, m in pairs}


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
