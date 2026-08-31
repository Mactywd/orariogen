from django.db import models

from .curriculum import StudyPlan
from .resources import Resource, Room


class SchoolClass(Resource):
    KIND = Resource.Kind.CLASS
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.PROTECT, related_name="classes")
    year = models.PositiveSmallIntegerField()
    preferred_room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="preferred_by"
    )
    max_weekly_weight_per_student = models.PositiveSmallIntegerField(null=True, blank=True)
    # `N.Alu` di EDT: il numero di alunni **previsto**, che è il dato con cui
    # la catena previsionale lavora anche senza anagrafica nominativa
    # (`docs/edt/classi.md`). NULL = non dichiarato, e non significa zero: un
    # criterio che lo legge non conta chi non sa contare.
    expected_students = models.PositiveSmallIntegerField(null=True, blank=True)


class ClassPartition(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="partitions")
    name = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school_class", "name"], name="uniq_partition_per_class"),
        ]


class ClassPart(Resource):
    KIND = Resource.Kind.CLASS_PART
    partition = models.ForeignKey(ClassPartition, on_delete=models.CASCADE, related_name="parts")
    study_plan = models.ForeignKey(
        StudyPlan, null=True, blank=True, on_delete=models.PROTECT, related_name="parts"
    )
    # L'effettivo della parte. ⚠ Non si deriva da quello della classe: è
    # precisamente ciò che una suddivisione non dice — due parti della stessa
    # partizione possono essere 12 e 11, o 20 e 3.
    expected_students = models.PositiveSmallIntegerField(null=True, blank=True)

    @property
    def effective_study_plan(self):
        return self.study_plan or self.partition.school_class.study_plan


class Group(models.Model):
    """Raggruppamento trasversale (FR groupe): M2M di parti, attraversa più
    classi. Derivato dall'allineamento, non anagrafica a monte."""

    name = models.CharField(max_length=100, unique=True)
    parts = models.ManyToManyField(ClassPart, related_name="groups")

    def __str__(self):
        return self.name
