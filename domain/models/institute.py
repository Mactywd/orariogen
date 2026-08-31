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

    # Il perimetro su cui si misura un buco, per popolazione. In EDT è la
    # casella «Non conteggiare come buchi le ore libere prima o dopo la linea
    # di fine mattinata», in `Parametri → Istituto → Orari`, **separata per
    # classi e per docenti** (sulla base di esempio: spuntata per i docenti,
    # non per le classi).
    #
    # 🔑 «Spuntata» equivale a «misura dentro la mezza giornata», e non è
    # un'assunzione. Sulla giornata il buco è `ultima − prima + 1 − conteggio`;
    # spezzarlo alla linea toglie esattamente le fasce libere fra l'ultima
    # occupata del mattino e la prima del pomeriggio — cioè, alla lettera, «le
    # ore libere prima o dopo la linea». La misura sta in
    # `tests/test_gap_span.py`.
    #
    # ⚠ Il default è `True` per entrambe, cioè lo **status quo**: fino al
    # 2026-08-30 il perimetro era la mezza giornata e basta. Non è il default
    # di EDT sulle classi, ed è deliberato — la scelta cambia la quantità di un
    # vincolo hard (il D.T.B.), quindi è della scuola e non nostra.
    gaps_split_at_lunch_teachers = models.BooleanField(default=True)
    gaps_split_at_lunch_classes = models.BooleanField(default=True)

    # I giorni che **non contano** come giornata (o mezza giornata) libera. In
    # EDT è una casella per giorno nella stessa finestra — «I giorni spuntati
    # saranno ignorati durante il calcolo delle giornate libere».
    #
    # ⚠ **Non è la maschera dei giorni lavorativi**, ed è tutta la voce: il
    # giorno resta in griglia e ci si lavora, semplicemente non vale come
    # giornata libera. Un sabato in cui nessuno ha lezione non regala a ogni
    # docente il suo giorno libero garantito.
    #
    # Maschera a bit sull'indice di giorno del ciclo, come `Activity.week_mask`
    # lo è sulle settimane: il bit `d` acceso esenta il giorno `d`. Default 0,
    # cioè lo status quo — tutti i giorni contano.
    free_day_exempt_mask = models.PositiveSmallIntegerField(default=0)

    def counts_as_free(self, day: int) -> bool:
        """Il giorno `day` può valere come giornata (o mezza giornata) libera?"""
        return not (self.free_day_exempt_mask >> day) & 1

    #: Le popolazioni per cui EDT ha la casella. Le altre risorse non ne hanno
    #: una da copiare: restano allo status quo.
    _SPLIT_BY_KIND = {
        "teacher": "gaps_split_at_lunch_teachers",
        "class": "gaps_split_at_lunch_classes",
        "class_part": "gaps_split_at_lunch_classes",
    }

    def gaps_split_at_lunch(self, kind):
        """Il buco di questa popolazione si misura dentro la mezza giornata?

        ⚠ Le classi **e le loro parti** leggono la stessa casella: in EDT la
        popolazione è `Classi`, e un gruppo non ha una casella propria."""
        campo = self._SPLIT_BY_KIND.get(kind)
        return True if campo is None else getattr(self, campo)

    # Nota: load() scrive alla prima lettura (get_or_create). Nei percorsi di
    # sola lettura (domain/analysis) si usa objects.filter(pk=1).first().
    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class QualityCriterion(models.Model):
    """Un criterio di qualità, e la sua posizione nella gerarchia.

    ⚠ In EDT i meccanismi sono **due**, e questa tabella ne rappresenta uno
    solo. `Ordinamento dei criteri` è la lista degli undici criteri di
    *piazzamento*, riordinabile fra «considerati» e «ignorati»;
    `Ottimizzazione degli orari` è una fase **separata**, con tre slot ordinati
    **per popolazione** su cinque valori. Qui stanno i quattro valori
    dell'ottimizzazione più `PREFERENCES`, che in EDT è l'undicesimo — e
    ultimo — criterio di piazzamento.

    🔑 L'ordine è un **dato** e non codice, perché è il punto dichiarato del
    meccanismo: *«"Criteri considerati / ignorati" è una UI onesta: dichiara
    che l'ottimizzazione è una scelta editoriale della scuola, non una
    verità»*. Un criterio che non compare qui è un criterio *ignorato*, e la
    tabella vuota dà la catena senza qualità — cioè quella di prima di questo
    pezzo, che è un test e non un corollario.

    ⚠ Nessuna di queste righe cambia ciò che il modello **ammette**: un
    criterio posta variabili di definizione e un `Minimize`, mai un vincolo che
    escluda una soluzione. È anche la ragione per cui ADR-018 non ha niente da
    dire su questa famiglia: le congelate contribuiscono costanti a una somma,
    e non esiste il «pretendere una riparazione» perché non esiste pretesa."""

    class Kind(models.TextChoices):
        # I quattro valori di `Ottimizzazione degli orari`, con l'enum RTTI di
        # EDT accanto: le etichette UI e le enum coincidono esattamente.
        GAPS = "gaps"                        # Durata totale dei buchi, tcoTrous
        FREE_HALF_DAYS = "free_half_days"    # 1/2 giornate libere, tcoDJLibres
        ISOLATED = "isolated"                # Attività isolate, tcoIsoles
        REGULARITY = "regularity"            # Equilibrio didattico,
                                             # tcoMemesHoraires — ⚠ la
                                             # traduzione italiana è
                                             # fuorviante: il senso è
                                             # «stessi orari», cioè la materia
                                             # ricade sempre nella stessa
                                             # fascia, non l'equilibrio del
                                             # carico.
        PREFERENCES = "preferences"          # Rispetta le preferenze (verde)
        # 🔑 **I due arrivati da O5, e vengono dall'altra lista.** Non sono
        # valori di `Ottimizzazione degli orari`: sono il 4° e l'8° degli
        # **undici criteri di piazzamento**, tradotti qui perché è l'unico
        # posto in cui sappiamo dirli. Il cambio di meccanismo è dichiarato in
        # ADR-025 e non è neutro — in EDT governano un'euristica di ricerca,
        # da noi diventano un costo — ma la direzione è quella prudente: un
        # costo non può rendere infattibile ciò che l'euristica al più
        # rallentava. Non hanno un'enum `tco*` accanto perché EDT non gliene
        # dà una: l'altro riquadro non ha enum osservate.
        WEEKLY_SPREAD = "weekly_spread"      # 4. Distribuisci nella settimana
                                             # le attività della stessa materia
        SLOT_SPREAD = "slot_spread"          # 8. Evita le attività della
                                             # stessa materia nella stessa ora
                                             # — ⚠ è `REGULARITY` col segno
                                             # opposto, e per l'altra
                                             # popolazione: vedi ADR-025.

    class Population(models.TextChoices):
        """Su quali risorse il criterio conta. Non è speculativa in vista della
        separazione docenti/classi: la tabella dei criteri di calcolo di EDT dà
        `Gestione dei buchi` come dichiarata «separatamente per i docenti e per
        le classi», quindi è un filtro sulle chiavi che ha significato oggi."""
        ALL = "all"
        TEACHERS = "teachers"
        CLASSES = "classes"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    population = models.CharField(max_length=10, choices=Population.choices,
                                  default=Population.ALL)
    # Crescente: 1 è il criterio più importante. Non è una posizione in una
    # lista di cinque — la gerarchia non va riempita, e nella base di esempio
    # di EDT due slot su tre restano a `Nessuno`.
    rank = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["rank", "kind"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "population"],
                                    name="quality_criterion_unico"),
        ]

    def __str__(self):
        return f"{self.rank}. {self.kind} ({self.population})"
