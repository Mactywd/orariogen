"""Il calcolo dell'orario da riga di comando, nella forma in cui EDT lo
racconta: le fasi dichiarate mentre girano, gli scarti **nominati** uno per
uno, e cosa è costato ogni criterio.

⚠ Non scrive niente senza `--applica`. Un solve sovrascrive l'orario di una
scuola, e un comando che lo facesse di default sarebbe un modo di perdere il
lavoro di qualcun altro premendo invio. Senza il flag il comando dice cosa
farebbe; con il flag scrive i piazzamenti e **cancella** quelli delle attività
che ha deciso di scartare.

Exit code ≠ 0 se qualcosa resta scartato: usabile in CI come `analyze`."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Activity, Extraction, Resource, Schedule
from domain.solver.model import apply, solve


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


class Command(BaseCommand):
    help = "Calcola l'orario: piazza ciò che ci sta, nomina ciò che scarta"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello Schedule da calcolare")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction su cui lavorare "
                                 "(il motore opera esclusivamente su di essa)")
        parser.add_argument("--limite", type=float, default=None,
                            help="limite di tempo in secondi, **per livello** "
                                 "della catena lessicografica")
        parser.add_argument("--lavoratori", type=int, default=None,
                            help="thread di ricerca; 1 rende il calcolo "
                                 "riproducibile")
        parser.add_argument("--ignora-opzionali", nargs="*", default=(),
                            choices=[k for k in Resource.Kind.values],
                            help="categorie di risorsa per cui le "
                                 "indisponibilità gialle non si rispettano")
        parser.add_argument("--applica", action="store_true",
                            help="scrive i piazzamenti (senza, non tocca nulla)")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        estrazione = None
        if options["estrazione"]:
            estrazione = Extraction.objects.get(name=options["estrazione"])

        soluzione = solve(schedule, extraction=estrazione,
                          time_limit=options["limite"],
                          workers=options["lavoratori"],
                          ignora_opzionali=options["ignora_opzionali"])
        stats = soluzione.stats

        self.stdout.write(f"== Calcolo (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Stato: {soluzione.status}")
        self.stdout.write(f"  Attività: {stats['attivita']} "
                          f"({stats['libere']} libere)")
        self.stdout.write(f"  Modello: {stats['variabili']} variabili, "
                          f"{stats['constraint']} constraint")
        self.stdout.write(f"  Tempo totale: {stats['secondi']}s")

        if stats["livelli"]:
            self.stdout.write("\n== Criteri, in ordine di priorità ==")
            for i, livello in enumerate(stats["livelli"], 1):
                valore = livello["valore"]
                esito = ("non concluso" if valore is None
                         else f"{valore}" + ("" if livello["ottimo"]
                                             else " (ottimo non dimostrato)"))
                self.stdout.write(f"  [{i}] {livello['nome']}: {esito}"
                                  f"   {livello['secondi']}s")

        if soluzione.status not in ("OPTIMAL", "FEASIBLE"):
            raise CommandError(
                "Nessuna soluzione: il modello è infattibile anche ammettendo "
                "gli scarti. È una diagnosi da `manage.py analyze`, non da qui: "
                "a bloccare è un vincolo sulle attività congelate o sui dati.")

        if soluzione.unplaced:
            self.stdout.write(f"\n== Attività scartate ({len(soluzione.unplaced)}, "
                              f"{_hm(stats['minuti_scartati'])}) ==")
            # ⚠ Si nominano dalle **attività**, non da `check_schedule`: prima
            # di `apply` gli scarti che il solver ha deciso non sono ancora nel
            # database, e il checker racconterebbe l'orario di ieri.
            for act in Activity.objects.filter(
                    pk__in=soluzione.unplaced).select_related("subject"):
                classi = ", ".join(sorted(c.name for c in act.classes.all()))
                docenti = ", ".join(sorted(t.name for t in act.teachers.all()))
                self.stdout.write(f"  {act.subject.name} ({_hm(act.duration_minutes)})"
                                  f"   classi: {classi or '—'}"
                                  f"   docenti: {docenti or '—'}")

        if not options["applica"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--applica` per salvare i piazzamenti.")
        else:
            apply(soluzione, schedule)
            hard = [f for f in check_schedule(schedule)
                    if f.severity == Severity.HARD
                    and f.code != "activity_unplaced"]
            self.stdout.write("\nPiazzamenti scritti.")
            if hard:
                self.stdout.write("\n== Violazioni residue ==")
                for f in hard:
                    self.stdout.write(f"  [{f.severity}] {f.message}")
                self.stdout.write(
                    "  (una violazione qui è un alleggerimento consumato o una "
                    "riga già violata dalle attività congelate: `analyze` le "
                    "spiega una per una)")

        if soluzione.unplaced:
            raise CommandError(
                f"{len(soluzione.unplaced)} attività non piazzate "
                f"({_hm(stats['minuti_scartati'])}).")
        self.stdout.write("\nCalcolo terminato: tutte le attività sono piazzate.")
