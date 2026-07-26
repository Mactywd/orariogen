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

    @property
    def effective_study_plan(self):
        return self.study_plan or self.partition.school_class.study_plan


class Group(models.Model):
    """Raggruppamento trasversale (FR groupe): M2M di parti, attraversa più
    classi. Derivato dall'allineamento, non anagrafica a monte."""

    name = models.CharField(max_length=100, unique=True)
    parts = models.ManyToManyField(ClassPart, related_name="groups")
