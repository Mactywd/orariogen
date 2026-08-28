"""`Estrai` da riga di comando: costruisce la selezione di lavoro e, con
`--salva`, la memorizza sotto un nome.

I criteri di uno stesso lancio si **intersecano** fra assi e si **uniscono**
dentro un asse: `--risorsa 3 7 --stato non_piazzate` sono «le non piazzate
della risorsa 3 **o** 7», come una maschera di filtro. La composizione con
un'estrazione già salvata è invece esplicita — `--base` più `--modo` — e copre
le quattro operazioni del menu di EDT, `Limita la ricerca alle attività già
estratte` compresa (`--modo limita`).

⚠ Senza `--salva` non scrive: il comando dice cosa estrarrebbe. È la stessa
cautela di `solve` e `assign_rooms`, per una ragione più tenue ma reale —
`--salva` **sovrascrive** l'estrazione omonima, e le estrazioni sono ciò su cui
il motore poi opera."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.conformity import check_schedule
from domain import extraction as ex
from domain.models import Activity, Extraction, Schedule


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


class Command(BaseCommand):
    help = "Costruisce la selezione di lavoro su cui il motore opera"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, default=None,
                            help="pk dello Schedule; serve a `--stato` e a "
                                 "`--rileva`, non ai criteri anagrafici")
        parser.add_argument("--elenca", action="store_true",
                            help="elenca le estrazioni salvate ed esce")
        parser.add_argument("--stato", nargs="*", default=(), choices=ex.STATI)
        parser.add_argument("--rileva", nargs="*", default=(),
                            choices=sorted(ex.RILEVATORI))
        parser.add_argument("--risorsa", nargs="*", type=int, default=(),
                            help="pk di Resource (docente, classe, parte, "
                                 "aula, personale, materiale)")
        parser.add_argument("--materia", nargs="*", type=int, default=())
        parser.add_argument("--giorno", type=int, default=None)
        parser.add_argument("--dalla", type=int, default=None)
        parser.add_argument("--alla", type=int, default=None)
        parser.add_argument("--parzialmente", action="store_true",
                            help="basta che l'attività tocchi la finestra "
                                 "(default: dev'esserci dentro tutta)")
        parser.add_argument("--base", type=str, default=None,
                            help="nome dell'estrazione da cui partire")
        parser.add_argument("--modo", type=str, default="sostituisci",
                            choices=ex.MODI)
        parser.add_argument("--salva", type=str, default=None,
                            help="nome sotto cui memorizzare (sovrascrive)")

    def handle(self, *args, **options):
        if options["elenca"]:
            self._elenca()
            return

        schedule = None
        if options["schedule"]:
            schedule = Schedule.objects.get(pk=options["schedule"])

        selezioni, rilevamenti = [], []
        if options["stato"]:
            if schedule is None:
                raise CommandError("`--stato` richiede `--schedule`.")
            unione = set()
            for stato in options["stato"]:
                unione |= ex.per_stato(schedule, stato)
            selezioni.append(frozenset(unione))
        if options["rileva"]:
            if schedule is None:
                raise CommandError("`--rileva` richiede `--schedule`.")
            # Una sola passata di `check_schedule` per tutti i rilevatori: è la
            # parte cara, e si paga una volta.
            findings = check_schedule(schedule)
            unione = set()
            for nome in options["rileva"]:
                r = ex.rileva(schedule, nome, findings)
                rilevamenti.append(r)
                unione |= r.activity_ids
            selezioni.append(frozenset(unione))
        if options["risorsa"]:
            selezioni.append(ex.per_risorsa(options["risorsa"]))
        if options["materia"]:
            selezioni.append(ex.per_materia(options["materia"]))
        if options["giorno"] is not None:
            if schedule is None:
                raise CommandError("`--giorno` richiede `--schedule`.")
            dalla = options["dalla"] if options["dalla"] is not None else 0
            alla = options["alla"] if options["alla"] is not None else 10 ** 6
            selezioni.append(ex.nella_fascia(
                schedule, options["giorno"], dalla, alla,
                interamente=not options["parzialmente"]))

        base = ex.carica(options["base"]) if options["base"] else frozenset()
        if selezioni:
            risultato = ex.componi(base, frozenset.intersection(*selezioni),
                                   options["modo"])
        elif options["base"]:
            risultato = base          # nessun criterio: si guarda la base
        else:
            risultato = frozenset(Activity.objects.values_list("pk", flat=True))

        self.stdout.write("== Estrai ==")
        if options["base"]:
            self.stdout.write(f"  Base: «{options['base']}» ({len(base)} attività)"
                              f"   modo: {options['modo'] if selezioni else '—'}")
        self.stdout.write(f"  Criteri: {len(selezioni)}"
                          + ("" if selezioni else "  (nessuno: tutte le attività)"))

        for r in rilevamenti:
            self.stdout.write(f"\n== Rilevatore «{r.nome}» ==")
            self.stdout.write(f"  Attività nominate: {len(r.activity_ids)}")
            if r.senza_attivita:
                # ⚠ Dichiarate, mai sottintese: un vincolo che tace e un
                # vincolo innocuo non devono leggersi uguali.
                self.stdout.write(
                    f"  Violazioni che non nominano nessuna attività: "
                    f"{len(r.senza_attivita)} — sono i vincoli sulla risorsa, "
                    "che descrivono la forma di una giornata e non una lezione:")
                for code, message in r.senza_attivita:
                    self.stdout.write(f"    - [{code}] {message}")
            if r.muto:
                self.stdout.write(
                    "  ⚠ L'estrazione di questo rilevatore è vuota, e **non** "
                    "perché l'orario sia sano: nessuna violazione era "
                    "attribuibile a un'attività.")

        self._stampa(schedule, risultato)

        if not options["salva"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--salva NOME` per memorizzare l'estrazione.")
            return
        ex.salva(options["salva"], risultato)
        self.stdout.write(f"\nEstrazione «{options['salva']}» salvata "
                          f"({len(risultato)} attività).")

    def _elenca(self):
        self.stdout.write("== Estrazioni salvate ==")
        righe = Extraction.objects.order_by("name")
        if not righe:
            self.stdout.write("  Nessuna.")
        for e in righe:
            self.stdout.write(f"  {e.name}: {e.activities.count()} attività")

    def _stampa(self, schedule, ids):
        acts = (Activity.objects.filter(pk__in=ids).select_related("subject")
                .prefetch_related("classes", "teachers").order_by("pk"))
        minuti = sum(a.duration_minutes for a in acts)
        self.stdout.write(f"\n== Estratte ({len(ids)}, {_hm(minuti)}) ==")
        for a in acts:
            classi = ", ".join(sorted(c.name for c in a.classes.all()))
            docenti = ", ".join(sorted(t.name for t in a.teachers.all()))
            self.stdout.write(
                f"  [{a.pk}] {a.subject.name} ({_hm(a.duration_minutes)})"
                f"   classi: {classi or '—'}   docenti: {docenti or '—'}")
