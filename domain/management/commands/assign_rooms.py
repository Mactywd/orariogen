"""La ripartizione delle aule: la seconda fase, come comando.

⚠ Non scrive niente senza `--applica`: una ripartizione sovrascrive le aule di
una scuola intera, e il default non puo' essere scrivere.

⚠ `--limite` e' **per livello** della catena, non per l'esecuzione."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Activity, Extraction, Schedule
from domain.solver.objective import descrivi_livello, nota_di_troncatura
from domain.solver.rooms import apply_rooms, solve_rooms


def _hm(minuti):
    return f"{minuti // 60}h{minuti % 60:02d}"


class Command(BaseCommand):
    help = "Assegna le aule alle attività già piazzate di uno schedule."

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello schedule da ripartire")
        parser.add_argument("--limite", type=float, default=None,
                            help="limite di tempo in secondi, per livello")
        parser.add_argument("--lavoratori", type=int, default=None,
                            help="numero di thread CP-SAT (1 = riproducibile)")
        parser.add_argument("--ignora-opzionali", nargs="*", default=(),
                            dest="ignora_opzionali",
                            help="tipi di risorsa per cui le indisponibilità "
                                 "gialle non si rispettano (es. room)")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction: si riassegnano solo le "
                                 "aule delle attività estratte, e le altre "
                                 "tengono la loro occupandone la capienza")
        parser.add_argument("--applica", action="store_true",
                            help="scrive le aule assegnate nel database")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        estrazione = None
        if options["estrazione"]:
            estrazione = Extraction.objects.get(name=options["estrazione"])
        soluzione = solve_rooms(schedule, time_limit=options["limite"],
                                workers=options["lavoratori"],
                                ignora_opzionali=options["ignora_opzionali"],
                                extraction=estrazione)
        stats = soluzione.stats

        self.stdout.write(f"== Ripartizione delle aule (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Stato: {soluzione.status}")
        self.stdout.write(f"  Richieste d'aula: {stats['richieste']} "
                          f"({stats['assegnate']} assegnate)")
        if stats["eccedenza_capienza"]:
            # ⚠ È un **criterio**, non un vincolo: si dichiara, non si rifiuta.
            # In EDT è `Minimizza il superamento della capienza`, e superarla è
            # previsto — quello che non è previsto è farlo senza dirlo.
            self.stdout.write(
                f"  Alunni oltre la capienza dichiarata: "
                f"{stats['eccedenza_capienza']}")
        self.stdout.write(f"  Modello: {stats['variabili']} variabili, "
                          f"{stats['constraint']} constraint")
        self.stdout.write(f"  Tempo totale: {stats['secondi']}s")

        if stats["livelli"]:
            self.stdout.write("\n== Criteri, in ordine di priorità ==")
            for i, livello in enumerate(stats["livelli"], 1):
                self.stdout.write(
                    f"  [{i}] {livello['nome']}: {descrivi_livello(livello)}"
                    f"   {livello['secondi']}s")
            nota = nota_di_troncatura(stats["livelli"])
            if nota is not None:
                self.stdout.write(nota)

        if soluzione.status not in ("OPTIMAL", "FEASIBLE"):
            raise CommandError(
                "Nessuna ripartizione: il modello è infattibile anche "
                "ammettendo le rinunce. A bloccare è un'aula tenuta da "
                "un'attività immobile o un dato incoerente.")

        if soluzione.unassigned:
            self.stdout.write(
                f"\n== Richieste senza aula ({len(soluzione.unassigned)}, "
                f"{_hm(stats['minuti_senza_aula'])}) ==")
            # ⚠ Si nominano dalle **attività**, non da `check_schedule`: prima
            # di `apply_rooms` le rinunce non sono nel database, e il checker
            # racconterebbe la ripartizione di ieri.
            for act in (Activity.objects.filter(pk__in=soluzione.unassigned)
                        .select_related("subject")
                        .prefetch_related("classes", "teachers", "rooms",
                                          "placements")):
                classi = ", ".join(sorted(c.name for c in act.classes.all()))
                docenti = ", ".join(sorted(t.name for t in act.teachers.all()))
                candidate = ", ".join(sorted(r.name for r in act.rooms.all()))
                dove = ", ".join(f"g{p.day} f{p.start_slot}"
                                 for p in act.placements.all()
                                 if p.schedule_id == schedule.pk)
                self.stdout.write(
                    f"  {act.subject.name} ({_hm(act.duration_minutes)})"
                    f"   classi: {classi or '—'}   docenti: {docenti or '—'}"
                    f"   quando: {dove or '—'}   chiedeva: {candidate}")

        if not options["applica"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--applica` per salvare le aule.")
        else:
            apply_rooms(soluzione, schedule)
            hard = [f for f in check_schedule(schedule)
                    if f.severity == Severity.HARD
                    and f.code not in ("activity_unplaced", "room_unassigned")]
            self.stdout.write("\nAule scritte.")
            if hard:
                self.stdout.write("\n== Violazioni residue ==")
                for f in hard:
                    self.stdout.write(f"  [{f.severity}] {f.message}")

        if soluzione.unassigned:
            raise CommandError(
                f"{len(soluzione.unassigned)} richieste d'aula senza risposta "
                f"({_hm(stats['minuti_senza_aula'])}).")
        self.stdout.write("\nRipartizione terminata: ogni richiesta ha la sua aula.")
