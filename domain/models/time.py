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


class SlotLabel(models.Model):
    """L'**etichetta oraria** della fascia: l'ora che l'utente legge.

    📦 È il `Place` dello XSD `Partenaire_Index` V4.6, che porta
    `@LibelleHeureDebut` e `@LibelleHeureFin` accanto al suo `@Numero`
    0-based — cioè l'orologio sta **per fascia**, non sulla griglia.

    🔑 E non è ridondante con `slot_minutes`, che è un'altra grandezza:
    `tempo-e-calendario.md` §*Due nozioni di «ora»* le tiene distinte per
    nome. La **fascia di calcolo** è l'unità del motore *e* dell'ora di
    servizio del docente (*«Mantenere la durata predefinita di 60 minuti se
    una fascia oraria corrisponde a un'ora di servizio»*); l'**etichetta**
    è personalizzabile (*«ad esempio 55 minuti»*, orari sfalsati) e non
    ricalcola nessun monte ore. Un calendario legge la seconda: al telefono
    di un docente interessa quando entra in aula, non quanto gli viene
    contato.

    ⚠ Facoltativa, e senza default: una griglia priva di etichette non ha un
    orologio, e inventarne uno («si comincia alle 8») metterebbe in silenzio
    le lezioni di tutta la scuola all'ora sbagliata. L'export rifiuta invece
    di indovinare."""

    grid = models.ForeignKey(TimeGrid, on_delete=models.CASCADE,
                             related_name="slot_labels")
    slot = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["slot"]
        constraints = [
            models.UniqueConstraint(fields=["grid", "slot"],
                                    name="uniq_slot_label_per_grid"),
        ]

    def __str__(self):
        return f"f{self.slot} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


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
