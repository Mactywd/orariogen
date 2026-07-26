"""L'analisi dei vincoli da riga di comando, nel formato di EDT:
enunciato → dettaglio con l'aritmetica → soluzione → azioni. In coda il
riepilogo navigabile che a EDT manca (diagnostica.md). Exit code ≠ 0 se
restano incoerenze: usabile in CI."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.domain_size import residual_domain
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState
from domain.models import Schedule


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


class Command(BaseCommand):
    help = "Analisi dei vincoli: capienza sui dati e conformità di uno schedule"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int,
                            help="pk dello Schedule di cui verificare la conformità")

    def handle(self, *args, **options):
        capacity = analyze_capacity()
        self.stdout.write("== Analisi di capienza ==")
        if not capacity:
            self.stdout.write("Nessun problema di capienza.")
        for i, f in enumerate(capacity, 1):
            self.stdout.write(f"\n[{i}] {f.statement}")
            header = f"    Unità: {f.unit_label}   Materia: {f.subject_label}"
            if f.teacher_label:
                header += f"   Docente: {f.teacher_label}"
            self.stdout.write(header)
            self.stdout.write(f"    Numero di attività: {f.n_activities}")
            self.stdout.write(f"    Durata da piazzare: {_hm(f.required_minutes)}")
            self.stdout.write(f"    Durata piazzabile:  {_hm(f.placeable_minutes)}")
            gap = f.required_minutes - f.placeable_minutes
            self.stdout.write(f"    » {_hm(gap)} non potrà essere piazzata")
            self.stdout.write("    Soluzione:")
            for culprit in f.culprits:
                self.stdout.write(f"      - {culprit}")
            self.stdout.write("    Azioni:")
            for remedy in f.remedies:
                self.stdout.write(f"      - {remedy}")

        hard = 0
        if options["schedule"]:
            schedule = Schedule.objects.get(pk=options["schedule"])
            findings = check_schedule(schedule)
            self.stdout.write(f"\n== Conformità (schedule {schedule.pk}) ==")
            if not findings:
                self.stdout.write("Nessuna violazione.")
            for f in findings:
                hard += f.severity == Severity.HARD
                details = ", ".join(f"{k}={v}" for k, v in sorted(f.quantities.items()))
                self.stdout.write(f"  [{f.severity}] {f.message}  ({details})")
            state = ScheduleState.build(schedule)
            unplaced = [a for aid, a in sorted(state.activities.items())
                        if aid not in state.placed]
            if unplaced:
                self.stdout.write("\n== S.P. delle attività non piazzate (crescente) ==")
                sized = sorted(((residual_domain(a, state), a) for a in unplaced),
                               key=lambda pair: pair[0].placements)
                for size, act in sized:
                    self.stdout.write(
                        f"  S.P. {size.placements:3d}  Nr G. {size.days}  "
                        f"{act.subject.name} ({_hm(act.duration_minutes)})")

        self.stdout.write("\n== Riepilogo ==")
        self.stdout.write(f"  {len(capacity)} problemi di capienza, "
                          f"{hard} violazioni hard.")
        if capacity or hard:
            raise CommandError("Rimangono delle incoerenze.")
        self.stdout.write("Verifica terminata: nessuna incoerenza.")
