from django.db import models

from .institute import InstituteSettings


class CompetitionClass(models.Model):
    """Classe di concorso ministeriale (A011, A027…). Nostra estensione, non
    campo EDT (ADR-002)."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100, blank=True)


class Discipline(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    competition_classes = models.ManyToManyField(CompetitionClass, blank=True)


class Subject(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    discipline = models.ForeignKey(Discipline, on_delete=models.PROTECT)
    max_reduced_students = models.PositiveSmallIntegerField(null=True, blank=True)
    didactic_weight = models.PositiveSmallIntegerField(default=1)

    @property
    def effective_max_reduced_students(self):
        if self.max_reduced_students is not None:
            return self.max_reduced_students
        return InstituteSettings.load().default_max_reduced_students


class StudyPlan(models.Model):
    """Indirizzo × anno (la chiave Formation+Specialite dello XSD)."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()


class Service(models.Model):
    """Riga del quadro orario del piano. Monte ore tripartito, in minuti."""

    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="services")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    class_minutes = models.PositiveIntegerField()
    #: ⚠ `Rid.` e `Sdop.` di EDT — *durata con alunni ridotti* e *con alunni
    #: sdoppiati*. Sono **osservazione registrata e non funzionalità**: nessuno
    #: li legge, e nessuna delle due basi che abbiamo li compila — né il Fermi
    #: né quella del produttore, dove sono vuoti su ogni riga di ogni piano.
    #: Restano perché EDT li ha davvero; il codice che li usasse andrebbe
    #: scritto su un dato che oggi non esiste (O3 di todo.md, chiusa così).
    reduced_minutes = models.PositiveIntegerField(null=True, blank=True)
    split_minutes = models.PositiveIntegerField(null=True, blank=True)
    #: ADR-026. *Questa riga è dovuta da tutti?* — il `MS` di EDT nella sua
    #: forma minima: `S` (`Tronc commun`, il percorso che tutti seguono) contro
    #: gli altri sette codici, che sono tutti forme di **opzione**.
    #: ⚠ È l'**altro** asse rispetto a `election_group`, non lo stesso: quello
    #: dice *«di queste se ne segue una»* e vincola un gruppo, questo dice
    #: *«questa non è dovuta a tutti»* e vale sulla singola riga. Una riga in
    #: un gruppo risponde «no» per costruzione, quindi qui il valore non è
    #: letto: la copertura misura prima i gruppi, poi questo sul resto.
    elective = models.BooleanField(default=False)
    #: ADR-020. Le righe dello stesso piano che condividono l'etichetta sono
    #: **alternative**: un alunno ne segue esattamente una. Senza di essa il
    #: piano è un catalogo letto come curriculum, e IRC/alternativa produce due
    #: scostamenti su ogni classe italiana. ⚠ È la forma minima del `MS` di EDT
    #: (`Modalité d'élection`, sette codici, `R` = Religioso): l'enumerazione
    #: si copia quando `MS` sarà osservata in UI, non prima (O6 di todo.md).
    election_group = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["study_plan", "subject"], name="uniq_service_plan_subject"),
        ]
