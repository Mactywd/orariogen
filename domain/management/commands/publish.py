"""L'orario nella forma che Aurora legge: la griglia piatta, e cosa si perde.

⚠ **Non scrive niente da nessuna parte, e oggi non potrebbe.** La `School` di
Aurora non esiste ancora in questo modello (ADR-032, il trasloco), quindi
questo comando mostra le righe che *usciranno* e conta la perdita. È il modo
di guardare la pubblicazione prima di poterla eseguire — e su questo progetto
provare il comando invece dei test ha già trovato una cosa che i test
tacevano.
"""

from django.core.management.base import BaseCommand, CommandError

from domain import extraction as ex
from domain.models import Resource, Schedule
from domain.publication import pubblica


class Command(BaseCommand):
    help = ("Mostra l'orario di uno schedule nella forma di `ScheduleEntry` "
            "(la griglia piatta di Aurora) e la perdita dell'appiattimento.")

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello schedule da pubblicare")
        parser.add_argument("--risorsa", type=int, default=None,
                            help="pk della risorsa: solo il suo orario")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction da pubblicare")
        parser.add_argument("--righe", action="store_true",
                            help="stampa anche le righe, una per riga")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        selected = None

        if options["risorsa"] is not None:
            risorsa = Resource.objects.filter(pk=options["risorsa"]).first()
            if risorsa is None:
                raise CommandError(f"risorsa {options['risorsa']} inesistente")
            selected = ex.per_risorsa([risorsa.pk])
        if options["estrazione"]:
            estratte = ex.carica(options["estrazione"])
            selected = estratte if selected is None else selected & estratte

        righe, perdita = pubblica(schedule, selected)

        if options["righe"]:
            for r in righe:
                self.stdout.write(
                    f"{r.teacher}\t{r.weekday}\t{r.period_number}\t"
                    f"{r.school_class}\t{r.subject}\t{r.iso_week_mask}")

        docenti = len({r.teacher for r in righe})
        classi = len({r.school_class for r in righe})
        settimanali = sum(1 for r in righe
                          if r.iso_week_mask != max((x.iso_week_mask
                                                     for x in righe), default=0))
        self.stdout.write("")
        self.stdout.write(f"== Griglia piatta (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Righe: {len(righe)}")
        self.stdout.write(f"  Docenti: {docenti} · Classi: {classi}")
        self.stdout.write(f"  Righe non annuali: {settimanali}")

        self.stdout.write("")
        self.stdout.write("== La perdita dell'appiattimento ==")
        if perdita.vuota:
            self.stdout.write("  Niente: l'orario passa il confine intero.")
            return
        # ⚠ Le due nature stanno separate apposta: la prima è
        # un'approssimazione con cui Aurora convive già, le altre sono ore che
        # **non escono affatto**.
        if perdita.parti or perdita.gruppi:
            self.stdout.write("  Vero ma incompleto — la lezione esce, la sua "
                              "unità no:")
            if perdita.parti:
                self.stdout.write(f"    {perdita.parti} attività su una parte "
                                  "di classe → esce la classe intera")
            if perdita.gruppi:
                self.stdout.write(f"    {perdita.gruppi} attività su un "
                                  "raggruppamento → escono le classi toccate")
        buchi = [(perdita.senza_docente, "attività senza docente "
                  "(`ScheduleEntry.teacher` è obbligatoria)"),
                 (perdita.fuori_settimana, "piazzamenti oltre il venerdì "
                  "(Aurora non ha il sabato)"),
                 (perdita.fuori_periodo, "attività fuori dal periodo dello "
                  "schedule")]
        buchi = [(n, t) for n, t in buchi if n]
        if buchi:
            self.stdout.write("  Non esce affatto:")
            for n, testo in buchi:
                self.stdout.write(f"    {n} {testo}")
        if perdita.celle_ambigue:
            self.stdout.write(f"  Celle ambigue: {len(perdita.celle_ambigue)} "
                              "(stesso docente, stessa classe, stessa ora, due "
                              "materie — l'unicità di Aurora non le distingue)")
            for chiave, materie in perdita.celle_ambigue[:10]:
                d, g, o, c = chiave
                self.stdout.write(f"    {d} · {g} ora {o} · {c}: "
                                  f"{' / '.join(materie)}")
        if perdita.fuse:
            self.stdout.write(f"  Righe fuse: {perdita.fuse} (due parti, stesso "
                              "docente e stessa materia: là è una riga sola)")
