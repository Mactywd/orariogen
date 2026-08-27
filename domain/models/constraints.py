from django.db import models

from .activities import Activity
from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .resources import Resource

_EXACTLY_ONE_UNIT = (
    models.Q(school_class__isnull=False, class_part__isnull=True, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=False, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=True, group__isnull=False)
)


class ResourceUnavailability(models.Model):
    """Rosso/giallo/verde, generico sulla risorsa. date NULL = ricorrente;
    valorizzata = assenza puntuale: indisponibilità e assenze, una tabella."""

    class Level(models.TextChoices):
        HARD = "hard"            # rosso
        OPTIONAL = "optional"    # giallo: violabile solo con override globale
        PREFERENCE = "preference"  # verde

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="unavailabilities")
    day = models.PositiveSmallIntegerField()
    slot = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=10, choices=Level.choices)
    date = models.DateField(null=True, blank=True)


class ResourceTimeConstraint(models.Model):
    """L'asse Cardinalità: i sette gruppi del pannello docente + la soglia
    buchi, sulla risorsa generica (stessa tabella per docenti e classi).
    Chiavi attese in params, per type:
      MIN_DISTRIBUTION:   {"min_days": int, "min_minutes_per_day": int}
      MAX_HOURS:          {"day_minutes": int?, "morning_minutes": int?, "afternoon_minutes": int?}
      MAX_PRESENCE:       {"days": int, "max_minutes": int}
      ARRIVAL_DEPARTURE:  {"days": int, "not_before_slot": int?, "not_after_slot": int?}
      FREE_GUARANTEED:    {"free_days": int, "free_half_days": int}
      MAX_HALF_DAYS:      {"max_half_days": int?, "only_half_day_per_day": bool?}
      MAX_SITE_CHANGES:   {"per_day": int?, "per_week": int?}
      MAX_GAP_HOURS:      {"max_gap_minutes": int}   # D.T.B.
    """

    class Type(models.TextChoices):
        MIN_DISTRIBUTION = "min_distribution"
        MAX_HOURS = "max_hours"
        MAX_PRESENCE = "max_presence"
        ARRIVAL_DEPARTURE = "arrival_departure"
        FREE_GUARANTEED = "free_guaranteed"
        MAX_HALF_DAYS = "max_half_days"
        MAX_SITE_CHANGES = "max_site_changes"
        MAX_GAP_HOURS = "max_gap_hours"

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="time_constraints")
    type = models.CharField(max_length=20, choices=Type.choices)
    params = models.JSONField(default=dict)


class SubjectConstraint(models.Model):
    """L'asse Relazione: orientato (A→B ≠ B→A), con A = B come caso dominante.
    L'enum ricalca TypeIncompatibiliteMatiereClasse di EDT (13 valori);
    l'orizzonte settimana/ciclo e il ritardo delle concatenazioni stanno in
    param (mezze giornate, o minuti per i MAX_HOURS_*)."""

    class Type(models.TextChoices):
        SAME_HALF_DAY_INCOMPATIBLE = "same_half_day_incompatible"
        SAME_DAY_INCOMPATIBLE = "same_day_incompatible"
        TWO_DAYS_INCOMPATIBLE = "two_days_incompatible"
        FORBIDDEN_SEQUENCE = "forbidden_sequence"
        MAX_HOURS_HALF_DAY = "max_hours_half_day"
        MAX_HOURS_DAY = "max_hours_day"
        WEEKLY_ORDER = "weekly_order"
        IMPOSED_SUCCESSION = "imposed_succession"
        HALF_DAY_GAP = "half_day_gap"
        PARTS_BEFORE_CLASS = "parts_before_class"
        PARTS_AFTER_CLASS = "parts_after_class"
        PARTS_BEFORE_OR_AFTER_CLASS_H = "parts_before_or_after_class_h"
        PARTS_BEFORE_OR_AFTER_CLASS_AB = "parts_before_or_after_class_ab"

    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.CASCADE)
    class_part = models.ForeignKey(ClassPart, null=True, blank=True, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    subject_a = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="constraints_as_a")
    subject_b = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="constraints_as_b")
    type = models.CharField(max_length=40, choices=Type.choices)
    param = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=_EXACTLY_ONE_UNIT, name="subject_constraint_one_unit"),
        ]


class RelaxationQuota(models.Model):
    """Alleggerimento a quota, mai a penalità: numero massimo di violazioni,
    per famiglia e opzionalmente per risorsa. Modello lessicografico.

    ⚠ Ogni riga della finestra `Alleggerimenti` di EDT ha **due** parametri, non
    uno: il *quanto* e il *quante volte*. «Autorizza un supplemento di … una
    volta per settimana e per docente» — il supplemento è il margine,
    `max_violations` è la seconda metà. Alcune famiglie hanno solo la seconda
    («Non considerare le incompatibilità … una sola volta al giorno»), e lì il
    vincolo si deroga invece di allargarsi.

    Chiavi attese in `params`, per famiglia:
      MAX_HOURS, MAX_PRESENCE:  {"margine": minuti}
      HALF_DAYS, FREE_GUARANTEED: {"margine": mezze giornate}
      DIDACTIC_WEIGHT:          {"margine": pesi}
      SITES:                    {"margine": cambi di sede}
      SUBJECT_CONSTRAINT:       nessuna — il vincolo si deroga, non si allarga

    `resource` a NULL vale per **tutte** le risorse di quella famiglia; una riga
    con la risorsa valorizzata ha la precedenza su quella generica."""

    class Family(models.TextChoices):
        MAX_PRESENCE = "max_presence"
        FREE_GUARANTEED = "free_guaranteed"
        HALF_DAYS = "half_days"
        SUBJECT_CONSTRAINT = "subject_constraint"
        SITES = "sites"
        BREAKS = "breaks"
        OPTIONAL_UNAVAILABILITY = "optional_unavailability"
        UNAVAILABILITY = "unavailability"
        MAX_HOURS = "max_hours"
        DIDACTIC_WEIGHT = "didactic_weight"
        # In EDT `Gestione Entrate / Uscite` è alleggeribile («Togli se
        # necessario … giornata ridotta per docente»): mancava.
        ARRIVAL_DEPARTURE = "arrival_departure"

    family = models.CharField(max_length=30, choices=Family.choices)
    resource = models.ForeignKey(
        Resource, null=True, blank=True, on_delete=models.CASCADE, related_name="relaxation_quotas"
    )
    max_violations = models.PositiveSmallIntegerField()
    params = models.JSONField(default=dict, blank=True)


class Extraction(models.Model):
    """La selezione di lavoro persistente e nominata: il motore opera
    esclusivamente su di essa."""

    name = models.CharField(max_length=100, unique=True)
    activities = models.ManyToManyField(Activity, related_name="extractions", blank=True)
