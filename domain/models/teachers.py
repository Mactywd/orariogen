from django.db import models

from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .institute import InstituteSettings
from .resources import Resource

_EXACTLY_ONE_UNIT = (
    models.Q(school_class__isnull=False, class_part__isnull=True, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=False, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=True, group__isnull=False)
)


class Teacher(Resource):
    KIND = Resource.Kind.TEACHER
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10, blank=True)
    status = models.CharField(max_length=30, blank=True)  # pura anagrafica
    weekly_minutes = models.PositiveIntegerField(null=True, blank=True)  # Mh/s; NULL = default globale
    max_overtime_minutes = models.PositiveIntegerField(null=True, blank=True)  # HSMax
    preferred_subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.SET_NULL, related_name="preferred_by"
    )
    teachable_subjects = models.ManyToManyField(Subject, related_name="teachable_by", blank=True)

    @property
    def effective_weekly_minutes(self):
        if self.weekly_minutes is not None:
            return self.weekly_minutes
        return InstituteSettings.load().default_teacher_weekly_minutes


class TeachingAssignment(models.Model):
    """La cattedra: docente × materia × unità × ore. L'unità è classe, parte o
    raggruppamento — mai solo la classe intera."""

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.CASCADE)
    class_part = models.ForeignKey(ClassPart, null=True, blank=True, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    weekly_minutes = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=_EXACTLY_ONE_UNIT, name="assignment_exactly_one_unit"),
        ]

    @property
    def unit(self):
        return self.school_class or self.class_part or self.group
