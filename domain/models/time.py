from django.db import models


class TimeGrid(models.Model):
    """Griglia parametrica: giorni per ciclo × fasce. In v1 ciclo = settimana,
    ma i due concetti restano campi separati. Niente suddivisioni sub-orarie."""

    days_per_cycle = models.PositiveSmallIntegerField(default=5)
    slots_per_day = models.PositiveSmallIntegerField(default=6)
    slot_minutes = models.PositiveSmallIntegerField(default=60)
    morning_end_slot = models.PositiveSmallIntegerField()  # primo slot del pomeriggio

    def half_day(self, slot: int) -> str:
        return "morning" if slot < self.morning_end_slot else "afternoon"


class Break(models.Model):
    """Intervallo: separatore fra due ranghi, non consuma slot. La linea sta
    prima di boundary_slot."""

    grid = models.ForeignKey(TimeGrid, on_delete=models.CASCADE, related_name="breaks")
    boundary_slot = models.PositiveSmallIntegerField()

    def straddles(self, start_slot: int, duration_slots: int) -> bool:
        return start_slot < self.boundary_slot < start_slot + duration_slots


class SchoolYear(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    first_week_monday = models.DateField()  # ancora del ciclo al calendario reale


class Holiday(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()


class Period(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="periods")
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()


class Schedule(models.Model):
    """Una versione d'orario per un periodo (ADR-010: si rigenera a ogni
    periodo). I piazzamenti appartengono a uno Schedule."""

    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="schedules")
    label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
