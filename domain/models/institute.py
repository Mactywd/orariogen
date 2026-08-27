from django.db import models


class Site(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class InstituteSettings(models.Model):
    """Singleton. I default d'istituto della cascata dichiarata (ADR-003) e i
    parametri unici (transizione di sede, tetti di peso didattico)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    default_teacher_weekly_minutes = models.PositiveIntegerField(null=True, blank=True)
    default_max_reduced_students = models.PositiveSmallIntegerField(null=True, blank=True)
    site_transition_slots = models.PositiveSmallIntegerField(default=1)
    max_weight_morning = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_afternoon = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_day = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_week = models.PositiveSmallIntegerField(null=True, blank=True)
    # Il tetto globale della finestra `Alleggerimenti`: «Numero massimo di
    # vincoli da alleggerire per risorsa». NULL = nessun tetto oltre alle
    # quote per famiglia.
    max_relaxed_constraints_per_resource = models.PositiveSmallIntegerField(
        null=True, blank=True)

    # Nota: load() scrive alla prima lettura (get_or_create). Nei percorsi di
    # sola lettura (domain/analysis) si usa objects.filter(pk=1).first().
    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
