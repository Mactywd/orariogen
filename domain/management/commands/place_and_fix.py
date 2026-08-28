"""`Piazza e sistema` da riga di comando: *«sposta l'attività in una posizione
già occupata; se ciò comporta lo spostamento di altre attività, queste
verranno automaticamente ricollocate»*.

Il rendiconto è quello che l'utente deve poter leggere prima di accettare la
mossa: **chi si sposta** e **chi resta fuori**, nominati per materia, classe e
docente. È la stessa forma con cui EDT dichiara il costo di una collocazione
nel risolutore passo-passo — non «3 conflitti», ma le tre lezioni con giorno,
ora, materia, docente e classe.

⚠ Non scrive niente senza `--applica`, come `solve`: forzare una collocazione
riscrive l'orario di una scuola, e un comando che lo facesse premendo invio
sarebbe un modo di perdere il lavoro di qualcun altro.

⚠ Quando non si può, il rifiuto è **nominato**. Sono due risposte diverse e il
comando le tiene distinte: la cella vietata all'attività dai suoi stessi
vincoli (nessuno spostamento aiuterebbe) e l'orario che non si ricompone
attorno (la cella andrebbe bene, ma chi c'è non ha dove andare). La seconda è
il caso in cui servirebbe il risolutore passo-passo, che v1 non ha."""

from django.core.management.base import BaseCommand, CommandError

from domain.models import Activity, Extraction, Resource, Schedule
from domain.solver.model import apply
from domain.solver.place_and_fix import place_and_fix


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


def _riga(act):
    classi = ", ".join(sorted(c.name for c in act.classes.all()))
    docenti = ", ".join(sorted(t.name for t in act.teachers.all()))
    return (f"{act.subject.name} ({_hm(act.duration_minutes)})"
            f"   classi: {classi or '—'}   docenti: {docenti or '—'}")


class Command(BaseCommand):
    help = "Impone una collocazione e ricolloca ciò che disturba"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True)
        parser.add_argument("--attivita", type=int, required=True,
                            help="pk dell'Activity da collocare")
        parser.add_argument("--giorno", type=int, required=True)
        parser.add_argument("--fascia", type=int, required=True,
                            help="fascia di **inizio**: un blocco da 3 ore "
                                 "avviato in 0 occupa 0, 1 e 2")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction su cui lavorare")
        parser.add_argument("--limite", type=float, default=None,
                            help="limite di tempo in secondi, per livello")
        parser.add_argument("--lavoratori", type=int, default=None)
        parser.add_argument("--ignora-opzionali", nargs="*", default=(),
                            choices=[k for k in Resource.Kind.values])
        parser.add_argument("--applica", action="store_true",
                            help="scrive i piazzamenti (senza, non tocca nulla)")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        estrazione = None
        if options["estrazione"]:
            estrazione = Extraction.objects.get(name=options["estrazione"])
        forzata = Activity.objects.select_related("subject").get(
            pk=options["attivita"])
        giorno, fascia = options["giorno"], options["fascia"]

        esito = place_and_fix(
            schedule, forzata.pk, giorno, fascia, extraction=estrazione,
            time_limit=options["limite"], workers=options["lavoratori"],
            ignora_opzionali=options["ignora_opzionali"])
        stats = esito.solution.stats

        self.stdout.write(f"== Piazza e sistema (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Attività: {_riga(forzata)}")
        self.stdout.write(f"  Collocazione richiesta: giorno {giorno}, "
                          f"fascia {fascia}")
        self.stdout.write(f"  Stato: {esito.solution.status}   "
                          f"{stats['secondi']}s")

        if not esito.ok:
            self.stdout.write("\n== Non si può, e il motivo è questo ==")
            for frase in esito.obstruction:
                self.stdout.write(f"  - {frase}")
            raise CommandError("Collocazione rifiutata.")

        self.stdout.write(f"\n== Attività ricollocate ({len(esito.moved)}) ==")
        if not esito.moved:
            self.stdout.write("  Nessuna: la cella era libera per tutti.")
        for act in Activity.objects.filter(pk__in=esito.moved).select_related("subject"):
            dove = esito.solution.placements[act.pk]
            self.stdout.write(f"  {_riga(act)}   → giorno {dove[0]}, "
                              f"fascia {dove[1]}")

        if esito.dropped:
            # ⚠ Separate dalle ricollocate, non sommate: chi resta fuori non si
            # è spostato, ha perso il posto. Sono due danni di gravità diversa.
            self.stdout.write(f"\n== Attività rimaste fuori ({len(esito.dropped)}) ==")
            for act in Activity.objects.filter(
                    pk__in=esito.dropped).select_related("subject"):
                self.stdout.write(f"  {_riga(act)}")

        if not options["applica"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--applica` per salvare.")
            return
        apply(esito.solution, schedule)
        self.stdout.write("\nPiazzamenti scritti.")
        if esito.dropped:
            raise CommandError(
                f"{len(esito.dropped)} attività hanno perso il posto.")
